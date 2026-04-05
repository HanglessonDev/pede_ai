"""Helper para construir set de nomes e aliases do cardapio."""

from __future__ import annotations

from src.extratores.normalizador import normalizar_para_busca


def build_itens_ids(cardapio: dict) -> frozenset[str]:
    """Constrói set de todos os nomes + aliases do cardápio.

    Args:
        cardapio: Dados do cardápio (get_cardapio()).

    Returns:
        Frozenset com nomes e aliases normalizados (lower).
    """
    ids: set[str] = set()
    for item in cardapio.get('itens', []):
        ids.add(normalizar_para_busca(item['nome']))
        for alias in item.get('aliases', []):
            ids.add(normalizar_para_busca(alias))
    return frozenset(ids)
