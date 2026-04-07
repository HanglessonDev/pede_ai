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

from src.graph.contexto import node_resolver_contexto
from src.graph.handlers.desconhecido import node_handler_desconhecido
from src.graph.nodes import (
    _criar_node_router,
    node_clarificacao,
    node_dispatcher_modificar,
    node_extrator,
    node_handler_adicionar,
    node_handler_cancelar,
    node_handler_carrinho,
    node_handler_confirmar,
    node_handler_pedir,
    node_handler_remover,
    node_handler_saudacao,
    node_handler_trocar,
    node_verificar_modo,
)
from src.graph.state import State
from src.roteador.service import ClassificadorIntencoes

# Mapping centralizado: intent → node name
# Fonte unica de verdade para edges condicionais
_INTENT_TO_NODE: dict[str, str] = {
    'saudacao': 'handler_saudacao',
    'pedir': 'extrator',
    'modificar_pedido': 'dispatcher_modificar',
    'finalizar_pedido': 'handler_confirmar',
    'carrinho': 'handler_carrinho',
    'confirmar': 'handler_confirmar',
    'cancelar': 'handler_cancelar',
    'remover': 'handler_remover',
    'trocar': 'handler_trocar',
    'desconhecido': 'handler_desconhecido',
    # Intents classificadas mas sem handler dedicado ainda
    'negar': 'handler_desconhecido',
    'duvida': 'handler_desconhecido',
}

# Mapping: acao do dispatcher → node handler
_ACAO_TO_NODE: dict[str, str] = {
    'adicionar_item': 'handler_adicionar',
    'remover_item': 'handler_remover',
    'trocar_variante': 'handler_trocar',
    'sem_entidade': 'handler_desconhecido',
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
    'handler_adicionar',
]


def _decidir_entrada(state: State) -> str:
    """Decide qual no executar baseado no modo atual."""
    if state.get('modo') == 'clarificando':
        return 'clarificacao'
    return 'router'


def _decidir_por_intent(state: State) -> str:
    """Decide qual handler executar baseado na intencao classificada."""
    intent = state.get('intent', '')
    if intent == '':
        return 'router'
    return _INTENT_TO_NODE.get(intent, 'handler_desconhecido')


def _decidir_por_acao(state: State) -> str:
    """Decide qual handler executar baseado na acao do dispatcher."""
    acao = state.get('acao', 'sem_entidade')
    return _ACAO_TO_NODE.get(acao, 'handler_desconhecido')


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
    builder.add_node('verificar_modo', node_verificar_modo)
    builder.add_node('resolver_contexto', node_resolver_contexto)
    builder.add_node('router', node_router)
    builder.add_node('extrator', node_extrator)
    builder.add_node('dispatcher_modificar', node_dispatcher_modificar)
    builder.add_node('clarificacao', node_clarificacao)
    builder.add_node('handler_pedir', node_handler_pedir)
    builder.add_node('handler_adicionar', node_handler_adicionar)
    builder.add_node('handler_saudacao', node_handler_saudacao)
    builder.add_node('handler_carrinho', node_handler_carrinho)
    builder.add_node('handler_confirmar', node_handler_confirmar)
    builder.add_node('handler_cancelar', node_handler_cancelar)
    builder.add_node('handler_remover', node_handler_remover)
    builder.add_node('handler_trocar', node_handler_trocar)
    builder.add_node('handler_desconhecido', node_handler_desconhecido)

    # 2. entry point + edge condicional de entrada
    builder.set_entry_point('verificar_modo')
    builder.add_conditional_edges(
        'verificar_modo',
        _decidir_entrada,
        {'clarificacao': 'clarificacao', 'resolver_contexto': 'resolver_contexto'},
    )

    # 3. resolver_contexto → handler direto ou router
    builder.add_conditional_edges(
        'resolver_contexto',
        _decidir_por_intent,
        {**{v: v for v in _INTENT_TO_NODE.values()}, 'router': 'router'},
    )

    # 4. edge condicional por intent (derivado do mapping centralizado)
    handler_destinos = {v: v for v in _INTENT_TO_NODE.values()}
    builder.add_conditional_edges(
        'router',
        _decidir_por_intent,
        handler_destinos,  # type: ignore[arg-type]
    )

    # 5. dispatcher → handlers por ação
    builder.add_conditional_edges(
        'dispatcher_modificar',
        _decidir_por_acao,
        {v: v for v in _ACAO_TO_NODE.values()},
    )

    # 6. edges simples
    builder.add_edge('extrator', 'handler_pedir')
    for node_name in _HANDLER_NODES:
        builder.add_edge(node_name, END)
    builder.add_edge('clarificacao', END)

    # 7. compila
    return builder.compile(checkpointer=checkpointer)  # pyright: ignore[reportReturnType]
