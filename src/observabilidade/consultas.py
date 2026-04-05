"""Consultas DuckDB para analise de eventos de classificacao.

Paths de arquivo sao interpolados com f-string (controlados internamente).
Valores de usuario (thread_id, limit) usam parametros seguros ``?``.

Example:
    ```python
    from src.observabilidade.consultas import baixa_confianca, distribuicao_caminhos

    casos = baixa_confianca('logs/classificacoes.csv', limit=10)
    dist = distribuicao_caminhos('logs/classificacoes.csv')
    ```
"""

from __future__ import annotations

from pathlib import Path

import duckdb


def _executar_query(query: str, params: list | None = None) -> list[dict]:
    """Executa query DuckDB com parametros seguros.

    Args:
        query: SQL com placeholders ``?``.
        params: Lista de parametros para os placeholders.

    Returns:
        Lista de dicionarios com resultados.
    """
    conn = duckdb.connect()
    result = conn.execute(query, params or [])
    cols = [desc[0] for desc in result.description]
    rows = result.fetchall()
    conn.close()
    return [dict(zip(cols, row, strict=True)) for row in rows]


def _sanitizar_path(csv_path: str) -> str:
    """Resolve e valida path de CSV.

    Args:
        csv_path: Caminho do arquivo CSV.

    Returns:
        Path absoluto como string.

    Raises:
        FileNotFoundError: Se o arquivo nao existe.
    """
    path = Path(csv_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f'Arquivo nao encontrado: {path}')
    return str(path)


def baixa_confianca(csv_path: str, limit: int = 20) -> list[dict]:
    """Retorna casos de baixa confianca que foram roteados para o LLM."""
    path = _sanitizar_path(csv_path)
    query = f"""
        SELECT mensagem, intent, confidence, caminho
        FROM '{path}'
        WHERE caminho IN ('llm_rag', 'llm_fixo')
        ORDER BY confidence ASC
        LIMIT ?
    """
    return _executar_query(query, [limit])


def distribuicao_caminhos(csv_path: str) -> list[dict]:
    """Retorna a distribuicao de eventos por caminho de classificacao."""
    path = _sanitizar_path(csv_path)
    query = f"""
        SELECT caminho, COUNT(*) as total
        FROM '{path}'
        GROUP BY caminho
        ORDER BY total DESC
    """
    return _executar_query(query)


def extracoes_sem_itens(csv_extracao: str, limit: int = 20) -> list[dict]:
    """Retorna mensagens onde extrator nao encontrou itens."""
    path = _sanitizar_path(csv_extracao)
    query = f"""
        SELECT mensagem, itens_encontrados, tempo_ms
        FROM '{path}'
        WHERE itens_encontrados = 0
        ORDER BY timestamp DESC
        LIMIT ?
    """
    return _executar_query(query, [limit])


def funil_com_abandono(csv_funil: str, thread_id: str | None = None) -> list[dict]:
    """Analisa sessoes que pararam em etapas intermediarias."""
    path = _sanitizar_path(csv_funil)
    if thread_id:
        query = f"""
            SELECT thread_id, etapa_atual, intent, carrinho_size, timestamp
            FROM '{path}'
            WHERE thread_id = ?
            ORDER BY timestamp DESC
            LIMIT 50
        """
        return _executar_query(query, [thread_id])
    query = f"""
        SELECT thread_id, etapa_atual, intent, carrinho_size, timestamp
        FROM '{path}'
        ORDER BY timestamp DESC
        LIMIT 50
    """
    return _executar_query(query)


def handlers_com_erro(csv_handler: str, limit: int = 20) -> list[dict]:
    """Retorna execucoes de handlers com erro."""
    path = _sanitizar_path(csv_handler)
    query = f"""
        SELECT handler, intent, input_resumo, erro, tempo_ms
        FROM '{path}'
        WHERE erro != ''
        ORDER BY timestamp DESC
        LIMIT ?
    """
    return _executar_query(query, [limit])


def tempo_medio_handlers(csv_handler: str) -> list[dict]:
    """Retorna tempo medio por handler."""
    path = _sanitizar_path(csv_handler)
    query = f"""
        SELECT handler, AVG(tempo_ms) as tempo_medio_ms, COUNT(*) as total_execucoes
        FROM '{path}'
        GROUP BY handler
        ORDER BY tempo_medio_ms DESC
    """
    return _executar_query(query)
