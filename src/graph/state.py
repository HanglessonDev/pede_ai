from typing import Literal, TypedDict

ETAPAS = Literal['inicio', 'clarificando_variante', 'confirmando', 'pedindo', 'carrinho']

class State(TypedDict):
    mensagem_atual: str
    intent: str
    itens_extraidos: list
    carrinho: list
    fila_clarificacao: list
    etapa: str
    resposta: str
