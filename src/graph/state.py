"""Estado compartilhado do grafo de atendimento.

Define o TypedDict ``State`` utilizado por todos os nós do grafo
LangGraph para compartilhar informações durante o fluxo de atendimento.

Example:
    >>> from src.graph.state import State, ETAPAS
    >>> state: State = {
    ...     'mensagem_atual': '',
    ...     'intent': '',
    ...     'itens_extraidos': [],
    ...     'carrinho': [],
    ...     'fila_clarificacao': [],
    ...     'etapa': 'inicio',
    ...     'resposta': '',
    ... }
"""

from typing import Literal, TypedDict

ETAPAS = Literal[
    'inicio', 'clarificando_variante', 'confirmando', 'pedindo', 'carrinho'
]
"""Literal com todas as etapas válidas do fluxo de atendimento."""


class State(TypedDict):
    """Estado compartilhado entre os nós do grafo de atendimento.

    Attributes:
        mensagem_atual: Última mensagem recebida do usuário.
        intent: Intenção classificada da mensagem atual.
        itens_extraidos: Lista de itens extraídos da mensagem.
        carrinho: Lista de itens adicionados ao pedido.
        fila_clarificacao: Fila de itens que precisam de clarificação.
        etapa: Etapa atual do fluxo de atendimento.
        resposta: Resposta gerada para o usuário.
        tentativas_clarificacao: Contador de tentativas para o item atual em clarificação.
    """

    mensagem_atual: str
    intent: str
    itens_extraidos: list
    carrinho: list
    fila_clarificacao: list
    etapa: str
    resposta: str
    tentativas_clarificacao: int
