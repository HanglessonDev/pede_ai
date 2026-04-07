"""Estado compartilhado do grafo de atendimento.

Define o TypedDict ``State`` utilizado por todos os nos do grafo
LangGraph para compartilhar informacoes durante o fluxo de atendimento.

Example:
    ```python
    from src.graph.state import State, MODOS, ACOES, RetornoNode

    state: State = {
        'mensagem_atual': '',
        'intent': '',
        'itens_extraidos': [],
        'carrinho': [],
        'fila_clarificacao': [],
        'modo': 'ocioso',
        'resposta': '',
        'acao': 'adicionar_item',
        'origem_intent': '',
        'dados_extracao': {},
    }
    ```
"""

from typing import Literal, NotRequired, TypedDict


MODOS = Literal[
    'ocioso',
    'coletando',
    'clarificando',
    'confirmando',
    'finalizado',
]
"""Literal com todos os modos validos do fluxo de atendimento.

Renomeado de 'ETAPAS' para 'MODOS' no dispatcher.
'clarificando_variante' → 'clarificando'.
"""

ACOES = Literal[
    'adicionar_item',
    'remover_item',
    'trocar_variante',
    'sem_entidade',
]
"""Literal com todas as acoes validas do dispatcher."""


class State(TypedDict):
    """Estado compartilhado entre os nos do grafo de atendimento.

    Attributes:
        mensagem_atual: Ultima mensagem recebida do usuario.
        intent: Intencao classificada da mensagem atual.
        confidence: Confidence da classificacao (0-1).
        itens_extraidos: Lista de dicts de itens extraidos da mensagem.
        carrinho: Lista de dicts de itens adicionados ao pedido.
        fila_clarificacao: Fila de dicts de itens que precisam de clarificacao.
        modo: Modo atual do fluxo de atendimento (renomeado de 'etapa').
        resposta: Resposta gerada para o usuario.
        tentativas_clarificacao: Contador de tentativas para o item atual.
        acao: Decisao do dispatcher (novo).
        origem_intent: Origem da classificacao: 'contexto'|'lookup'|'rag_forte'|'llm_rag'|'llm_fixo' (novo).
        dados_extracao: Output de extrair_itens_troca() ou carrinho matches (novo).
        turn_id: Identificador do turno para correlacao de eventos de observabilidade.
    """

    mensagem_atual: str
    intent: str
    confidence: float
    itens_extraidos: list
    carrinho: list
    fila_clarificacao: list
    modo: MODOS
    resposta: str
    tentativas_clarificacao: int
    acao: ACOES
    origem_intent: str
    dados_extracao: dict
    turn_id: str


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
    modo: NotRequired[MODOS]
    resposta: NotRequired[str]
    tentativas_clarificacao: NotRequired[int]
    acao: NotRequired[ACOES]
    origem_intent: NotRequired[str]
    dados_extracao: NotRequired[dict]
    turn_id: NotRequired[str]
