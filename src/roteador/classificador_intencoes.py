"""
Classificador de intenções do Pede AI.

Classifica mensagens do usuário em intenções como:
saudacao, pedir, remover, trocar, carrinho, duvida, etc.

Example:
    ```python
    from src.roteador import classificar_intencao

    classificar_intencao('quero um xbacon')
    'pedir'
    ```
"""

import json
from pathlib import Path
from typing import Any

from langchain_ollama import OllamaLLM

from src.config import get_intencoes_validas, get_prompt
from src.roteador.rag_utils import (
    buscar_similares,
    calcular_votacao,
    lookup_intencao_direta,
    montar_prompt_rag,
)


INTENCOES_VALIDAS = get_intencoes_validas()
PROMPT_FIXO = get_prompt('classificador_intencoes')

modelo_llm = OllamaLLM(
    model='qwen3.5:2b',
    temperature=0,
    reasoning=False,
    num_ctx=512,
    num_predict=10,
)

CACHE_PATH = Path(__file__).parent / 'embedding_cache.json'


def _carregar_cache() -> dict[str, Any]:
    with open(CACHE_PATH, encoding='utf-8') as f:
        return json.load(f)


_cache = _carregar_cache()
EXEMPLOS = _cache['exemplos']
EMBEDDINGS = _cache['embeddings']

# Threshold para RAG-only: se similaridade >= 0.95, usa RAG direto sem LLM.
# Justificativa: matches >= 0.95 são quase idênticos, LLM pode atrapalhar.
# Ver testes em tests/src/roteador/test_classificador_rag.py
RAG_FORTE_THRESHOLD = 0.95

MAX_CHARS = 500


def classificar_intencao_com_confidence(mensagem: str) -> tuple[str, float]:
    """Classifica intenção usando RAG com confiança."""
    if not mensagem or not mensagem.strip():
        return classificar_intencao_fixo(mensagem), 1.0

    # Lookup direto para tokens únicos (mais confiável)
    intent_direta = lookup_intencao_direta(mensagem)
    if intent_direta:
        return intent_direta, 1.0

    mensagem = mensagem[:MAX_CHARS]

    if not EMBEDDINGS:
        return classificar_intencao_fixo(mensagem), 1.0

    try:
        similares = buscar_similares(mensagem, EXEMPLOS, EMBEDDINGS, top_k=5)
    except Exception:
        return classificar_intencao_fixo(mensagem), 1.0

    if not similares:
        return classificar_intencao_fixo(mensagem), 1.0

    intencao_dominante = calcular_votacao(similares)
    confidence = similares[0]['similaridade']

    if confidence < 0.5:
        intent_fixo = classificar_intencao_fixo(mensagem)
        return (intent_fixo if intent_fixo != 'desconhecido' else 'desconhecido'), (
            1.0 if intent_fixo != 'desconhecido' else confidence
        )

    # RAG forte (>= 0.95): usa direto, sem LLM
    # Justificativa: matches >= 0.95 são quase idênticos, LLM pode atrapalhar
    if confidence >= RAG_FORTE_THRESHOLD:
        return intencao_dominante, confidence

    # RAG médio (0.50 - 0.95): valida com LLM
    try:
        prompt_rag = montar_prompt_rag(mensagem, similares, intencao_dominante)
        intent, _ = chamar_llm_rag(prompt_rag)
    except Exception:
        intent = intencao_dominante

    return intent, confidence


def chamar_llm_rag(prompt: str) -> tuple[str, float]:
    """Chama o LLM com o prompt RAG e retorna intent + confidence.

    Args:
        prompt: Prompt RAG formatado.

    Returns:
        Tupla (intent, confidence).
    """
    resposta = modelo_llm.invoke(prompt)
    intencao = resposta.strip().lower().split()[0]

    if intencao not in INTENCOES_VALIDAS:
        return ('desconhecido', 0.0)

    return (intencao, 1.0)


def classificar_intencao_fixo(mensagem: str) -> str:
    """Classifica usando o prompt fixo (fallback).

    Args:
        mensagem: Mensagem do usuário.

    Returns:
        Nome da intenção.
    """
    resposta = modelo_llm.invoke(PROMPT_FIXO.format(mensagem=mensagem))
    intencao = resposta.strip().lower().split()[0]

    if intencao not in INTENCOES_VALIDAS:
        return 'desconhecido'

    return intencao


def classificar_intencao(mensagem: str) -> str:
    """Classifica a intenção (compatível com API existente).

    Args:
        mensagem: Texto da mensagem do usuário.

    Returns:
        Nome da intenção classificada ou 'desconhecido'.
    """
    intent, _ = classificar_intencao_com_confidence(mensagem)
    return intent


if __name__ == '__main__':
    testes = [
        'oi',
        'quero um xtudo',
        'tira a coca',
        'bom dia, cancela tudo',
        'vocês entregam?',
    ]
    for msg in testes:
        intent, confidence = classificar_intencao_com_confidence(msg)
        print(f'{msg!r} → {intent} (confidence: {confidence:.2f})')
