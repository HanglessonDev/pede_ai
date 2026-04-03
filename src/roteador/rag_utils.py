"""RAG utilities para classificação de intenções."""

from collections import Counter, defaultdict
from typing import Any

import numpy as np
import ollama


EMBEDDING_MODEL = 'mini-embed'

# Threshold mínimo de similaridade para incluir exemplos no RAG.
# Valor baseado na análise empírica: exemplos >= 0.55 têm relevância aceitável,
# enquanto < 0.55 tendem a ser ruído (palavras similares mas intenção diferente).
MIN_SIMILARITY_THRESHOLD = 0.55


def gerar_embedding(texto: str) -> list[float]:
    """Gera embedding para um texto usando Ollama.

    Args:
        texto: Texto para gerar embedding.

    Returns:
        Lista de floats representando o embedding.
    """
    # API nova: ollama.embed() com input= (não embeddings com prompt=)
    response = ollama.embed(model=EMBEDDING_MODEL, input=texto)
    return response['embeddings'][0]


def cosine_similarity(
    a: list[float] | np.ndarray, b: list[float] | np.ndarray
) -> float:
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
    min_similarity: float = MIN_SIMILARITY_THRESHOLD,
) -> list[dict[str, Any]]:
    """Busca os top-k exemplos mais similares à mensagem.

    Args:
        mensagem: Mensagem do usuário.
        exemplos: Lista de exemplos com 'texto' e 'intencao'.
        embeddings: Lista de embeddings pré-computados.
        top_k: Número de resultados a retornar.
        min_similarity: Similaridade mínima para incluir exemplo (padrão: 0.55).

    Returns:
        Lista de exemplos mais similares com 'similaridade'.
        Apenas exemplos com similaridade >= min_similarity são retornados.
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

    # Filtra exemplos abaixo do threshold mínimo
    results = [r for r in results if r['similaridade'] >= min_similarity]

    return results


def calcular_votacao_max(similares: list[dict[str, Any]]) -> str:
    """Voto majoritário simples: conta exemplos, ignora similaridade.
    
    Args:
        similares: Lista de exemplos similares com 'intencao'.
    
    Returns:
        Nome da intenção com mais exemplos no top-k.
    """
    if not similares:
        return 'desconhecido'
    
    votos = Counter(s['intencao'] for s in similares)
    return votos.most_common(1)[0][0]


def calcular_votacao_hybrid(
    similares: list[dict[str, Any]], threshold: float = 0.95
) -> str:
    """Hybrid Voting: confia no top-1 se similaridade >= threshold, senão maioria.
    
    Lógica:
    - Se top-1 tem similaridade >= 0.95: retorna intenção do top-1 (match exato)
    - Senão: usa voto majoritário (evita viés de redundância)
    
    Args:
        similares: Lista de exemplos similares com 'intencao' e 'similaridade'.
        threshold: Similaridade mínima para confiar no top-1 (padrão: 0.95).
    
    Returns:
        Nome da intenção classificada.
    """
    if not similares:
        return 'desconhecido'
    
    top_sim = similares[0]['similaridade']
    
    # Match muito forte: confia no top-1
    if top_sim >= threshold:
        return similares[0]['intencao']
    
    # Ambiguidade: usa voto majoritário
    return calcular_votacao_max(similares)


def calcular_votacao(similares: list[dict[str, Any]]) -> str:
    """Calcula a intenção usando Hybrid Voting (novo padrão).
    
    Usa Hybrid Voting: confia no top-1 se similaridade >= 0.95,
    senão usa voto majoritário simples.
    
    Args:
        similares: Lista de exemplos similares com 'intencao' e 'similaridade'.
    
    Returns:
        Nome da intenção classificada.
    """
    return calcular_votacao_hybrid(similares)


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
        f'"{s["texto"]}" → {s["intencao"]}' for s in similares[:5]
    )

    prompt = f"""Classifique a intenção do usuário em UMA palavra.
Responda APENAS o NOME DA INTENÇÃO exatamente como listado abaixo.

INTENÇÕES VÁLIDAS: saudacao, pedir, remover, trocar, carrinho, duvida, confirmar, negar, cancelar

Analise os exemplos abaixo e classifique a nova mensagem.
Cada exemplo mostra a intenção correta para aquela frase.

EXEMPLOS:
{exemplos_formatados}

Agora classifique esta mensagem:
"{mensagem}" →
"""
    return prompt
