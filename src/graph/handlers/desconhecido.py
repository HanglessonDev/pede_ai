"""Handler para intents desconhecidas."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.graph.state import RetornoNode, State

if TYPE_CHECKING:
    from src.observabilidade.loggers import ObservabilidadeLoggers


def node_handler_desconhecido(
    state: State,
    loggers: ObservabilidadeLoggers | None = None,
    thread_id: str = '',
    turn_id: str = '',
) -> RetornoNode:
    """Gera resposta de esclarecimento para intents desconhecidas.

    Args:
        state: Estado atual do grafo de atendimento.
        loggers: Loggers de observabilidade (opcional).
        thread_id: ID da sessao (opcional).
        turn_id: ID do turno (opcional).

    Returns:
        Dicionário com ``resposta`` e ``etapa`` atualizados.
    """
    resposta = (
        'Não entendi. Pode reformular sua mensagem? '
        'Posso ajudar com pedidos, ver o carrinho, confirmar ou cancelar.'
    )
    resultado: RetornoNode = {
        'resposta': resposta,
        'modo': 'ocioso',
    }

    if loggers and loggers.negocio is not None:
        carrinho = state.get('carrinho', [])
        loggers.negocio.registrar(
            thread_id=thread_id,
            turn_id=turn_id,
            evento='desconhecido',
            carrinho_size=len(carrinho),
            preco_total_centavos=0,
            intent='desconhecido',
            resposta=resposta,
            tentativas_clarificacao=state.get('tentativas_clarificacao', 0),
        )

    return resultado
