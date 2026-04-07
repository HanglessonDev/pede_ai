"""Handler de exibicao do carrinho.

Lista todos os itens no carrinho com quantidades e precos.
"""

from __future__ import annotations

from src.graph.handlers.carrinho import Carrinho
from src.graph.state import RetornoNode


def processar_carrinho(carrinho_dicts: list[dict]) -> RetornoNode:
    """Gera resposta com o conteudo atual do carrinho.

    Args:
        carrinho_dicts: Lista de dicts do carrinho no State.

    Returns:
        Dicionario com ``resposta`` e ``etapa`` atualizados.
    """
    if not carrinho_dicts:
        return {'resposta': 'Seu carrinho esta vazio!', 'modo': 'coletando'}

    carrinho = Carrinho.from_state_dicts(carrinho_dicts)
    resposta = 'Seu pedido:\n' + carrinho.formatar()
    return {'resposta': resposta, 'modo': 'coletando'}
