"""Builder do grafo LangGraph.

Constroi e compila o grafo de atendimento com nodes,
arestas condicionais e roteamento por intent.

Example:
    >>> from langgraph.checkpoint.sqlite import SqliteSaver
    >>> from src.graph.builder import criar_graph
    >>> import sqlite3
    >>> conn = sqlite3.connect(':memory:')
    >>> checkpointer = SqliteSaver(conn)
    >>> graph = criar_graph(checkpointer)
"""

from langgraph.graph import END, StateGraph

from src.graph.handlers.desconhecido import node_handler_desconhecido
from src.graph.nodes import (
    node_clarificacao,
    node_extrator,
    node_handler_cancelar,
    node_handler_carrinho,
    node_handler_confirmar,
    node_handler_pedir,
    node_handler_saudacao,
    node_router,
    node_verificar_etapa,
)
from src.graph.state import State


def _decidir_entrada(state: State) -> str:
    if state.get('etapa') == 'clarificando_variante':
        return 'clarificacao'
    return 'router'


def _decidir_por_intent(state: State) -> str:
    intent = state.get('intent', '')

    mapeamento = {
        'saudacao': 'handler_saudacao',
        'pedir': 'extrator',
        'carrinho': 'handler_carrinho',
        'confirmar': 'handler_confirmar',
        'cancelar': 'handler_cancelar',
        'desconhecido': 'handler_desconhecido',
    }
    return mapeamento.get(intent, 'handler_saudacao')


def criar_graph(checkpointer):
    """Constroi e compila o grafo de atendimento.

    Args:
        checkpointer: Checkpointer para persistência de estado (SqliteSaver).

    Returns:
        Grafo compilado pronto para uso com invoke().

    Example:
        >>> from langgraph.checkpoint.sqlite import SqliteSaver
        >>> import sqlite3
        >>> conn = sqlite3.connect('./pede_ai.db')
        >>> graph = criar_graph(SqliteSaver(conn))
        >>> config = {'configurable': {'thread_id': 'usuario_001'}}
        >>> result = graph.invoke({'mensagem_atual': 'oi'}, config)
    """
    builder = StateGraph(State)

    # 1. registra nodes
    builder.add_node('verificar_etapa', node_verificar_etapa)
    builder.add_node('router', node_router)
    builder.add_node('extrator', node_extrator)
    builder.add_node('clarificacao', node_clarificacao)
    builder.add_node('handler_pedir', node_handler_pedir)
    builder.add_node('handler_saudacao', node_handler_saudacao)
    builder.add_node('handler_carrinho', node_handler_carrinho)
    builder.add_node('handler_confirmar', node_handler_confirmar)
    builder.add_node('handler_cancelar', node_handler_cancelar)
    builder.add_node('handler_desconhecido', node_handler_desconhecido)

    # 2. entry point + edge condicional de entrada
    builder.set_entry_point('verificar_etapa')
    builder.add_conditional_edges(
        'verificar_etapa',
        _decidir_entrada,
        {'clarificacao': 'clarificacao', 'router': 'router'},
    )

    # 3. edge condicional por intent (após router)
    builder.add_conditional_edges(
        'router',
        _decidir_por_intent,
        {
            'extrator': 'extrator',
            'handler_saudacao': 'handler_saudacao',
            'handler_carrinho': 'handler_carrinho',
            'handler_confirmar': 'handler_confirmar',
            'handler_cancelar': 'handler_cancelar',
            'handler_desconhecido': 'handler_desconhecido',
        },
    )

    # 4. edges simples
    builder.add_edge('extrator', 'handler_pedir')  # extrator → handler
    builder.add_edge('handler_pedir', END)
    builder.add_edge('handler_saudacao', END)
    builder.add_edge('handler_carrinho', END)
    builder.add_edge('handler_cancelar', END)
    builder.add_edge('clarificacao', END)
    builder.add_edge('handler_confirmar', END)
    builder.add_edge('handler_desconhecido', END)

    # 5. compila
    return builder.compile(checkpointer=checkpointer)
