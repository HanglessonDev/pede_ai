from langchain_ollama import OllamaLLM

from src.config import get_intencoes_validas, get_prompt


INTENCOES_VALIDAS = get_intencoes_validas()
PROMPT = get_prompt('classificador_intencoes')


modelo_llm = OllamaLLM(model='qwen3.5:2b', temperature=0, reasoning=False)


def classificar_intencao(mensagem: str) -> str:

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
