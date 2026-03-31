"""Grafo de fluxo de atendimento do Pede AI.

Define o estado compartilhado e os nós de processamento
para o grafo de atendimento (LangGraph).

Example:
    >>> from src.graph import State
    >>> from src.graph import node_router, node_handler_saudacao
"""

from .nodes import (
    node_extrator,
    node_handler_cancelar,
    node_handler_carrinho,
    node_handler_confirmar,
    node_handler_pedir,
    node_handler_saudacao,
    node_router,
)
from .state import ETAPAS, State

__all__ = [
    'ETAPAS',
    'State',
    'node_extrator',
    'node_handler_cancelar',
    'node_handler_carrinho',
    'node_handler_confirmar',
    'node_handler_pedir',
    'node_handler_saudacao',
    'node_router',
]
