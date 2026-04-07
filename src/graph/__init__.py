"""Grafo de fluxo de atendimento do Pede AI.

Define o estado compartilhado e os nós de processamento
para o grafo de atendimento (LangGraph).

Example:
    ```python
    from src.graph import State, MODOS, ACOES
    from src.graph import node_verificar_modo, node_handler_saudacao
    from src.graph import criar_graph
    ```
"""

from .builder import criar_graph
from .nodes import (
    node_clarificacao,
    node_extrator,
    node_handler_cancelar,
    node_handler_carrinho,
    node_handler_confirmar,
    node_handler_pedir,
    node_handler_saudacao,
    node_router,
    node_verificar_modo,
)
from .state import MODOS, ACOES, State

__all__ = [
    'ACOES',
    'MODOS',
    'State',
    'criar_graph',
    'node_clarificacao',
    'node_extrator',
    'node_handler_cancelar',
    'node_handler_carrinho',
    'node_handler_confirmar',
    'node_handler_pedir',
    'node_handler_saudacao',
    'node_router',
    'node_verificar_modo',
]
