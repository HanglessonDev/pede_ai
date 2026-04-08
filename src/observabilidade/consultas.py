"""Consultas DuckDB para analise de decisoes, fluxo e metricas de negocio.

Funcoes para extrair insights dos logs de observabilidade:
- Reconstruir sessao completa (decisoes + fluxo + negocio)
- Identificar bugs de logica (decisoes suspeitas)
- Metricas de negocio (ticket medio, taxa de cancelamento)
- Performance (latencia p95, tempo por componente)

Example:
    ```python
    from src.observabilidade.consultas import (
        reconstruir_sessao,
        bugs_logica,
        ticket_medio,
    )

    # Reconstruir sessao
    eventos = reconstruir_sessao('sessao_001')

    # Ver bugs de logica
    bugs = bugs_logica(limite=20)

    # Metricas de negocio
    ticket = ticket_medio()
    ```
"""

from __future__ import annotations

from pathlib import Path

import duckdb


def _conectar() -> duckdb.DuckDBPyConnection:
    """Cria conexao DuckDB temporaria."""
    return duckdb.connect()


def _executar_query(query: str, params: list | None = None) -> list[dict]:
    """Executa query DuckDB com parametros seguros.

    Args:
        query: SQL com placeholders ``?``.
        params: Lista de parametros para os placeholders.

    Returns:
        Lista de dicionarios com resultados.
    """
    conn = _conectar()
    try:
        result = conn.execute(query, params or [])
        cols = [desc[0] for desc in result.description]
        rows = result.fetchall()
        return [dict(zip(cols, row, strict=True)) for row in rows]
    finally:
        conn.close()


def _sanitizar_path(csv_path: str | Path) -> str:
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


# ══════════════════════════════════════════════════════════════════════════════
# Reconstrucao de Sessao
# ══════════════════════════════════════════════════════════════════════════════


def reconstruir_sessao(
    thread_id: str,
    turn_id: str | None = None,
    log_dir: str | Path = 'logs',
) -> list[dict]:
    """Reconstrói timeline completa de uma sessao.

    Junta decisoes, fluxo e negocio por thread_id + turn_id.
    Ordena por timestamp.

    Args:
        thread_id: ID da sessao.
        turn_id: ID do turno (opcional, filtra se fornecido).
        log_dir: Diretorio dos arquivos de log.

    Returns:
        Lista de eventos ordenados por timestamp com tipo do evento.
    """
    log_path = Path(log_dir)

    # Construir query UNION ALL entre os 3 CSVs
    queries = []

    decisoes_csv = log_path / 'decisoes.csv'
    if decisoes_csv.exists():
        d_path = _sanitizar_path(decisoes_csv)
        q = f"""
            SELECT
                timestamp,
                thread_id,
                turn_id,
                'decisao' as tipo,
                componente,
                decisao as acao,
                criterio,
                resultado,
                contexto,
                0 as tempo_ms
            FROM '{d_path}'
            WHERE thread_id = ?
        """
        if turn_id:
            q += f" AND turn_id = '{turn_id}'"
        queries.append((q, [thread_id]))

    fluxo_csv = log_path / 'fluxo.csv'
    if fluxo_csv.exists():
        f_path = _sanitizar_path(fluxo_csv)
        q = f"""
            SELECT
                timestamp,
                thread_id,
                turn_id,
                'fluxo' as tipo,
                componente,
                acao,
                observacao as criterio,
                observacao as resultado,
                estado_depois as contexto,
                tempo_ms
            FROM '{f_path}'
            WHERE thread_id = ?
        """
        if turn_id:
            q += f" AND turn_id = '{turn_id}'"
        queries.append((q, [thread_id]))

    negocio_csv = log_path / 'negocio.csv'
    if negocio_csv.exists():
        n_path = _sanitizar_path(negocio_csv)
        q = f"""
            SELECT
                timestamp,
                thread_id,
                turn_id,
                'negocio' as tipo,
                evento as componente,
                evento as acao,
                resposta as criterio,
                evento as resultado,
                '' as contexto,
                0 as tempo_ms
            FROM '{n_path}'
            WHERE thread_id = ?
        """
        if turn_id:
            q += f" AND turn_id = '{turn_id}'"
        queries.append((q, [thread_id]))

    if not queries:
        return []

    # Union all e ordenacao
    union_parts = []
    all_params: list = []
    for q, params in queries:
        union_parts.append(q)
        all_params.extend(params)

    full_query = f"""
        SELECT * FROM (
            {' UNION ALL '.join(union_parts)}
        )
        ORDER BY timestamp ASC
    """

    return _executar_query(full_query, all_params)


# ══════════════════════════════════════════════════════════════════════════════
# Detecao de Bugs de Logica
# ══════════════════════════════════════════════════════════════════════════════


def bugs_logica(
    log_dir: str | Path = 'logs',
    limite: int = 50,
) -> list[dict]:
    """Identifica potenciais bugs de logica nas decisoes.

    Padroes detectados:
    - Dispatcher sem_entidade após caso B (bug J)
    - Extracao vazia por negacao com mensagem longa (bug O)
    - LLM fallback com intent desconhecido (bug C)

    Args:
        log_dir: Diretorio dos arquivos de log.
        limite: Maximo de resultados.

    Returns:
        Lista de decisoes suspeitas com descricao do bug.
    """
    log_path = Path(log_dir)
    decisoes_csv = log_path / 'decisoes.csv'

    if not decisoes_csv.exists():
        return []

    d_path = _sanitizar_path(decisoes_csv)

    # Bug J: dispatcher caso B → sem_entidade
    bug_j = f"""
        SELECT
            timestamp, thread_id, turn_id, componente, decisao,
            criterio, resultado, contexto,
            'BUG_J: Caso B sem variante -> sem_entidade' as bug_tipo
        FROM '{d_path}'
        WHERE componente = 'dispatcher_passo1_troca'
          AND decisao LIKE '%caso_B%'
          AND resultado = 'sem_entidade'
    """

    # Bug O: extracao_negacao → lista_vazia com mensagem longa
    bug_o = f"""
        SELECT
            timestamp, thread_id, turn_id, componente, decisao,
            criterio, resultado, contexto,
            'BUG_O: Negacao silencia extracao' as bug_tipo
        FROM '{d_path}'
        WHERE componente = 'extracao_negacao'
          AND resultado = 'vazio'
          AND LENGTH(contexto) > 100
    """

    # Bug C: LLM fallback com intent desconhecido
    bug_c = f"""
        SELECT
            timestamp, thread_id, turn_id, componente, decisao,
            criterio, resultado, contexto,
            'BUG_C: LLM fallback com intent desconhecido' as bug_tipo
        FROM '{d_path}'
        WHERE componente = 'classificacao_llm_fallback'
          AND resultado = 'desconhecido'
    """

    query = f"""
        SELECT * FROM (
            {bug_j} UNION ALL {bug_o} UNION ALL {bug_c}
        )
        ORDER BY timestamp DESC
        LIMIT ?
    """

    return _executar_query(query, [limite])


def decisoes_erradas(
    componente: str | None = None,
    log_dir: str | Path = 'logs',
    limite: int = 20,
) -> list[dict]:
    """Retorna decisoes suspeitas para analise.

    Filtra por componente ou padroes suspeitos.

    Args:
        componente: Filtra por componente (ex: 'dispatcher').
        log_dir: Diretorio dos arquivos de log.
        limite: Maximo de resultados.

    Returns:
        Lista de decisoes suspeitas.
    """
    log_path = Path(log_dir)
    decisoes_csv = log_path / 'decisoes.csv'

    if not decisoes_csv.exists():
        return []

    d_path = _sanitizar_path(decisoes_csv)

    conditions = []
    params: list = [limite]

    if componente:
        conditions.append(f"componente LIKE '%{componente}%'")

    # Adicionar filtros de padroes suspeitos
    conditions.append(
        "(resultado = 'sem_entidade' OR resultado = 'vazio' OR resultado = 'desconhecido')"
    )

    where = ' AND '.join(conditions)

    query = f"""
        SELECT
            timestamp, thread_id, turn_id, componente, decisao,
            criterio, threshold, resultado, contexto
        FROM '{d_path}'
        WHERE {where}
        ORDER BY timestamp DESC
        LIMIT ?
    """

    return _executar_query(query, params)


# ══════════════════════════════════════════════════════════════════════════════
# Metricas de Negocio
# ══════════════════════════════════════════════════════════════════════════════


def ticket_medio(log_dir: str | Path = 'logs') -> dict:
    """Calcula ticket medio dos pedidos confirmados.

    Args:
        log_dir: Diretorio dos arquivos de log.

    Returns:
        Dict com ticket_medio_centavos e total_pedidos.
    """
    log_path = Path(log_dir)
    negocio_csv = log_path / 'negocio.csv'

    if not negocio_csv.exists():
        return {'ticket_medio_centavos': 0, 'total_pedidos': 0}

    n_path = _sanitizar_path(negocio_csv)

    query = f"""
        SELECT
            AVG(preco_total_centavos) as ticket_medio,
            COUNT(*) as total
        FROM '{n_path}'
        WHERE evento = 'confirmar' AND preco_total_centavos > 0
    """

    result = _executar_query(query)
    if not result or result[0]['total'] == 0:
        return {'ticket_medio_centavos': 0, 'total_pedidos': 0}

    return {
        'ticket_medio_centavos': result[0]['ticket_medio'],
        'total_pedidos': result[0]['total'],
    }


def taxa_cancelamento(log_dir: str | Path = 'logs') -> dict:
    """Calcula taxa de cancelamento vs confirmacoes.

    Args:
        log_dir: Diretorio dos arquivos de log.

    Returns:
        Dict com confirmacoes, cancelamentos e taxa_cancelamento.
    """
    log_path = Path(log_dir)
    negocio_csv = log_path / 'negocio.csv'

    if not negocio_csv.exists():
        return {'confirmacoes': 0, 'cancelamentos': 0, 'taxa_cancelamento': 0.0}

    n_path = _sanitizar_path(negocio_csv)

    query = f"""
        SELECT
            COUNT(CASE WHEN evento = 'confirmar' THEN 1 END) as confirmacoes,
            COUNT(CASE WHEN evento = 'cancelar' THEN 1 END) as cancelamentos
        FROM '{n_path}'
        WHERE evento IN ('confirmar', 'cancelar')
    """

    result = _executar_query(query)[0]
    confirmacoes = result['confirmacoes']
    cancelamentos = result['cancelamentos']
    total = confirmacoes + cancelamentos

    return {
        'confirmacoes': confirmacoes,
        'cancelamentos': cancelamentos,
        'taxa_cancelamento': cancelamentos / total if total > 0 else 0.0,
    }


def distribuicao_eventos(
    log_dir: str | Path = 'logs',
) -> list[dict]:
    """Retorna distribuicao de eventos de negocio.

    Args:
        log_dir: Diretorio dos arquivos de log.

    Returns:
        Lista de dicts com evento e total.
    """
    log_path = Path(log_dir)
    negocio_csv = log_path / 'negocio.csv'

    if not negocio_csv.exists():
        return []

    n_path = _sanitizar_path(negocio_csv)

    query = f"""
        SELECT evento, COUNT(*) as total
        FROM '{n_path}'
        GROUP BY evento
        ORDER BY total DESC
    """

    return _executar_query(query)


# ══════════════════════════════════════════════════════════════════════════════
# Performance
# ══════════════════════════════════════════════════════════════════════════════


def latencia_p95(log_dir: str | Path = 'logs') -> dict:
    """Calcula latencia p95 e p99 dos componentes.

    Args:
        log_dir: Diretorio dos arquivos de log.

    Returns:
        Dict com p95_ms, p99_ms, media_ms por componente.
    """
    log_path = Path(log_dir)
    fluxo_csv = log_path / 'fluxo.csv'

    if not fluxo_csv.exists():
        return {}

    f_path = _sanitizar_path(fluxo_csv)

    query = f"""
        SELECT
            componente,
            COUNT(*) as total,
            AVG(tempo_ms) as media_ms,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY tempo_ms) as p95_ms,
            PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY tempo_ms) as p99_ms
        FROM '{f_path}'
        WHERE tempo_ms > 0
        GROUP BY componente
        ORDER BY media_ms DESC
    """

    return {r['componente']: r for r in _executar_query(query)}


def tempo_medio_por_componente(
    log_dir: str | Path = 'logs',
) -> list[dict]:
    """Retorna tempo medio por componente.

    Args:
        log_dir: Diretorio dos arquivos de log.

    Returns:
        Lista de dicts com componente, tempo_medio_ms, total_execucoes.
    """
    log_path = Path(log_dir)
    fluxo_csv = log_path / 'fluxo.csv'

    if not fluxo_csv.exists():
        return []

    f_path = _sanitizar_path(fluxo_csv)

    query = f"""
        SELECT
            componente,
            AVG(tempo_ms) as tempo_medio_ms,
            COUNT(*) as total_execucoes
        FROM '{f_path}'
        WHERE tempo_ms > 0
        GROUP BY componente
        ORDER BY tempo_medio_ms DESC
    """

    return _executar_query(query)


# ══════════════════════════════════════════════════════════════════════════════
# Classificacao
# ══════════════════════════════════════════════════════════════════════════════


def distribuicao_caminhos(
    log_dir: str | Path = 'logs',
) -> list[dict]:
    """Retorna distribuicao de caminhos de classificacao.

    Suporta tanto caminho de CSV legado quanto diretório de logs.
    """
    path_input = Path(log_dir)

    # Se é um arquivo CSV (compatibilidade com testes antigos)
    if path_input.suffix == '.csv':
        return distribuicao_caminhos_csv(str(path_input))

    # Novo formato: diretório de logs
    log_path = path_input
    decisoes_csv = log_path / 'decisoes.csv'

    if not decisoes_csv.exists():
        return []

    d_path = _sanitizar_path(decisoes_csv)

    # Extrair caminho do contexto JSON
    query = f"""
        SELECT
            json_extract_string(contexto, '$.caminho') as caminho,
            COUNT(*) as total
        FROM '{d_path}'
        WHERE componente LIKE 'classificacao_%'
          AND json_extract_string(contexto, '$.caminho') != ''
        GROUP BY caminho
        ORDER BY total DESC
    """

    return _executar_query(query)


def distribuicao_caminhos_csv(csv_path: str) -> list[dict]:
    """Retorna distribuicao de caminhos de um CSV legado.

    Compatibilidade com testes antigos.
    """
    path = _sanitizar_path(csv_path)
    query = f"""
        SELECT caminho, COUNT(*) as total
        FROM '{path}'
        GROUP BY caminho
        ORDER BY total DESC
    """
    return _executar_query(query)


def top_intents(
    log_dir: str | Path = 'logs',
    limite: int = 10,
) -> list[dict]:
    """Retorna as intents mais classificadas.

    Args:
        log_dir: Diretorio dos arquivos de log.
        limite: Maximo de resultados.

    Returns:
        Lista de dicts com intent, total.
    """
    log_path = Path(log_dir)
    negocio_csv = log_path / 'negocio.csv'

    if not negocio_csv.exists():
        return []

    n_path = _sanitizar_path(negocio_csv)

    query = f"""
        SELECT intent, COUNT(*) as total
        FROM '{n_path}'
        WHERE intent != ''
        GROUP BY intent
        ORDER BY total DESC
        LIMIT ?
    """

    return _executar_query(query, [limite])


# Compatibilidade com testes antigos (CSV legado)


def baixa_confianca(csv_path: str, limit: int = 20) -> list[dict]:
    path = _sanitizar_path(csv_path)
    query = f"""
        SELECT mensagem, intent, confidence, caminho
        FROM '{path}'
        WHERE caminho IN ('llm_rag', 'llm_fixo')
        ORDER BY confidence ASC
        LIMIT ?
    """
    return _executar_query(query, [limit])


def extracoes_sem_itens(csv_extracao: str, limit: int = 20) -> list[dict]:
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
    path = _sanitizar_path(csv_handler)
    query = f"""
        SELECT handler, AVG(tempo_ms) as tempo_medio_ms, COUNT(*) as total_execucoes
        FROM '{path}'
        GROUP BY handler
        ORDER BY tempo_medio_ms DESC
    """
    return _executar_query(query)
