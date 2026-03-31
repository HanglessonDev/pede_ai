"""
Configuração do Pede AI.

Pacote centralizado para acesso a prompts, cardápio e configurações do tenant.

Example:
    >>> from src.config import get_prompt, get_cardapio, get_tenant_nome
    >>> prompt = get_prompt('classificador_intencoes')
    >>> cardapio = get_cardapio()
    >>> nome = get_tenant_nome()
"""

from src.config.cardapio import (
    get_cardapio,
    get_item_por_id,
    get_itens_por_categoria,
    get_nome_item,
    get_observacoes_genericas,
    get_preco_item,
    get_remocoes_genericas,
    get_variantes,
)
from src.config.prompts import (
    get_intencoes_validas,
    get_prompt,
    get_tenant_id,
    get_tenant_info,
    get_tenant_nome,
)

__all__ = [
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
