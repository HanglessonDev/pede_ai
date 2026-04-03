"""Consultas DuckDB para analise de eventos de classificacao."""

from __future__ import annotations

import duckdb


def baixa_confianca(csv_path: str, limit: int = 20) -> list[dict]:
    """Retorna casos de baixa confianca que foram para o LLM.

    Args:
        csv_path: Caminho do arquivo CSV.
        limit: Numero maximo de resultados.

    Returns:
        Lista de dicionarios com mensagem, intent, confidence e caminho.
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
    """Retorna distribuicao de eventos por caminho.

    Args:
        csv_path: Caminho do arquivo CSV.

    Returns:
        Lista de dicionarios com caminho e total.
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

