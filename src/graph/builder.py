"""Builder do grafo LangGraph.

Constroi e compila o grafo de atendimento com nodes,
arestas condicionais e roteamento por intent.

Example:
    ```python
    from langgraph.checkpoint.sqlite import SqliteSaver
    from src.graph.builder import criar_graph
    import sqlite3

    conn = sqlite3.connect(':memory:')
    checkpointer = SqliteSaver(conn)
    graph = criar_graph(checkpointer)
    ```
"""

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph

from src.graph.handlers.desconhecido import node_handler_desconhecido
from src.graph.nodes import (
    _criar_node_router,
    node_clarificacao,
    node_extrator,
    node_handler_cancelar,
    node_handler_carrinho,
    node_handler_confirmar,
    node_handler_pedir,
    node_handler_remover,
    node_handler_saudacao,
    node_handler_trocar,
    node_verificar_etapa,
)
from src.graph.state import State
from src.roteador.service import ClassificadorIntencoes

# Mapping centralizado: intent → node name
# Fonte unica de verdade para edges condicionais
_INTENT_TO_NODE: dict[str, str] = {
    'saudacao': 'handler_saudacao',
    'pedir': 'extrator',
    'carrinho': 'handler_carrinho',
    'confirmar': 'handler_confirmar',
    'cancelar': 'handler_cancelar',
    'remover': 'handler_remover',
    'trocar': 'handler_trocar',
    'desconhecido': 'handler_desconhecido',
}

# Todos os nodes handlers (para edges para END)
_HANDLER_NODES: list[str] = [
    'handler_saudacao',
    'handler_carrinho',
    'handler_confirmar',
    'handler_cancelar',
    'handler_remover',
    'handler_trocar',
    'handler_desconhecido',
    'handler_pedir',
]


def _decidir_entrada(state: State) -> str:
    """Decide qual no executar baseado na etapa atual."""
    if state.get('etapa') == 'clarificando_variante':
        return 'clarificacao'
    return 'router'


def _decidir_por_intent(state: State) -> str:
    """Decide qual handler executar baseado na intencao classificada."""
    intent = state.get('intent', '')
    return _INTENT_TO_NODE.get(intent, 'handler_saudacao')


def criar_graph(
    checkpointer: SqliteSaver,
    classificador: ClassificadorIntencoes,
) -> StateGraph:
    """Constroi e compila o grafo de atendimento.

    Args:
        checkpointer: Checkpointer para persistencia de estado (SqliteSaver).
        classificador: Instancia de ClassificadorIntencoes injetada.

    Returns:
        Grafo compilado pronto para uso com invoke().
    """
    node_router = _criar_node_router(classificador)
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
    builder.add_node('handler_remover', node_handler_remover)
    builder.add_node('handler_trocar', node_handler_trocar)
    builder.add_node('handler_desconhecido', node_handler_desconhecido)

    # 2. entry point + edge condicional de entrada
    builder.set_entry_point('verificar_etapa')
    builder.add_conditional_edges(
        'verificar_etapa',
        _decidir_entrada,
        {'clarificacao': 'clarificacao', 'router': 'router'},
    )

    # 3. edge condicional por intent (derivado do mapping centralizado)
    builder.add_conditional_edges(
        'router',
        _decidir_por_intent,
        _INTENT_TO_NODE,  # type: ignore[arg-type]
    )

    # 4. edges simples
    builder.add_edge('extrator', 'handler_pedir')
    for node_name in _HANDLER_NODES:
        builder.add_edge(node_name, END)
    builder.add_edge('clarificacao', END)

    # 5. compila
    return builder.compile(checkpointer=checkpointer)  # pyright: ignore[reportReturnType]
