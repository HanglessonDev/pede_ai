"""Consultas DuckDB para análise de eventos de classificação.

Este módulo fornece funções para analisar os dados registrados pelo
`ObservabilidadeLogger` usando DuckDB. Permite consultar o arquivo CSV
gerado pelo logger com SQL para extrair insights sobre o comportamento
do classificador.

Example:
    ```python
    from src.observabilidade.consultas import baixa_confianca, distribuicao_caminhos

    # Casos de baixa confiança que foram para o LLM
    casos = baixa_confianca("logs/classificacoes.csv", limit=10)
    for caso in casos:
        print(f"{caso['mensagem']}: {caso['confidence']:.2f}")

    # Distribuição de caminhos
    dist = distribuicao_caminhos("logs/classificacoes.csv")
    for item in dist:
        print(f"{item['caminho']}: {item['total']} eventos")
    ```

Note:
    As funções retornam listas de dicionários, facilitando a conversão
    para DataFrames pandas ou visualizações.
"""

from __future__ import annotations

import duckdb


def baixa_confianca(csv_path: str, limit: int = 20) -> list[dict]:
    """Retorna casos de baixa confiança que foram roteados para o LLM.

    Esta consulta identifica eventos onde o RAG não atingiu confiança
    suficiente e o sistema fez fallback para LLM (`llm_rag` ou `llm_fixo`).
    Útil para analisar onde o classificador RAG está tendo dificuldades.

    Args:
        csv_path: Caminho do arquivo CSV de eventos.
        limit: Número máximo de resultados retornados.

    Returns:
        Lista de dicionários com `mensagem`, `intent`, `confidence` e
        `caminho`, ordenados por confiança crescente.

    Example:
        ```python
        casos = baixa_confianca("logs/classificacoes.csv")
        # [{'mensagem': 'tem opcao vegana?', 'intent': 'info_cardapio',
        #   'confidence': 0.35, 'caminho': 'llm_rag'}, ...]

        # Limitar resultados
        top5 = baixa_confianca("logs/classificacoes.csv", limit=5)
        ```

    Tip:
        Use os resultados para identificar padrões de mensagens que
        precisam de mais exemplos no banco de dados RAG.
    """
    conn = duckdb.connect()
    query = f"""
        SELECT mensagem, intent, confidence, caminho
        FROM '{csv_path}'
        WHERE caminho IN ('llm_rag', 'llm_fixo')
        ORDER BY confidence ASC
        LIMIT {limit}
    """
    rows = conn.execute(query).fetchall()
    cols = [desc[0] for desc in conn.execute(query).description]
    conn.close()
    return [dict(zip(cols, row, strict=True)) for row in rows]


def distribuicao_caminhos(csv_path: str) -> list[dict]:
    """Retorna a distribuição de eventos por caminho de classificação.

    Esta consulta agrupa os eventos pelo campo `caminho` e conta o total
    de cada um. Útil para entender como as mensagens estão sendo
    classificadas e qual percentual usa cada fluxo.

    Args:
        csv_path: Caminho do arquivo CSV de eventos.

    Returns:
        Lista de dicionários com `caminho` e `total`, ordenados pelo
        total em ordem decrescente.

    Example:
        ```python
        dist = distribuicao_caminhos("logs/classificacoes.csv")
        # [{'caminho': 'rag_forte', 'total': 150},
        #  {'caminho': 'lookup', 'total': 45},
        #  {'caminho': 'llm_rag', 'total': 12}]

        # Calcular percentual
        total_geral = sum(item['total'] for item in dist)
        for item in dist:
            pct = item['total'] / total_geral * 100
            print(f"{item['caminho']}: {pct:.1f}%")
        ```

    Tip:
        Uma alta taxa de `llm_rag` ou `llm_fixo` pode indicar que o
        banco de exemplos RAG precisa ser expandido.
    """
    conn = duckdb.connect()
    query = f"""
        SELECT caminho, COUNT(*) as total
        FROM '{csv_path}'
        GROUP BY caminho
        ORDER BY total DESC
    """
    rows = conn.execute(query).fetchall()
    cols = [desc[0] for desc in conn.execute(query).description]
    conn.close()
    return [dict(zip(cols, row, strict=True)) for row in rows]

