"""Testes para o handler desconhecido."""

from src.graph.handlers.desconhecido import node_handler_desconhecido
from src.graph.state import State


def test_handler_desconhecido_retorna_mensagem_clarificacao():
    """Handler desconhecido deve pedir esclarecimento."""
    state: State = {
        'mensagem_atual': 'xyz123',
        'intent': 'desconhecido',
        'confidence': 0.0,
        'itens_extraidos': [],
        'carrinho': [],
        'fila_clarificacao': [],
        'modo': 'ocioso',
        'resposta': '',
        'tentativas_clarificacao': 0,
    }

    result = node_handler_desconhecido(state)

    assert 'resposta' in result
    assert 'Não entendi' in result['resposta']
    assert result['modo'] == 'ocioso'
