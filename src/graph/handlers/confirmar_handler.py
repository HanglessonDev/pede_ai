"""Handler de confirmacao de pedido.

Calcula o total do carrinho, gera mensagem de confirmacao
e limpa o carrinho apos o pedido ser finalizado.
"""

from __future__ import annotations

from src.graph.handlers.carrinho import Carrinho
from src.graph.state import RetornoNode


def processar_confirmacao(carrinho_dicts: list[dict]) -> RetornoNode:
    """Processa confirmacao do pedido pelo usuario.

    Args:
        carrinho_dicts: Lista de dicts do carrinho no State.

    Returns:
        Dicionario com ``resposta``, ``etapa`` e ``carrinho`` atualizados.
    """
    if not carrinho_dicts:
        return {'resposta': 'Não há pedido para confirmar.'}

    carrinho = Carrinho.from_state_dicts(carrinho_dicts)
    total = carrinho.total_reais()

    return {
        'resposta': f'Pedido confirmado! Total: R$ {total:.2f}',
        'etapa': 'finalizado',
        'carrinho': [],
    }
