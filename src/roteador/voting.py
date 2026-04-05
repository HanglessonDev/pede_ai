"""Estrategia de votacao consolidada para classificacao RAG.

Consolida as 4 funcoes antigas (votacao_max, hybrid, com_prioridade, wrapper)
em uma unica funcao com logica clara.

Example:
    ```python
    from src.roteador.voting import votar_com_prioridade
    from src.roteador.modelos import ExemploSimilar

    exemplos = [
        ExemploSimilar('oi', 'saudacao', 0.90),
        ExemploSimilar('quero lanche', 'pedir', 0.75),
    ]
    votar_com_prioridade(exemplos, {'pedir', 'carrinho'})
    'saudacao'
    ```
"""

from __future__ import annotations

from collections import Counter

from src.roteador.modelos import ExemploSimilar


# Threshold para confianca absoluta no top-1
_TOP1_CONFIANCA = 0.98


def votar_com_prioridade(
    exemplos: list[ExemploSimilar],
    alta_prioridade: frozenset[str],
    min_similarity: float = 0.55,
) -> str:
    """Votacao com prioridade de intents no top-K.

    Regras (em ordem):
    1. Se top-1 >= 0.98: confia direto no top-1 (match quase identico).
    2. Se ha intent de alta prioridade no top-K com similaridade >= min_similarity:
       retorna a de maior similaridade entre as prioritarias.
    3. Fallback: maioria simples (voto majoritario).

    Args:
        exemplos: Lista de exemplos similares ordenados por similaridade decrescente.
        alta_prioridade: Conjunto de intents de alta prioridade.
        min_similarity: Similaridade minima para considerar intent prioritaria.

    Returns:
        Nome da intencao vencedora ou 'desconhecido' se lista vazia.

    Example:
        ```python
        exemplos = [
            ExemploSimilar('bom dia', 'saudacao', 0.92),
            ExemploSimilar('quero xbacon', 'pedir', 0.78),
        ]
        votar_com_prioridade(exemplos, {'pedir', 'carrinho'})
        'pedir'
        ```
    """
    if not exemplos:
        return 'desconhecido'

    # Regra 1: confianca absoluta no top-1
    if exemplos[0].similaridade >= _TOP1_CONFIANCA:
        return exemplos[0].intencao

    # Regra 2: alta prioridade no top-K
    melhor_prioritaria: str | None = None
    melhor_sim_prioritaria = 0.0

    for ex in exemplos:
        if ex.intencao in alta_prioridade and ex.similaridade > melhor_sim_prioritaria:
            melhor_prioritaria = ex.intencao
            melhor_sim_prioritaria = ex.similaridade

    if melhor_prioritaria and melhor_sim_prioritaria >= min_similarity:
        return melhor_prioritaria

    # Regra 3: maioria simples
    votos = Counter(ex.intencao for ex in exemplos)
    return votos.most_common(1)[0][0]
