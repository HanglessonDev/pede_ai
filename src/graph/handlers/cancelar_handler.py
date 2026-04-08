"""Handler de cancelamento de pedido.

Limpa o carrinho e reseta o estado do fluxo.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.graph.handlers.carrinho import Carrinho
from src.graph.state import RetornoNode

if TYPE_CHECKING:
    from src.observabilidade.loggers import ObservabilidadeLoggers


def processar_cancelamento(
    carrinho_dicts: list[dict],
    loggers: ObservabilidadeLoggers | None = None,
    thread_id: str = '',
    turn_id: str = '',
) -> RetornoNode:
    """Processa cancelamento do pedido.

    Args:
        carrinho_dicts: Lista de dicts do carrinho no State.
        loggers: Loggers de observabilidade (opcional).
        thread_id: ID da sessao (opcional).
        turn_id: ID do turno (opcional).

    Returns:
        Dicionario com ``resposta``, ``etapa`` e ``carrinho`` atualizados.
    """
    if not carrinho_dicts:
        return {'resposta': 'Não há pedido para cancelar.', 'modo': 'ocioso'}

    carrinho = Carrinho.from_state_dicts(carrinho_dicts)
    total = carrinho.total_reais()

    resultado: RetornoNode = {
        'resposta': f'Pedido cancelado. Total descartado: R$ {total:.2f}',
        'modo': 'ocioso',
        'carrinho': [],
        'fila_clarificacao': [],
        'tentativas_clarificacao': 0,
    }

    if loggers and loggers.negocio is not None:
        loggers.negocio.registrar(
            thread_id=thread_id,
            turn_id=turn_id,
            evento='cancelar',
            carrinho_size=0,
            preco_total_centavos=int(total * 100),
            intent='cancelar',
            resposta=resultado['resposta'],
            tentativas_clarificacao=0,
        )

    return resultado
