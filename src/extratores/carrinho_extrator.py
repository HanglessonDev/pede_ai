"""Extrator de itens do carrinho para remocao.

Substitui extrair_item_carrinho() do modulo procedural.

Example:
    ```python
    from src.extratores.carrinho_extrator import CarrinhoExtrator

    extrator = CarrinhoExtrator(engine, config)
    extrator.extrair('tira a coca', carrinho)
    ```
"""

from __future__ import annotations

from src.config import get_nome_item
from src.extratores.config import ExtratorConfig
from src.extratores.modelos import ItemMencionado, MatchCarrinho
from src.extratores.nlp_engine import NlpEngine
from src.extratores.normalizador import normalizar_para_busca


class CarrinhoExtrator:
    """Extrai itens do carrinho para remocao."""

    def __init__(self, engine: NlpEngine, config: ExtratorConfig) -> None:
        """Inicializa o extrator de carrinho.

        Args:
            engine: NlpEngine com modelo spaCy lazy-loaded.
            config: Configuracao do extrator.
        """
        self._engine = engine
        self._config = config

    def extrair(self, mensagem: str, carrinho: list[dict]) -> list[MatchCarrinho]:
        """Extrai itens do carrinho para remocao.

        Args:
            mensagem: Texto da mensagem do usuario.
            carrinho: Lista de itens no carrinho atual.

        Returns:
            Lista de MatchCarrinho com item_id, variante e indices.
        """
        if not mensagem or not mensagem.strip():
            return []

        if not carrinho:
            return []

        # Caso especial: "tira tudo"
        msg_norm = normalizar_para_busca(mensagem)
        if 'tira tudo' in msg_norm or 'remove tudo' in msg_norm:
            return [
                MatchCarrinho(
                    item_id=item['item_id'],
                    variante=item.get('variante'),
                    indices=[i],
                )
                for i, item in enumerate(carrinho)
            ]

        # Extrair itens mencionados na mensagem
        doc = self._engine.processar(mensagem)
        itens_mencionados: list[ItemMencionado] = []

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
                if itens_mencionados:
                    ultimo = itens_mencionados[-1]
                    itens_mencionados[-1] = ItemMencionado(
                        texto=ultimo.texto,
                        variante=normalizar_para_busca(ent.text),
                        ent_id=ultimo.ent_id,
                    )
                else:
                    itens_mencionados.append(
                        ItemMencionado(
                            texto='',
                            variante=normalizar_para_busca(ent.text),
                            ent_id=ent.ent_id_,
                        )
                    )

        return _buscar_matches_no_carrinho(itens_mencionados, carrinho)


def _buscar_matches_no_carrinho(
    itens_mencionados: list[ItemMencionado],
    carrinho: list[dict],
) -> list[MatchCarrinho]:
    """Busca itens mencionados no carrinho e retorna matches."""
    from src.extratores.troca_extrator import (  # noqa: PLC0415 — shared helpers
        _adicionar_ou_atualizar_resultado,
        _verificar_match_nome,
        _verificar_match_variante,
    )

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
