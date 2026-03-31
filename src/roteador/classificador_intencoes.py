"""
Classificador de intenções do Pede AI.

Classifica mensagens do usuário em intenções como:
saudacao, pedir, remover, trocar, carrinho, duvida, etc.

Example:
    >>> from src.roteador import classificar_intencao
    >>> classificar_intencao('quero um xbacon')
    'pedir'
"""
from langchain_ollama import OllamaLLM

from src.config import get_intencoes_validas, get_prompt


INTENCOES_VALIDAS = get_intencoes_validas()
PROMPT = get_prompt('classificador_intencoes')


modelo_llm = OllamaLLM(model='qwen3.5:2b', temperature=0, reasoning=False)


def classificar_intencao(mensagem: str) -> str:
    """
    Classifica a intenção de uma mensagem do usuário.

    Analisa a mensagem usando um modelo de linguagem (LLM) e
    retorna a intenção identificada.

    Args:
        mensagem: Texto da mensagem do usuário.

    Returns:
        Nome da intenção classificada ou 'desconhecido' se não for válida.

    Raises:
        Exception: Se o modelo LLM falhar ao processar a mensagem.

    Example:
        >>> from src.roteador import classificar_intencao
        
        >>> classificar_intencao('oi')
        'saudacao'
        >>> classificar_intencao('quero um xtudo')
        'pedir'
        >>> classificar_intencao('tira a coca')
        'remover'
    """
    resposta = modelo_llm.invoke(PROMPT.format(mensagem=mensagem))
    intencao = resposta.strip().lower().split()[0]

    if intencao not in INTENCOES_VALIDAS:
        return 'desconhecido'

    return intencao


if __name__ == '__main__':
    testes = [
        'oi',
        'quero um xtudo',
        'tira a coca',
        'bom dia, cancela tudo',
        'vocês entregam?',
    ]
    for msg in testes:
        print(f'{msg!r} → {classificar_intencao(msg)}')
