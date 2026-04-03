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
    normalizar_input,
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
    """Carrega o cache de embeddings do arquivo JSON.

    Returns:
        Dicionário com 'exemplos' e 'embeddings'.

    Example:
        ```python
        cache = _carregar_cache()
        'exemplos' in cache
        True
        ```
    """
    with open(CACHE_PATH, encoding='utf-8') as f:
        return json.load(f)


_cache = _carregar_cache()
EXEMPLOS = _cache['exemplos']
EMBEDDINGS = _cache['embeddings']

# Threshold para RAG-only: se similaridade >= 0.95, usa RAG direto sem LLM.
# Justificativa: matches >= 0.95 são quase idênticos, LLM pode atrapalhar.
# Ver testes em tests/src/roteador/test_classificador_rag.py
RAG_FORTE_THRESHOLD = 0.95

# Threshold mínimo de confiança para usar RAG.
# Se confidence < 0.5, usa fallback com LLM diretamente.
RAG_FRACO_THRESHOLD = 0.5

MAX_CHARS = 500


def _preparar_mensagem(mensagem: str) -> str | None:
    """Prepara e valida a mensagem para classificação.

    Args:
        mensagem: Texto original do usuário.

    Returns:
        Mensagem truncada se válida, None se vazia.

    Example:
        ```python
        _preparar_mensagem('oi')
        'oi'

        _preparar_mensagem('')
        None

        _preparar_mensagem('mensagem muito longa...')
        'mensagem muito longa...'  # truncada para MAX_CHARS
        ```
    """
    if not mensagem or not mensagem.strip():
        return None
    return mensagem[:MAX_CHARS]


def _fallback(mensagem: str) -> tuple[str, float]:
    """Retorna intent via LLM com confidence 1.0 (fallback).

    Args:
        mensagem: Texto do usuário.

    Returns:
        Tupla (intent, confidence=1.0).

    Example:
        ```python
        _fallback('mensagem qualquer')
        ('saudacao', 1.0)
        ```
    """
    return classificar_com_llm(mensagem), 1.0


def _decidir_intent(
    similares: list[dict[str, Any]],
    mensagem: str,
) -> tuple[str, float]:
    """Decide a intenção baseada na confiança dos similares.

    Args:
        similares: Lista de exemplos similares com similaridade.
        mensagem: Mensagem original para fallback.

    Returns:
        Tupla (intent, confidence).

    Example:
        ```python
        similares = [{'intencao': 'pedir', 'similaridade': 0.98}]
        _decidir_intent(similares, 'quero lanche')
        ('pedir', 0.98)

        similares = [{'intencao': 'duvida', 'similaridade': 0.40}]
        _decidir_intent(similares, 'msg')
        ('duvida', 1.0)  # fallback, confidence 1.0
        ```
    """
    intencao_rag = calcular_votacao(similares)
    confidence = similares[0]['similaridade']

    if confidence < RAG_FRACO_THRESHOLD:
        intent_fixo = classificar_com_llm(mensagem)
        return (
            intent_fixo if intent_fixo != 'desconhecido' else 'desconhecido',
            1.0 if intent_fixo != 'desconhecido' else confidence,
        )

    if confidence >= RAG_FORTE_THRESHOLD:
        return intencao_rag, confidence

    # RAG médio (0.5 - 0.95): valida com LLM
    try:
        prompt_rag = montar_prompt_rag(mensagem, similares, intencao_rag)
        intent, _ = validar_com_llm(prompt_rag)
    except Exception:
        intent = intencao_rag

    return intent, confidence


def _classificar_intencao(  # noqa: PLR0911
    mensagem: str, thread_id: str = ''
) -> dict[str, Any]:
    """Classifica intenção usando RAG com confiança (interno).

    Args:
        mensagem: Texto da mensagem do usuário.
        thread_id: Identificador da conversa (LangGraph config).

    Returns:
        Dicionário com 'intent', 'confidence', 'caminho',
        'top1_texto', 'top1_intencao', 'mensagem_norm'.

    Example:
        ```python
        resultado = _classificar_intencao('oi')
        resultado['intent']
        'saudacao'
        resultado['caminho']
        'lookup'
        ```
    """
    mensagem_norm = normalizar_input(mensagem) if mensagem else ''
    mensagem_truncada = _preparar_mensagem(mensagem_norm)

    if mensagem_truncada is None:
        intent, confidence = _fallback(mensagem)
        return {
            'intent': intent,
            'confidence': confidence,
            'caminho': 'llm_fixo',
            'top1_texto': '',
            'top1_intencao': '',
            'mensagem_norm': mensagem_norm,
        }

    # Lookup direto
    intent_direta = lookup_intencao_direta(mensagem_truncada)
    if intent_direta:
        return {
            'intent': intent_direta,
            'confidence': 1.0,
            'caminho': 'lookup',
            'top1_texto': mensagem_truncada,
            'top1_intencao': intent_direta,
            'mensagem_norm': mensagem_norm,
        }

    if not EMBEDDINGS:
        intent, confidence = _fallback(mensagem_truncada)
        return {
            'intent': intent,
            'confidence': confidence,
            'caminho': 'llm_fixo',
            'top1_texto': '',
            'top1_intencao': '',
            'mensagem_norm': mensagem_norm,
        }

    try:
        similares = buscar_similares(mensagem_truncada, EXEMPLOS, EMBEDDINGS, top_k=5)
    except Exception:
        intent, confidence = _fallback(mensagem_truncada)
        return {
            'intent': intent,
            'confidence': confidence,
            'caminho': 'llm_fixo',
            'top1_texto': '',
            'top1_intencao': '',
            'mensagem_norm': mensagem_norm,
        }

    if not similares:
        intent, confidence = _fallback(mensagem_truncada)
        return {
            'intent': intent,
            'confidence': confidence,
            'caminho': 'llm_fixo',
            'top1_texto': '',
            'top1_intencao': '',
            'mensagem_norm': mensagem_norm,
        }

    # RAG
    confidence = similares[0]['similaridade']
    top1_texto = similares[0]['texto']
    top1_intencao = similares[0]['intencao']

    if confidence < RAG_FRACO_THRESHOLD:
        intent, _ = _fallback(mensagem_truncada)
        return {
            'intent': intent,
            'confidence': confidence,
            'caminho': 'llm_rag',
            'top1_texto': top1_texto,
            'top1_intencao': top1_intencao,
            'mensagem_norm': mensagem_norm,
        }

    if confidence >= RAG_FORTE_THRESHOLD:
        intent = calcular_votacao(similares)
        return {
            'intent': intent,
            'confidence': confidence,
            'caminho': 'rag_forte',
            'top1_texto': top1_texto,
            'top1_intencao': top1_intencao,
            'mensagem_norm': mensagem_norm,
        }

    # RAG médio: valida com LLM
    intencao_rag = calcular_votacao(similares)
    try:
        prompt_rag = montar_prompt_rag(mensagem_truncada, similares, intencao_rag)
        intent, _ = validar_com_llm(prompt_rag)
    except Exception:
        intent = intencao_rag

    return {
        'intent': intent,
        'confidence': confidence,
        'caminho': 'llm_rag',
        'top1_texto': top1_texto,
        'top1_intencao': top1_intencao,
        'mensagem_norm': mensagem_norm,
    }


def validar_com_llm(prompt: str) -> tuple[str, float]:
    """Valida intent com LLM usando prompt RAG.

    Args:
        prompt: Prompt RAG formatado com exemplos similares.

    Returns:
        Tupla (intent, confidence).

    Example:
        ```python
        prompt = 'Classifique: "quero lanche" → pedir'
        validar_com_llm(prompt)
        ('pedir', 1.0)
        ```
    """
    resposta = modelo_llm.invoke(prompt)
    intencao = resposta.strip().lower().split()[0]

    if intencao not in INTENCOES_VALIDAS:
        return ('desconhecido', 0.0)

    return (intencao, 1.0)


def classificar_com_llm(mensagem: str) -> str:
    """Classifica intenção usando apenas o LLM (fallback).

    Args:
        mensagem: Mensagem do usuário.

    Returns:
        Nome da intenção.

    Example:
        ```python
        classificar_com_llm('oi')
        'saudacao'

        classificar_com_llm('xyz123')
        'desconhecido'
        ```
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

    Example:
        ```python
        classificar_intencao('oi')
        'saudacao'

        classificar_intencao('quero um xbacon')
        'pedir'
        ```
    """
    resultado = _classificar_intencao(mensagem)
    return resultado['intent']


if __name__ == '__main__':
    testes = [
        'oi',
        'quero um xtudo',
        'tira a coca',
        'bom dia, cancela tudo',
        'vocês entregam?',
    ]
    for msg in testes:
        resultado = _classificar_intencao(msg)
        print(
            f'{msg!r} → {resultado["intent"]} '
            f'(confidence: {resultado["confidence"]:.2f}, '
            f'caminho: {resultado["caminho"]})'
        )
