"""Extrator de informacoes de troca de itens.

Substitui extrair_itens_troca() do modulo procedural.

Example:
    ```python
    from src.extratores.troca_extrator import TrocaExtrator

    extrator = TrocaExtrator(engine, config)
    extrator.extrair('muda pra lata', carrinho)
    ```
"""

from __future__ import annotations

from src.config import get_nome_item
from src.extratores.config import ExtratorConfig
from src.extratores.fuzzy_extrator import fuzzy_match_variante
from src.extratores.modelos import (
    ExtracaoTroca,
    ItemMencionado,
    ItemOriginal,
    MatchCarrinho,
)
from src.extratores.nlp_engine import NlpEngine
from src.extratores.normalizador import normalizar_para_busca


class TrocaExtrator:
    """Extrai informacoes de troca da mensagem."""

    def __init__(self, engine: NlpEngine, config: ExtratorConfig) -> None:
        """Inicializa o extrator de troca.

        Args:
            engine: NlpEngine com modelo spaCy lazy-loaded.
            config: Configuracao do extrator.
        """
        self._engine = engine
        self._config = config

    def extrair(self, mensagem: str, carrinho: list[dict]) -> ExtracaoTroca:
        """Extrai informacoes de troca da mensagem.

        Classifica em casos:
        - 'A': 2+ ITEMs (troca item por item)
        - 'B': 1 ITEM (com ou sem variante, busca no carrinho)
        - 'C': 0 ITEMs + 1 VARIANTE isolada
        - 'vazio': nenhuma entidade relevante encontrada

        Args:
            mensagem: Mensagem do usuario.
            carrinho: Carrinho atual.

        Returns:
            ExtracaoTroca com caso, item_original e variante_nova.
        """
        if not mensagem or not mensagem.strip():
            return ExtracaoTroca(caso='vazio', item_original=None, variante_nova=None)

        doc = self._engine.processar(mensagem)

        # Coletar entidades em ordem
        itens_mencionados: list[ItemMencionado] = []
        variantes_sozinhas: list[str] = []

        for ent in doc.ents:
            if ent.label_ == 'ITEM':
                itens_mencionados.append(
                    ItemMencionado(
                        texto=normalizar_para_busca(ent.text),
                        variante=None,
                        ent_id=ent.ent_id_,
                    )
                )
            elif ent.label_ == 'VARIANTE':
                # Se tem ITEM antes, associa a ele
                if itens_mencionados:
                    ultimo = itens_mencionados[-1]
                    itens_mencionados[-1] = ItemMencionado(
                        texto=ultimo.texto,
                        variante=normalizar_para_busca(ent.text),
                        ent_id=ultimo.ent_id,
                    )
                else:
                    # Variante sem ITEM = variante isolada (caso C)
                    variantes_sozinhas.append(normalizar_para_busca(ent.text))

        # Classificar caso
        num_items = len(itens_mencionados)
        num_variantes = len(variantes_sozinhas)

        # Caso A: 2+ ITEMs (troca item por item)
        if num_items >= 2:
            return ExtracaoTroca(caso='A', item_original=None, variante_nova=None)

        # Caso B: 1 ITEM (com ou sem variante)
        if num_items == 1:
            return self._processar_caso_b(itens_mencionados[0], carrinho, mensagem)

        # Caso C: 0 ITEMs + 1 VARIANTE isolada
        if num_items == 0 and num_variantes == 1:
            return ExtracaoTroca(
                caso='C', item_original=None, variante_nova=variantes_sozinhas[0]
            )

        # Fallback fuzzy: se nada foi extrai do, tentar fuzzy match
        return self._fallback_fuzzy_completo(mensagem, carrinho)

    def _processar_caso_b(
        self,
        item_mencionado: ItemMencionado,
        carrinho: list[dict],
        mensagem: str,
    ) -> ExtracaoTroca:
        """Processa caso B: 1 ITEM mencionado."""
        # Buscar no carrinho — sem considerar a variante mencionada,
        # pois ela e a variante de DESTINO, nao a atual do carrinho.
        item_para_busca = ItemMencionado(
            texto=item_mencionado.texto,
            variante=None,
            ent_id=item_mencionado.ent_id,
        )
        matches = _buscar_matches_no_carrinho([item_para_busca], carrinho)

        item_original: ItemOriginal | None = None
        if matches:
            match = matches[0]
            nome = get_nome_item(match.item_id) or match.item_id
            item_original = ItemOriginal(
                item_id=match.item_id,
                nome=nome,
                indices=match.indices,
            )

        variante_nova = item_mencionado.variante

        # Fallback fuzzy: se variante nao foi extraida pelo EntityRuler
        if variante_nova is None and item_original is not None:
            variante_nova = self._tentar_fuzzy_variante(mensagem, item_original.item_id)

        return ExtracaoTroca(
            caso='B',
            item_original=item_original,
            variante_nova=variante_nova,
        )

    def _tentar_fuzzy_variante(self, mensagem: str, item_id: str | None) -> str | None:
        """Tenta extrair variante via fuzzy matching."""
        from src.config import get_cardapio  # noqa: PLC0415 — lazy loading

        cardapio = get_cardapio()
        if item_id:
            item_data = next((i for i in cardapio['itens'] if i['id'] == item_id), None)
            variantes = (
                [v['opcao'] for v in item_data.get('variantes', [])]
                if item_data
                else []
            )
        else:
            variantes = []
            for item in cardapio['itens']:
                for v in item.get('variantes', []):
                    if v['opcao'] not in variantes:
                        variantes.append(v['opcao'])

        resultado, _score = fuzzy_match_variante(mensagem, variantes)
        return resultado

    def _fallback_fuzzy_completo(
        self, mensagem: str, carrinho: list[dict]
    ) -> ExtracaoTroca:
        """Fallback completo quando EntityRuler nao extrai nada."""
        from src.config import get_cardapio  # noqa: PLC0415 — lazy loading
        from src.extratores.fuzzy_extrator import fuzzy_match_item  # noqa: PLC0415

        cardapio = get_cardapio()
        alias_para_id: dict[str, str] = {}
        for item in cardapio['itens']:
            for texto in [item['nome'], *item.get('aliases', [])]:
                if texto and texto not in alias_para_id:
                    alias_para_id[texto] = item['id']

        alias, _score, item_id = fuzzy_match_item(mensagem, alias_para_id)
        if item_id is None:
            return ExtracaoTroca(caso='vazio', item_original=None, variante_nova=None)

        # Buscar no carrinho
        item_para_busca = ItemMencionado(
            texto=normalizar_para_busca(alias) if alias else '',
            variante=None,
            ent_id=item_id,
        )
        matches = _buscar_matches_no_carrinho([item_para_busca], carrinho)

        item_original: ItemOriginal | None = None
        if matches:
            match = matches[0]
            nome = get_nome_item(match.item_id) or match.item_id
            item_original = ItemOriginal(
                item_id=match.item_id,
                nome=nome,
                indices=match.indices,
            )
        else:
            nome = get_nome_item(item_id) or item_id
            item_original = ItemOriginal(
                item_id=item_id,
                nome=nome,
                indices=[],
            )

        # Tentar fuzzy variante
        variante = self._tentar_fuzzy_variante(mensagem, item_id)

        return ExtracaoTroca(
            caso='B' if item_original else 'vazio',
            item_original=item_original,
            variante_nova=variante,
        )


def _buscar_matches_no_carrinho(
    itens_mencionados: list[ItemMencionado],
    carrinho: list[dict],
) -> list[MatchCarrinho]:
    """Busca itens mencionados no carrinho e retorna matches."""
    resultados: list[MatchCarrinho] = []
    indices_ja_adicionados: set[int] = set()

    for item_mencionado in itens_mencionados:
        for i, item_carrinho in enumerate(carrinho):
            if i in indices_ja_adicionados:
                continue

            nome_item = (
                get_nome_item(item_carrinho['item_id']) or item_carrinho['item_id']
            )
            nome_normalizado = normalizar_para_busca(nome_item)
            variante_carrinho = normalizar_para_busca(
                item_carrinho.get('variante') or ''
            )

            match_nome = _verificar_match_nome(
                item_mencionado.texto,
                item_mencionado.ent_id,
                item_carrinho['item_id'],
                nome_normalizado,
            )
            match_variante = _verificar_match_variante(
                item_mencionado.variante, variante_carrinho
            )

            if match_nome and match_variante:
                _adicionar_ou_atualizar_resultado(
                    resultados, item_carrinho, i, indices_ja_adicionados
                )

    return resultados


def _verificar_match_nome(
    texto_mencionado: str | None,
    ent_id: str,
    item_id_carrinho: str,
    nome_normalizado: str,
) -> bool:
    """Verifica se ha match por nome ou ID."""
    if texto_mencionado and texto_mencionado in nome_normalizado:
        return True
    return ent_id == item_id_carrinho


def _verificar_match_variante(
    variante_mencionada: str | None, variante_carrinho: str
) -> bool:
    """Verifica se ha match por variante."""
    if variante_mencionada:
        return variante_mencionada in variante_carrinho
    return True


def _adicionar_ou_atualizar_resultado(
    resultados: list[MatchCarrinho],
    item_carrinho: dict,
    indice: int,
    indices_ja_adicionados: set[int],
) -> None:
    """Adiciona ou atualiza resultado existente."""
    existente = next(
        (r for r in resultados if r.item_id == item_carrinho['item_id']), None
    )
    if existente:
        resultados[resultados.index(existente)] = MatchCarrinho(
            item_id=existente.item_id,
            variante=existente.variante,
            indices=[*existente.indices, indice],
        )
    else:
        resultados.append(
            MatchCarrinho(
                item_id=item_carrinho['item_id'],
                variante=item_carrinho.get('variante'),
                indices=[indice],
            )
        )
    indices_ja_adicionados.add(indice)
