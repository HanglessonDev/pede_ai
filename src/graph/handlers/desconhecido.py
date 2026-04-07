"""Handler para intents desconhecidas."""

from src.graph.state import RetornoNode, State


def node_handler_desconhecido(state: State) -> RetornoNode:
    """Gera resposta de esclarecimento para intents desconhecidas.

    Args:
        state: Estado atual do grafo de atendimento.

    Returns:
        Dicionário com ``resposta`` e ``etapa`` atualizados.
    """
    return {
        'resposta': 'Não entendi. Pode reformular sua mensagem? '
        'Posso ajudar com pedidos, ver o carrinho, confirmar ou cancelar.',
        'modo': 'ocioso',
    }
