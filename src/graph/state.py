"""Estado compartilhado do grafo de atendimento.

Define o TypedDict ``State`` utilizado por todos os nos do grafo
LangGraph para compartilhar informacoes durante o fluxo de atendimento.

Example:
    ```python
    from src.graph.state import State, ETAPAS, RetornoNode

    state: State = {
        'mensagem_atual': '',
        'intent': '',
        'itens_extraidos': [],
        'carrinho': [],
        'fila_clarificacao': [],
        'etapa': 'inicio',
        'resposta': '',
    }
    ```
"""

from typing import Literal, NotRequired, TypedDict


ETAPAS = Literal[
    'inicio',
    'clarificando_variante',
    'confirmando',
    'pedindo',
    'carrinho',
    'saudacao',
    'finalizado',
    'coletando',
]
"""Literal com todas as etapas validas do fluxo de atendimento."""


class State(TypedDict):
    """Estado compartilhado entre os nos do grafo de atendimento.

    Attributes:
        mensagem_atual: Ultima mensagem recebida do usuario.
        intent: Intencao classificada da mensagem atual.
        confidence: Confidence da classificacao (0-1).
        itens_extraidos: Lista de dicts de itens extraidos da mensagem.
        carrinho: Lista de dicts de itens adicionados ao pedido.
        fila_clarificacao: Fila de dicts de itens que precisam de clarificacao.
        etapa: Etapa atual do fluxo de atendimento.
        resposta: Resposta gerada para o usuario.
        tentativas_clarificacao: Contador de tentativas para o item atual.
    """

    mensagem_atual: str
    intent: str
    confidence: float
    itens_extraidos: list
    carrinho: list
    fila_clarificacao: list
    etapa: ETAPAS
    resposta: str
    tentativas_clarificacao: int


class RetornoNode(TypedDict, total=False):
    """Tipo de retorno parcial dos nos do grafo.

    Cada no retorna apenas as chaves que atualiza.
    O LangGraph faz o merge com o ``State`` completo.

    Campos identicos ao ``State`` — mantidos aqui para type safety
    com total=False (todos opcionais).
    """

    mensagem_atual: NotRequired[str]
    intent: NotRequired[str]
    confidence: NotRequired[float]
    itens_extraidos: NotRequired[list]
    carrinho: NotRequired[list]
    fila_clarificacao: NotRequired[list]
    etapa: NotRequired[ETAPAS]
    resposta: NotRequired[str]
    tentativas_clarificacao: NotRequired[int]
