"""Extrator principal de itens do cardapio.

API publica com compatibilidade retroativa — retorna dicts
para nao quebrar consumidores existentes.

Example:
    ```python
    from src.extratores.extrator import extrair, extrair_variante

    extrair('2 x-bacon sem cebola')
    [
        {
            'item_id': 'lanche_003',
            'quantidade': 2,
            'variante': None,
            'remocoes': ['cebola'],
        }
    ]
    ```
"""

from __future__ import annotations

from dataclasses import asdict
from typing import cast

from src.extratores.complementos import detectar_complementos
from src.extratores.config import ExtratorConfig
from src.extratores.itens_ids import build_itens_ids
from src.extratores.modelos import ItemExtraido
from src.extratores.negacao import detectar_negacao
from src.extratores.nlp_engine import NlpEngine
from src.extratores.observacoes import detectar_observacoes
from src.extratores.quantidade import resolver_quantidade, extrair_quantidade_do_texto
from src.extratores.remocoes import capturar_remocoes_v2


def _entidade_dentro_de_parenteses(doc, ent) -> bool:
    """Verifica se a entidade está dentro de parenteses.

    Ex: '(com dois 'o')' — 'dois' nao deve ser tratado como QTD.
    Procura por '(' ou '[' em qualquer token anterior na mesma sentenca.
    """
    for i in range(ent.start - 1, -1, -1):
        t = doc[i]
        if t.text in ('(', '[', ')', ']'):
            return t.text in ('(', '[')
        if t.pos_ == 'PUNCT' and t.text in ('.', '!', '?'):
            return False  # sentenca diferente
    return False


class Extrator:
    """Extrator de itens do cardapio via spaCy + fuzzy fallback."""

    def __init__(
        self,
        engine: NlpEngine,
        config: ExtratorConfig,
        cardapio: dict,
    ) -> None:
        """Inicializa o extrator.

        Args:
            engine: NlpEngine com modelo spaCy lazy-loaded.
            config: Configuracao do extrator.
            cardapio: Dados do cardapio (get_cardapio()).
        """
        self._engine = engine
        self._config = config
        self._itens_ids = build_itens_ids(cardapio)
        self._cardapio = cardapio

    def extrair(self, mensagem: str) -> list[ItemExtraido]:
        """Extrai itens do cardapio de uma mensagem.

        Tenta EntityRuler (spaCy) primeiro. Se nao encontrar itens,
        usa fuzzy matching como fallback para tolerar typos.

        Args:
            mensagem: Texto da mensagem do usuario.

        Returns:
            Lista de ItemExtraido.
        """
        # Verifica negacao primeiro — se usuario esta cancelando o pedido
        if detectar_negacao(mensagem):
            return []

        doc = self._engine.processar(mensagem)

        itens_spacy = self._extrair_spacy(doc)

        # Fuzzy para regioes nao cobertas pelo EntityRuler
        itens_fuzzy = self._extrair_fuzzy_nao_coberto(doc, itens_spacy)

        if itens_spacy or itens_fuzzy:
            return itens_spacy + itens_fuzzy

        # Fallback total: fuzzy na mensagem inteira
        from src.extratores.fuzzy_extrator import extrair_item_fuzzy  # noqa: PLC0415

        qtd, _ = extrair_quantidade_do_texto(mensagem, self._config)
        return extrair_item_fuzzy(mensagem, int(qtd) if qtd else 1)

    def _extrair_qtd_do_doc(self, doc) -> int:
        """Extrai quantidade de entidades QTD/NUM_PENDING no doc."""
        for ent in doc.ents:
            if ent.label_ in ('QTD', 'NUM_PENDING'):
                qtd = resolver_quantidade(ent.text.lower(), self._config)
                if qtd is not None:
                    return int(qtd)
        return 1

    def _extrair_spacy(self, doc) -> list[ItemExtraido]:
        """Extrai itens via spaCy EntityRuler.

        Fluxo de quantidades:
        - QTD antes do ITEM → aplica ao próximo item (qtd_pendente)
        - QTD depois do ITEM já registrado (item_atual not None) → **NÃO**
          guardar como qtd_pendente para o próximo item. Em vez disso,
          atualizar item_atual.quantidade diretamente. Isso resolve o caso
          'hamburguer 2' onde o número aparece DEPOIS do item e deve ser
          associado a ele, não ao item seguinte.
        - Variante depois do ITEM → associa direto ao item_atual
        - Variante antes do ITEM → guarda como variante_pendente

        Nota de design (EXTRATOR_DESIGN.md §5.4):
        O Branch 4 redundante do desambiguar() foi removido porque tanto o
        'elif ultimo_item_ent is not None' quanto o 'else' produziam o mesmo
        output (Entidade QTD). A associação correta é feita aqui, no
        _extrair_spacy(), onde temos contexto do item_atual.
        """
        qtd_pendente = 1
        remocoes_fila = capturar_remocoes_v2(doc, self._config, self._itens_ids)
        prox_remocao = 0
        itens: list[ItemExtraido] = []
        item_atual: ItemExtraido | None = None
        variante_pendente: str | None = None  # variante antes do ITEM

        def _consumir_remocoes_ate(limite: int) -> None:
            nonlocal prox_remocao
            nonlocal item_atual
            while (
                prox_remocao < len(remocoes_fila)
                and remocoes_fila[prox_remocao][1] < limite
            ):
                if item_atual is not None:
                    item_atual = ItemExtraido(
                        item_id=item_atual.item_id,
                        quantidade=item_atual.quantidade,
                        variante=item_atual.variante,
                        remocoes=[*item_atual.remocoes, remocoes_fila[prox_remocao][0]],
                    )
                prox_remocao += 1

        def _e_numero_exato(texto: str) -> bool:
            """Retorna True se o texto e um digito exato (ex: '2', '3')."""
            return texto.isdigit()

        item_atual_ent_end: int = -1  # posicao final do ITEM atual

        for ent in doc.ents:
            if item_atual is not None:
                _consumir_remocoes_ate(ent.start)

            if ent.label_ in ('QTD', 'NUM_PENDING'):
                texto = ent.text.lower()
                qtd = resolver_quantidade(texto, self._config) or 1

                # Numeros exatos (digitos) imediatamente depois do ITEM
                # atualizam o item (ex: 'hamburguer 2' — end do ITEM == start do NUM)
                # Se nao for adjacente, e qtd_pendente para o PROXIMO item
                eh_pos_item = (
                    item_atual is not None
                    and _e_numero_exato(texto)
                    and ent.start == item_atual_ent_end
                )

                if eh_pos_item:
                    # item_atual é garantido não-None aqui (condicao do eh_pos_item)
                    _atual = cast('ItemExtraido', item_atual)
                    item_atual = ItemExtraido(
                        item_id=_atual.item_id,
                        quantidade=qtd,
                        variante=_atual.variante,
                        remocoes=_atual.remocoes,
                    )
                else:
                    # Numero antes do item — fica pendente para o proximo
                    qtd_pendente = qtd

            elif ent.label_ == 'ITEM':
                if item_atual is not None:
                    itens.append(item_atual)
                item_atual = ItemExtraido(
                    item_id=ent.ent_id_,
                    quantidade=qtd_pendente,
                    variante=variante_pendente,  # aplica variante pendente
                    remocoes=[],
                )
                item_atual_ent_end = ent.end  # salva posicao final do ITEM
                variante_pendente = None  # consumida
                qtd_pendente = 1

            elif ent.label_ == 'VARIANTE':
                if item_atual is not None:
                    # Variante depois do ITEM — associa direto
                    item_atual = ItemExtraido(
                        item_id=item_atual.item_id,
                        quantidade=item_atual.quantidade,
                        variante=ent.text,
                        remocoes=item_atual.remocoes,
                    )
                else:
                    # Variante antes do ITEM — guarda para associar depois
                    variante_pendente = ent.text

        if item_atual is not None:
            _consumir_remocoes_ate(len(doc))
            itens.append(item_atual)

        # Camada 6 + 7: detectar complementos e observacoes por item
        if itens:
            itens = self._enriquecer_itens(itens, doc)

        return itens

    def _extrair_fuzzy_nao_coberto(
        self, doc, itens_spacy: list[ItemExtraido]
    ) -> list[ItemExtraido]:
        """Extrai itens via fuzzy para regioes nao cobertas pelo EntityRuler.

        Quando o EntityRuler encontra alguns items mas nao todos (ex:
        'hamburguer' com acento nao e' reconhecido mas 'batata' e 'coca' sao),
        esta funcao identifica o texto nao coberto e tenta fuzzy matching nele.

        Tambem preserva quantidades detectadas pelo EntityRuler (QTD/NUM_PENDING)
        que nao foram consumidas por nenhum ITEM.

        Args:
            doc: Documento spaCy processado.
            itens_spacy: Itens ja extraidos pelo EntityRuler.

        Returns:
            Lista de ItemExtraido encontrados via fuzzy (sem duplicatas).
        """
        # 1. Tokens cobertos por qualquer entidade nossa
        # IMPORTANTE: so' marcar VARIANTE como coberto se houver ITEM —
        # caso contrario, variante solta (ex: "simples" em "hamburges simples")
        # deve ficar disponivel para o fuzzy match extrair.
        tem_item_spacy = any(ent.label_ == 'ITEM' for ent in doc.ents)
        cobertos: set[int] = set()
        for ent in doc.ents:
            if ent.label_ in ('ITEM', 'QTD', 'NUM_PENDING') or (
                ent.label_ == 'VARIANTE' and tem_item_spacy
            ):
                for i in range(ent.start, ent.end):
                    cobertos.add(i)

        # Coletar QTDs nao consumidas (entidades QTD/NUM_PENDING sem ITEM correspondente)
        # Cada ITEM do EntityRuler consome a QTD mais recente que o precede
        todas_qtds: list[tuple[int, int | float]] = []  # (pos_token, valor)
        for ent in doc.ents:
            if ent.label_ in ('QTD', 'NUM_PENDING'):
                if _entidade_dentro_de_parenteses(doc, ent):
                    continue
                texto = ent.text.lower()
                qtd = resolver_quantidade(texto, self._config)
                if qtd is not None:
                    todas_qtds.append((ent.start, qtd))

        # QTDs consumidas por itens spacy: cada ITEM consome a QTD mais recente antes dele
        qtds_indices_consumidas: set[int] = set()
        for item in itens_spacy:
            # Find the QTD entity that was used for this item
            # (the one with the highest position before the item's first entity match)
            for idx, (_qtd_pos, qtd_val) in reversed(list(enumerate(todas_qtds))):
                if idx not in qtds_indices_consumidas and qtd_val == item.quantidade:
                    qtds_indices_consumidas.add(idx)
                    break

        # QTDs disponiveis para fuzzy
        qtds_pendentes = [
            qtd
            for idx, qtd in enumerate(todas_qtds)
            if idx not in qtds_indices_consumidas
        ]

        # 2. Tokens livres (nao cobertos, significativos)
        _palavras_baixa_qualidade = self._config.palavras_remocao | {
            'sal',
            'gelo',
            'agua',
            'nada',
            'tudo',
            'algo',
        }
        tokens_livres = [
            t
            for t in doc
            if t.i not in cobertos
            and t.pos_ not in ('PUNCT', 'SPACE', 'SYM')
            and len(t.text) >= 3
            and t.text.lower() not in _palavras_baixa_qualidade
        ]
        if not tokens_livres:
            return []

        # 3. Reconstruir texto dos tokens livres
        texto_livre = doc[tokens_livres[0].i : tokens_livres[-1].i + 1].text

        # Texto muito curto → nao vale fuzzy
        if len(texto_livre.strip()) < 4:
            return []

        # 4. Fuzzy match com quantidade pendente
        from src.extratores.fuzzy_extrator import extrair_item_fuzzy  # noqa: PLC0415
        from src.extratores.fuzzy_extrator import (  # noqa: PLC0415
            fuzzy_match_item,
            extrair_tokens_significativos,
        )

        quantidade = int(qtds_pendentes[0][1]) if qtds_pendentes else 1
        itens = extrair_item_fuzzy(texto_livre, quantidade=quantidade)

        # 5. Evitar duplicatas — so' adiciona se item_id nao existe em spacy
        # E tambem se o token fuzzy nao e substring de item ja extraido
        # (ex: "coca" quando "coca zero" ja existe)
        ids_spacy = {item.item_id for item in itens_spacy}
        nomes_spacy = {ent.text.lower() for ent in doc.ents if ent.label_ == 'ITEM'}

        def _tem_substring_repetida(texto: str) -> bool:
            """Verifica se algum token do texto e substring de item spacy."""
            tokens = texto.split() if ' ' in texto else [texto]
            for nome_spacy in nomes_spacy:
                for token in tokens:
                    if len(token) >= 3 and token.lower() in nome_spacy:
                        return True
            return False

        resultados = [
            ItemExtraido(
                item_id=item.item_id,
                quantidade=item.quantidade,
                variante=item.variante,
                remocoes=item.remocoes,
                complementos=item.complementos,
                observacoes=item.observacoes,
                confianca=item.confianca,
                fonte='fuzzy',
            )
            for item in itens
            if item.item_id not in ids_spacy
            and not _tem_substring_repetida(texto_livre)
        ]

        # Se nao encontrou nada no texto inteiro, tentar tokens individuais
        # Resolve "cocas e batata" onde fuzzy prefere "batata" no texto completo
        if not resultados:
            alias_para_id: dict[str, str] = {}
            for item in self._cardapio.get('itens', []):
                alias_para_id[item['nome'].lower()] = item['id']
                for alias in item.get('aliases', []):
                    alias_para_id[alias.lower()] = item['id']

            # Usar QTDs nao consumidas pelos itens spacy
            qtd_fuzzy = int(qtds_pendentes[0][1]) if qtds_pendentes else 1

            tokens_sig = extrair_tokens_significativos(texto_livre)
            cutoff = self._config.fuzzy_item_cutoff
            # Limitar a 1 item por fallback para evitar over-matching
            for token in tokens_sig:
                alias, score, item_id = fuzzy_match_item(token, alias_para_id)
                if (
                    item_id
                    and item_id not in ids_spacy
                    and not _tem_substring_repetida(token)
                    and score >= cutoff
                ):
                    resultados.append(
                        ItemExtraido(
                            item_id=item_id,
                            quantidade=qtd_fuzzy,
                            variante=None,
                            remocoes=[],
                            complementos=[],
                            observacoes=[],
                            confianca=score / 100,
                            fonte='fuzzy',
                        )
                    )
                    break  # So' pega o melhor match

        return resultados

    def _enriquecer_itens(self, itens: list[ItemExtraido], doc) -> list[ItemExtraido]:
        """Detecta complementos e observacoes para cada item extraido.

        Args:
            itens: Lista de itens extraidos pelo loop principal.
            doc: Documento spaCy processado.

        Returns:
            Lista de itens com complementos e observacoes preenchidos.
        """
        itens_enriquecidos: list[ItemExtraido] = []
        for item in itens:
            complementos = detectar_complementos(
                doc, item.item_id, self._cardapio, self._config
            )
            observacoes = detectar_observacoes(doc)
            itens_enriquecidos.append(
                ItemExtraido(
                    item_id=item.item_id,
                    quantidade=item.quantidade,
                    variante=item.variante,
                    remocoes=item.remocoes,
                    complementos=complementos,
                    observacoes=observacoes,
                    confianca=item.confianca,
                    fonte=item.fonte,
                )
            )
        return itens_enriquecidos

    def extrair_variante(self, mensagem: str, item_id: str) -> str | None:
        """Extrai e valida uma variante de uma mensagem para um item especifico.

        Args:
            mensagem: Texto da mensagem do usuario.
            item_id: ID do item no cardapio para validacao.

        Returns:
            Texto da variante valida ou None.
        """
        if not mensagem or not mensagem.strip():
            return None

        doc = self._engine.processar(mensagem)
        for ent in doc.ents:
            if ent.label_ == 'VARIANTE' and ent.ent_id_ == item_id:
                return ent.text

        return None


# ── API publica compativel com a versao procedural ─────────────────────────

_extrator: Extrator | None = None


def _get_extrator() -> Extrator:
    """Retorna extrator singleton lazy."""
    global _extrator  # noqa: PLW0603 — lazy singleton intencional
    if _extrator is None:
        from src.config import get_cardapio  # noqa: PLC0415 — lazy loading
        from src.extratores.config import get_extrator_config  # noqa: PLC0415
        from src.extratores.nlp_engine import NlpEngine  # noqa: PLC0415

        config = get_extrator_config()
        cardapio = get_cardapio()
        engine = NlpEngine(config, cardapio)
        _extrator = Extrator(engine, config, cardapio)
    return _extrator


def extrair(mensagem: str) -> list[dict]:
    """Extrai itens do cardapio de uma mensagem do usuario.

    API compativel com a versao procedural — retorna list[dict].

    Args:
        mensagem: Texto da mensagem do usuario.

    Returns:
        Lista de dicionarios com as chaves:
            - item_id: ID do item no cardapio.
            - quantidade: Quantidade solicitada.
            - variante: Variante selecionada (ou None).
            - remocoes: Lista de ingredientes a remover.

    Example:
        ```python
        from src.extratores import extrair

        extrair('2 x-bacon sem cebola')
        [
            {
                'item_id': 'lanche_003',
                'quantidade': 2,
                'variante': None,
                'remocoes': ['cebola'],
            }
        ]
        ```
    """
    itens = _get_extrator().extrair(mensagem)
    return [asdict(item) for item in itens]


def extrair_variante(mensagem: str, item_id: str) -> str | None:
    """Extrai e valida uma variante de uma mensagem para um item especifico.

    Args:
        mensagem: Texto da mensagem do usuario.
        item_id: ID do item no cardapio para validacao.

    Returns:
        Texto da variante valida ou None.
    """
    return _get_extrator().extrair_variante(mensagem, item_id)
