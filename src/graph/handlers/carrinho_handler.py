"""Handler de exibicao do carrinho.

Lista todos os itens no carrinho com quantidades e precos.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.graph.handlers.carrinho import Carrinho
from src.graph.state import RetornoNode

if TYPE_CHECKING:
    from src.observabilidade.loggers import ObservabilidadeLoggers


def processar_carrinho(
    carrinho_dicts: list[dict],
    loggers: ObservabilidadeLoggers | None = None,
    thread_id: str = '',
    turn_id: str = '',
) -> RetornoNode:
    """Gera resposta com o conteudo atual do carrinho.

    Args:
        carrinho_dicts: Lista de dicts do carrinho no State.
        loggers: Loggers de observabilidade (opcional).
        thread_id: ID da sessao (opcional).
        turn_id: ID do turno (opcional).

    Returns:
        Dicionario com ``resposta`` e ``etapa`` atualizados.
    """
    if not carrinho_dicts:
        return {'resposta': 'Seu carrinho esta vazio!', 'modo': 'coletando'}

    carrinho = Carrinho.from_state_dicts(carrinho_dicts)
    resposta = 'Seu pedido:\n' + carrinho.formatar()

    resultado: RetornoNode = {'resposta': resposta, 'modo': 'coletando'}

    if loggers and loggers.negocio is not None:
        preco_total = sum(i.get('preco_centavos', 0) for i in carrinho_dicts)
        loggers.negocio.registrar(
            thread_id=thread_id,
            turn_id=turn_id,
            evento='carrinho',
            carrinho_size=len(carrinho_dicts),
            preco_total_centavos=preco_total,
            intent='carrinho',
            resposta=resposta,
            tentativas_clarificacao=0,
        )

    return resultado
