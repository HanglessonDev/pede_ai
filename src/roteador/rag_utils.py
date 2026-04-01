"""RAG utilities para classificação de intenções."""
from collections import Counter
from typing import Any

import numpy as np
import ollama

EMBEDDING_MODEL = 'mini-embed'


def gerar_embedding(texto: str) -> list[float]:
    """Gera embedding para um texto usando Ollama.

    Args:
        texto: Texto para gerar embedding.

    Returns:
        Lista de floats representando o embedding.
    """
    response = ollama.embeddings(model=EMBEDDING_MODEL, prompt=texto)
    return response['embedding']


def cosine_similarity(a: list[float] | np.ndarray, b: list[float] | np.ndarray) -> float:
    """Calcula similaridade cosseno entre dois vetores.

    Args:
        a: Primeiro vetor.
        b: Segundo vetor.

    Returns:
        Similaridade cosseno entre -1 e 1.
    """
    a = np.array(a)
    b = np.array(b)
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def buscar_similares(
    mensagem: str,
    exemplos: list[dict[str, Any]],
    embeddings: list[list[float]],
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Busca os top-k exemplos mais similares à mensagem.

    Args:
        mensagem: Mensagem do usuário.
        exemplos: Lista de exemplos com 'texto' e 'intencao'.
        embeddings: Lista de embeddings pré-computados.
        top_k: Número de resultados a retornar.

    Returns:
        Lista de exemplos mais similares com 'similaridade'.
    """
    query_emb = gerar_embedding(mensagem)
    query_vec = np.array(query_emb)

    similarities = []
    for emb in embeddings:
        emb_vec = np.array(emb)
        sim = cosine_similarity(query_vec, emb_vec)
        similarities.append(sim)

    top_indices = np.argsort(similarities)[::-1][:top_k]

    results = [
        {**exemplos[idx], 'similaridade': float(similarities[idx])}
        for idx in top_indices
    ]

    return results


def calcular_votacao(similares: list[dict[str, Any]]) -> str:
    """Calcula a intenção mais comum entre os exemplos similares.

    Args:
        similares: Lista de exemplos similares com 'intencao'.

    Returns:
        Nome da intenção mais comum.
    """
    votos = Counter(s['intencao'] for s in similares)
    return votos.most_common(1)[0][0]


def montar_prompt_rag(
    mensagem: str,
    similares: list[dict[str, Any]],
    intencao_dominante: str,
) -> str:
    """Monta prompt dinâmico com exemplos similares e votação.

    Args:
        mensagem: Mensagem do usuário.
        similares: Lista de exemplos similares.
        intencao_dominante: Intenção mais comum nos exemplos.

    Returns:
        Prompt formatado para o LLM.
    """
    exemplos_formatados = '\n'.join(
        f'"{s["texto"]}" → {s["intencao"]}'
        for s in similares[:5]
    )

    prompt = f"""Classifique a intenção do usuário em UMA palavra.
Responda APENAS o NOME DA INTENÇÃO exatamente como listado abaixo.

INTENÇÕES VÁLIDAS: saudacao, pedir, remover, trocar, carrinho, duvida, confirmar, negar, cancelar

Use os exemplos abaixo como referência. A maioria dos exemplos similares
aponta para a intenção "{intencao_dominante}".

EXEMPLOS:
{exemplos_formatados}

SUA VEZ:
"{mensagem}" →
"""
    return prompt
