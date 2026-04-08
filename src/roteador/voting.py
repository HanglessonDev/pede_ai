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
from typing import TYPE_CHECKING

from src.roteador.modelos import ExemploSimilar

if TYPE_CHECKING:
    from src.observabilidade.loggers import ObservabilidadeLoggers


# Threshold para confianca absoluta no top-1
_TOP1_CONFIANCA = 0.98


def votar_com_prioridade(
    exemplos: list[ExemploSimilar],
    alta_prioridade: frozenset[str],
    min_similarity: float = 0.55,
    loggers: ObservabilidadeLoggers | None = None,
    thread_id: str = '',
    turn_id: str = '',
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
        loggers: Loggers de observabilidade para decision tracing.
        thread_id: ID da sessao para correlacao de logs.
        turn_id: ID do turno para correlacao de logs.

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
        if loggers and loggers.decisor:
            loggers.decisor.registrar(
                thread_id=thread_id,
                turn_id=turn_id,
                componente='classificacao_voting',
                decisao='top1_confianca',
                alternativas=[f'{e.intencao}({e.similaridade})' for e in exemplos[:5]],
                criterio=f'top1_similaridade={exemplos[0].similaridade}',
                threshold=f'>={_TOP1_CONFIANCA}',
                resultado=exemplos[0].intencao,
                contexto={'num_exemplos': len(exemplos)},
            )
        return exemplos[0].intencao

    # Regra 2: alta prioridade no top-K
    melhor_prioritaria: str | None = None
    melhor_sim_prioritaria = 0.0

    for ex in exemplos:
        if ex.intencao in alta_prioridade and ex.similaridade > melhor_sim_prioritaria:
            melhor_prioritaria = ex.intencao
            melhor_sim_prioritaria = ex.similaridade

    if melhor_prioritaria and melhor_sim_prioritaria >= min_similarity:
        if loggers and loggers.decisor:
            loggers.decisor.registrar(
                thread_id=thread_id,
                turn_id=turn_id,
                componente='classificacao_voting',
                decisao='alta_prioridade',
                alternativas=[f'{e.intencao}({e.similaridade})' for e in exemplos[:5]],
                criterio=f"prioritaria='{melhor_prioritaria}' sim={melhor_sim_prioritaria}",
                threshold=f'>={min_similarity}',
                resultado=melhor_prioritaria,
                contexto={'num_exemplos': len(exemplos)},
            )
        return melhor_prioritaria

    # Regra 3: maioria simples
    votos = Counter(ex.intencao for ex in exemplos)
    resultado = votos.most_common(1)[0][0]

    if loggers and loggers.decisor:
        loggers.decisor.registrar(
            thread_id=thread_id,
            turn_id=turn_id,
            componente='classificacao_voting',
            decisao='voto_majoritario',
            alternativas=[f'{e.intencao}({e.similaridade})' for e in exemplos[:5]],
            criterio=f'maioria_simples votos={dict(votos)}',
            threshold='nenhum (fallback)',
            resultado=resultado,
            contexto={'num_exemplos': len(exemplos)},
        )

    return resultado
