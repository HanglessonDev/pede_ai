"""
Configuração do Pede AI.

Fornece acesso centralizado a prompts e configurações.

Example:
    >>> from src.config import get_prompt, get_cardapio, get_item_por_id
    >>> prompt = get_prompt('classificador_intencoes')
    >>> cardapio = get_cardapio()
    >>> item = get_item_por_id('lanche_001')
"""

from __future__ import annotations

from pathlib import Path

import yaml


CONFIG_DIR = Path(__file__).parent.parent / 'config'


class _ConfigCache:
    """Cache interno para configurações carregadas."""

    _prompts: dict | None = None
    _cardapio: dict | None = None
    _itens_por_id: dict[str, dict] | None = None

    @classmethod
    def carregar_prompts(cls) -> dict:
        """Carrega prompts.yml com cache."""
        if cls._prompts is None:
            with open(CONFIG_DIR / 'prompts.yml', encoding='utf-8') as f:
                cls._prompts = yaml.safe_load(f)
        assert cls._prompts is not None
        return cls._prompts

    @classmethod
    def carregar_cardapio(cls) -> dict:
        """
        Carrega cardapio.yml com cache.

        Retorna dicionário com: tenant_id, tenant_nome, itens, etc.
        """
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


# ── API de Prompts ─────────────────────────────────────────────────────────
def get_prompt(nome: str) -> str:
    """
    Retorna um prompt por nome.

    Args:
        nome: Nome do prompt (ex: 'classificador_intencoes').

    Returns:
        O conteúdo do prompt.

    Raises:
        KeyError: Se o prompt não existir.

    Example:
        >>> get_prompt('classificador_intencoes')
        'Classifique a intenção...'
    """
    return _ConfigCache.carregar_prompts()[nome]['prompt']


def get_intencoes_validas() -> list[str]:
    """Retorna lista de intenções válidas."""
    return _ConfigCache.carregar_prompts()['classificador_intencoes'][
        'intencoes_validas'
    ]


# ── API de Cardápio ────────────────────────────────────────────────────────
def get_cardapio() -> dict:
    """
    Retorna o cardápio completo.

    Returns:
        Dicionário com todos os itens, remoções e observações.

    Example:
        >>> cardapio = get_cardapio()
        >>> len(cardapio['itens'])
        7
    """
    return _ConfigCache.carregar_cardapio()


def get_item_por_id(item_id: str) -> dict | None:
    """
    Busca um item do cardápio pelo ID.

    Args:
        item_id: ID do item (ex: 'lanche_001').

    Returns:
        Dados do item ou None se não encontrado.

    Example:
        >>> get_item_por_id('lanche_001')
        {'id': 'lanche_001', 'nome': 'Hambúrguer', ...}
    """
    return _ConfigCache.indexar_itens_por_id().get(item_id)


def get_itens_por_categoria(categoria: str) -> list[dict]:
    """
    Retorna todos os itens de uma categoria.

    Args:
        categoria: Nome da categoria (ex: 'lanche', 'bebida', 'acompanhamento').

    Returns:
        Lista de itens da categoria.

    Example:
        >>> get_itens_por_categoria('lanche')
        [{'id': 'lanche_002', 'nome': 'X-Salada', ...}, ...]
    """
    cardapio = _ConfigCache.carregar_cardapio()
    return [item for item in cardapio['itens'] if item['categoria'] == categoria]


def get_remocoes_genericas() -> list[str]:
    """
    Retorna lista de palavras de remoção genéricas.

    Returns:
        Lista de palavras como 'sem', 'tira', 'retira', etc.
    """
    return _ConfigCache.carregar_cardapio()['remocoes_genericas']


def get_observacoes_genericas() -> list[str]:
    """
    Retorna lista de observações genéricas.

    Returns:
        Lista de observações como 'bem passado', 'ao ponto', etc.
    """
    return _ConfigCache.carregar_cardapio()['observacoes_genericas']


# ── API de Tenant ──────────────────────────────────────────────────────────
def get_tenant_info() -> dict[str, str]:
    """
    Retorna informações do tenant (restaurante).

    Returns:
        Dicionário com tenant_id e tenant_nome.

    Example:
        >>> get_tenant_info()
        {'tenant_id': 'restaurante_teste', 'tenant_nome': 'Lanchonete do Zé'}
    """
    cardapio = _ConfigCache.carregar_cardapio()
    return {
        'tenant_id': cardapio['tenant_id'],
        'tenant_nome': cardapio['tenant_nome'],
    }


def get_tenant_id() -> str:
    """
    Retorna o ID do tenant.

    Returns:
        ID do tenant.
    """
    return _ConfigCache.carregar_cardapio()['tenant_id']


def get_tenant_nome() -> str:
    """
    Retorna o nome do tenant (restaurante).

    Returns:
        Nome do restaurante.
    """
    return _ConfigCache.carregar_cardapio()['tenant_nome']


# ── exports ────────────────────────────────────────────────────────────────
__all__ = [
    'CONFIG_DIR',
    'get_cardapio',
    'get_intencoes_validas',
    'get_item_por_id',
    'get_itens_por_categoria',
    'get_observacoes_genericas',
    'get_prompt',
    'get_remocoes_genericas',
    'get_tenant_id',
    'get_tenant_info',
    'get_tenant_nome',
]

if __name__ == '__main__':
    print(get_tenant_info())
    print(get_item_por_id('lanche_001'))
    print(get_prompt('classificador_intencoes')[:50])
