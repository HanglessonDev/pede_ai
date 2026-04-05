"""Handler de cancelamento de pedido.

Limpa o carrinho e reseta o estado do fluxo.
"""

from __future__ import annotations

from src.graph.handlers.carrinho import Carrinho
from src.graph.state import RetornoNode


def processar_cancelamento(carrinho_dicts: list[dict]) -> RetornoNode:
    """Processa cancelamento do pedido.

    Args:
        carrinho_dicts: Lista de dicts do carrinho no State.

    Returns:
        Dicionario com ``resposta``, ``etapa`` e ``carrinho`` atualizados.
    """
    if not carrinho_dicts:
        return {'resposta': 'Não há pedido para cancelar.', 'etapa': 'inicio'}

    carrinho = Carrinho.from_state_dicts(carrinho_dicts)
    total = carrinho.total_reais()

    return {
        'resposta': f'Pedido cancelado. Total descartado: R$ {total:.2f}',
        'etapa': 'inicio',
        'carrinho': [],
        'fila_clarificacao': [],
        'tentativas_clarificacao': 0,
    }
