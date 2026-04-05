"""
DEPRECATED — Código legado, mantido apenas para compatibilidade.

Este módulo foi substituído por `src/roteador/service.py` (ClassificadorIntencoes)
durante a refatoração de 04/2026. O código OO usa injeção de dependência,
providers intercambiáveis (Groq, Ollama) e embeddings via sentence-transformers.

Arquivos substitutos:
- `src/roteador/service.py` — ClassificadorIntencoes (orchestrator)
- `src/roteador/modelos.py` — ResultadoClassificacao, ExemploSimilar
- `src/roteador/protocolos.py` — LLMProvider, EmbeddingProvider
- `src/roteador/classificadores/` — Lookup, RAG, LLM
- `src/roteador/voting.py` — votar_com_prioridade
- `src/roteador/embedding_service.py` — EmbeddingService
- `src/infra/` — GroqProvider, OllamaProvider, SentenceTransformerEmbeddings

TODO: Remover este arquivo após migrar todos os imports externos.
Rastrear: `git grep classificador_intencoes` para verificar uso.

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
    INTENT_PRIORITY,
    buscar_similares,
    calcular_votacao,  # noqa: F401 — usado por testes antigos
    calcular_votacao_com_prioridade,
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

# Intents de alta prioridade: quando presentes no top-k, prevalecem sobre
# intents de conversação (saudacao) mesmo com menor similaridade.
ALTA_PRIORIDADE_INTENTS = {
    'pedir',
    'remover',
    'trocar',
    'carrinho',
    'confirmar',
    'cancelar',
}

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
    mensagem_truncada: str,
    mensagem_norm: str,
) -> dict[str, Any]:
    """Decide a intenção baseada na confiança dos similares RAG.

    Usa votação com prioridade para lidar com mensagens compostas
    como "bom dia, quero um suco" (saudacao + pedir → pedir vence).

    Args:
        similares: Lista de exemplos similares com similaridade.
        mensagem_truncada: Mensagem normalizada e truncada.
        mensagem_norm: Mensagem normalizada original.

    Returns:
        Dicionário com 'intent', 'confidence', 'caminho',
        'top1_texto', 'top1_intencao', 'mensagem_norm'.
    """
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
        # Usa votação com prioridade para mensagens compostas
        intent = calcular_votacao_com_prioridade(similares)
        return {
            'intent': intent,
            'confidence': confidence,
            'caminho': 'rag_forte',
            'top1_texto': top1_texto,
            'top1_intencao': top1_intencao,
            'mensagem_norm': mensagem_norm,
        }

    # RAG médio: verifica se há alta prioridade no top-k
    intencao_rag = calcular_votacao_com_prioridade(similares)

    # Se a prioridade encontrou uma intent de alta prioridade,
    # usa direto sem validação LLM (evita que LLM volte para saudacao)
    if INTENT_PRIORITY.get(intencao_rag, 99) <= INTENT_PRIORITY.get('carrinho', 99):
        intent = intencao_rag
        caminho = 'rag_forte'
    else:
        # Sem alta prioridade: valida com LLM
        try:
            prompt_rag = montar_prompt_rag(mensagem_truncada, similares, intencao_rag)
            intent, _ = validar_com_llm(prompt_rag)
            caminho = 'llm_rag'
        except Exception:
            intent = intencao_rag
            caminho = 'llm_rag'

    return {
        'intent': intent,
        'confidence': confidence,
        'caminho': caminho,
        'top1_texto': top1_texto,
        'top1_intencao': top1_intencao,
        'mensagem_norm': mensagem_norm,
    }


def _classificar_intencao(mensagem: str, thread_id: str = '') -> dict[str, Any]:
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

    return _decidir_intent(similares, mensagem_truncada, mensagem_norm)


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
