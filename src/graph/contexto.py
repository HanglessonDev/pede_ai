"""Resolução de intent por contexto conversacional.

Tenta resolver a intent do usuário com base no modo atual da conversa
antes de chamar o classificador. Se resolver: preenche intent +
origem_intent='contexto' — o grafo vai direto para o handler.

A tabela RESOLUCOES é a fonte de verdade: dados, não código.
Adicionar comportamento = adicionar uma linha.

Example:
    ```python
    from src.graph.contexto import node_resolver_contexto

    state = {'modo': 'confirmando', 'mensagem_atual': 'sim'}
    result = node_resolver_contexto(state)
    result['intent'] == 'finalizar_pedido'
    True
    ```
"""

from src.graph.state import RetornoNode, State


# Tabela de transições: (modo, categoria_msg) → intent
# Dados, não código. Adicionar comportamento = adicionar uma linha.
RESOLUCOES: dict[tuple[str, str], str] = {
    ('confirmando', 'afirmativo'): 'finalizar_pedido',
    ('confirmando', 'negativo'): 'modificar_pedido',  # volta a coletar
    ('confirmando', 'cancelar'): 'cancelar_pedido',
    ('coletando', 'afirmativo'): 'finalizar_pedido',  # "pode, isso mesmo"
    ('coletando', 'cancelar'): 'cancelar_pedido',
}

CATEGORIAS: dict[str, frozenset[str]] = {
    'afirmativo': frozenset(
        {
            'sim',
            'pode',
            'ok',
            'certo',
            'isso',
            'confirma',
            'vai',
            'bora',
            'fechar',
            'combinado',
            'isso mesmo',
            'exato',
            'perfeito',
            'show',
            'beleza',
        }
    ),
    'negativo': frozenset(
        {
            'nao',
            'não',
            'nem',
            'nope',
            'negativo',
        }
    ),
    'cancelar': frozenset(
        {
            'cancela',
            'esquece',
            'desisto',
            'anula',
            'zera',
            'recomeça',
            'começa de novo',
        }
    ),
}


def _categorizar(mensagem: str) -> str | None:
    """Categoriza mensagem curta. Retorna None se não reconhecida."""
    msg = mensagem.strip().lower()
    for categoria, tokens in CATEGORIAS.items():
        if msg in tokens:
            return categoria
    return None


def node_resolver_contexto(state: State) -> RetornoNode:
    """Tenta resolver intent pelo modo conversacional antes do classificador.

    Se resolver: preenche intent + origem_intent='contexto' e o grafo
    vai direto para o handler — sem chamar o classificador.

    Se não resolver: retorna intent='' e o grafo vai para o router.

    Args:
        state: Estado atual com 'modo' e 'mensagem_atual'.

    Returns:
        RetornoNode com intent resolvida ou vazio.
    """
    mensagem = state.get('mensagem_atual', '')
    modo = state.get('modo', 'ocioso')

    categoria = _categorizar(mensagem)
    if categoria:
        chave = (modo, categoria)
        intent_resolvida = RESOLUCOES.get(chave)
        if intent_resolvida:
            return {
                'intent': intent_resolvida,
                'confidence': 1.0,
                'origem_intent': 'contexto',
            }

    # Contexto não resolveu — sinaliza para ir ao classificador
    return {'intent': '', 'origem_intent': ''}
