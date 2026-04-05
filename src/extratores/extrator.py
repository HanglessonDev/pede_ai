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

from src.extratores.config import ExtratorConfig
from src.extratores.itens_ids import build_itens_ids
from src.extratores.modelos import ItemExtraido
from src.extratores.nlp_engine import NlpEngine
from src.extratores.remocoes import capturar_remocoes


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

    def extrair(self, mensagem: str) -> list[ItemExtraido]:
        """Extrai itens do cardapio de uma mensagem.

        Tenta EntityRuler (spaCy) primeiro. Se nao encontrar itens,
        usa fuzzy matching como fallback para tolerar typos.

        Args:
            mensagem: Texto da mensagem do usuario.

        Returns:
            Lista de ItemExtraido.
        """
        doc = self._engine.processar(mensagem)

        itens_spacy = self._extrair_spacy(doc)

        # EntityRuler encontrou itens — usa direto
        if itens_spacy:
            return itens_spacy

        # Fallback: delega ao modulo fuzzy
        from src.extratores.fuzzy_extrator import extrair_item_fuzzy  # noqa: PLC0415

        qtd = self._extrair_qtd_do_doc(doc)
        return extrair_item_fuzzy(mensagem, qtd)

    def _extrair_qtd_do_doc(self, doc) -> int:
        """Extrai quantidade de entidades QTD no doc.

        Args:
            doc: Documento spaCy processado.

        Returns:
            Quantidade encontrada ou 1 (default).
        """
        for ent in doc.ents:
            if ent.label_ in ('QTD', 'NUM_PENDING'):
                texto = ent.text.lower()
                return (
                    int(ent.text)
                    if ent.text.isdigit()
                    else self._config.numeros_escritos.get(texto, 1)
                )
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
        remocoes_fila = capturar_remocoes(doc, self._config)
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

        for ent in doc.ents:
            if item_atual is not None:
                _consumir_remocoes_ate(ent.start)

            if ent.label_ in ('QTD', 'NUM_PENDING'):
                texto = ent.text.lower()
                qtd_pendente = (
                    int(ent.text)
                    if ent.text.isdigit()
                    else self._config.numeros_escritos.get(texto, 1)
                )

            elif ent.label_ == 'ITEM':
                if item_atual is not None:
                    itens.append(item_atual)
                item_atual = ItemExtraido(
                    item_id=ent.ent_id_,
                    quantidade=qtd_pendente,
                    variante=variante_pendente,  # aplica variante pendente
                    remocoes=[],
                )
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

        return itens

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
