"""
Configuração do Pede AI.

Fornece acesso centralizado a prompts e configurações.

Example:
    >>> from src.config import get_prompt, get_intencoes_validas, get_tenant_nome
    >>> prompt = get_prompt('classificador_intencoes')
    >>> nome = get_tenant_nome()
"""

from __future__ import annotations

from pathlib import Path

import yaml


CONFIG_DIR = Path(__file__).parent.parent / 'config'


# ── Re-exports de cardapio.py (compatibilidade) ──────────────────────────────
from src.cardapio import (
    get_cardapio,
    get_item_por_id,
    get_itens_por_categoria,
    get_nome_item,
    get_observacoes_genericas,
    get_preco_item,
    get_remocoes_genericas,
    get_variantes,
)


class _PromptsCache:
    """Cache interno para prompts."""

    _prompts: dict | None = None

    @classmethod
    def carregar_prompts(cls) -> dict:
        """Carrega prompts.yml com cache."""
        if cls._prompts is None:
            with open(CONFIG_DIR / 'prompts.yml', encoding='utf-8') as f:
                cls._prompts = yaml.safe_load(f)
        assert cls._prompts is not None
        return cls._prompts


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
        ```python
        from src.config import get_prompt

        prompt = get_prompt('classificador_intencoes')
        ```
    """
    return _PromptsCache.carregar_prompts()[nome]['prompt']


def get_intencoes_validas() -> list[str]:
    """Retorna lista de intenções válidas."""
    return _PromptsCache.carregar_prompts()['classificador_intencoes'][
        'intencoes_validas'
    ]


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
    cardapio = get_cardapio()
    return {
        'tenant_id': cardapio['tenant_id'],
        'tenant_nome': cardapio['tenant_nome'],
    }


def get_tenant_id() -> str:
    """Retorna o ID do tenant."""
    return get_cardapio()['tenant_id']


def get_tenant_nome() -> str:
    """Retorna o nome do tenant (restaurante)."""
    return get_cardapio()['tenant_nome']


# ── exports ────────────────────────────────────────────────────────────────
__all__ = [
    'CONFIG_DIR',
    'get_cardapio',
    'get_intencoes_validas',
    'get_item_por_id',
    'get_itens_por_categoria',
    'get_nome_item',
    'get_observacoes_genericas',
    'get_preco_item',
    'get_prompt',
    'get_remocoes_genericas',
    'get_tenant_id',
    'get_tenant_info',
    'get_tenant_nome',
    'get_variantes',
]

if __name__ == '__main__':
    print(get_tenant_info())
    print(get_item_por_id('lanche_001'))
    print(get_prompt('classificador_intencoes')[:50])
