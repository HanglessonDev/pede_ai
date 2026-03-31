"""
Módulo de Cardápio do Pede AI.

Fornece acesso centralizado aos dados do cardápio.

Example:
    >>> from src.config import get_cardapio, get_item_por_id, get_variantes
    >>> cardapio = get_cardapio()
    >>> item = get_item_por_id('lanche_001')
    >>> variantes = get_variantes('lanche_001')
"""

from __future__ import annotations

from pathlib import Path

import yaml


CONFIG_DIR = Path(__file__).parent.parent.parent / 'config'


class _CardapioCache:
    """Cache interno para dados do cardápio."""

    _cardapio: dict | None = None
    _itens_por_id: dict[str, dict] | None = None

    @classmethod
    def carregar_cardapio(cls) -> dict:
        """Carrega cardapio.yml com cache."""
        if cls._cardapio is None:
            with open(CONFIG_DIR / 'cardapio.yml', encoding='utf-8') as f:
                cls._cardapio = yaml.safe_load(f)
        assert cls._cardapio is not None
        return cls._cardapio

    @classmethod
    def indexar_itens_por_id(cls) -> dict[str, dict]:
        """Cria índice de itens do cardápio por ID."""
        if cls._itens_por_id is None:
            cardapio = cls.carregar_cardapio()
            cls._itens_por_id = {item['id']: item for item in cardapio['itens']}
        return cls._itens_por_id


# ── API de Cardápio ────────────────────────────────────────────────────────
def get_cardapio() -> dict:
    """
    Retorna o cardápio completo.

    Returns:
        Dicionário com todos os itens, remoções e observações.

    Example:
        ```python
        cardapio = get_cardapio()
        len(cardapio['itens'])  # 7
        ```
    """
    return _CardapioCache.carregar_cardapio()


def get_item_por_id(item_id: str) -> dict | None:
    """
    Busca um item do cardápio pelo ID.

    Args:
        item_id: ID do item (ex: 'lanche_001').

    Returns:
        Dados do item ou None se não encontrado.

    Example:
        ```python
        item = get_item_por_id('lanche_001')
        # {'id': 'lanche_001', 'nome': 'Hambúrguer', ...}
        ```
    """
    return _CardapioCache.indexar_itens_por_id().get(item_id)


def get_itens_por_categoria(categoria: str) -> list[dict]:
    """
    Retorna todos os itens de uma categoria.

    Args:
        categoria: Nome da categoria (ex: 'lanche', 'bebida', 'acompanhamento').

    Returns:
        Lista de itens da categoria.

    Example:
        ```python
        itens = get_itens_por_categoria('lanche')
        # [{'id': 'lanche_002', 'nome': 'X-Salada', ...}, ...]
        ```
    """
    cardapio = _CardapioCache.carregar_cardapio()
    return [item for item in cardapio['itens'] if item['categoria'] == categoria]


def get_remocoes_genericas() -> list[str]:
    """
    Retorna lista de palavras de remoção genéricas.

    Returns:
        Lista de palavras como 'sem', 'tira', 'retira', etc.
    """
    return _CardapioCache.carregar_cardapio()['remocoes_genericas']


def get_observacoes_genericas() -> list[str]:
    """
    Retorna lista de observações genéricas.

    Returns:
        Lista de observações como 'bem passado', 'ao ponto', etc.
    """
    return _CardapioCache.carregar_cardapio()['observacoes_genericas']


def get_variantes(item_id: str) -> list[str]:
    """
    Retorna lista de opções de variante de um item.

    Args:
        item_id: ID do item (ex: 'lanche_001').

    Returns:
        Lista de nomes de variantes (ex: ['simples', 'duplo', 'triplo']).

    Example:
        >>> get_variantes('lanche_001')
        ['simples', 'duplo', 'triplo']
    """
    item_data = get_item_por_id(item_id)
    if item_data is not None:
        return [v['opcao'] for v in item_data.get('variantes', [])]
    return []


def get_preco_item(item_id: str) -> int | None:
    """
    Retorna preço base do item (sem variante).

    Args:
        item_id: ID do item (ex: 'lanche_001').

    Returns:
        Preço em centavos ou None se não existir.

    Example:
        >>> get_preco_item('lanche_001')
        1500
    """
    item = get_item_por_id(item_id)
    return item.get('preco') if item else None


def get_nome_item(item_id: str) -> str | None:
    """
    Retorna nome do item.

    Args:
        item_id: ID do item (ex: 'lanche_001').

    Returns:
        Nome do item ou None se não existir.

    Example:
        >>> get_nome_item('lanche_001')
        'Hamburguer'
    """
    item = get_item_por_id(item_id)
    return item.get('nome') if item else None


__all__ = [
    'get_cardapio',
    'get_item_por_id',
    'get_itens_por_categoria',
    'get_nome_item',
    'get_observacoes_genericas',
    'get_preco_item',
    'get_remocoes_genericas',
    'get_variantes',
]
