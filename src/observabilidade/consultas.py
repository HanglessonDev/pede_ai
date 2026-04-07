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


# ══════════════════════════════════════════════════════════════════════════════
# Métricas de Negócio (novas)
# ══════════════════════════════════════════════════════════════════════════════


def pedidos_confirmados(csv_negocio: str) -> list[dict]:
    """Retorna todos os pedidos confirmados com valores."""
    path = _sanitizar_path(csv_negocio)
    query = f"""
        SELECT thread_id, turn_id, carrinho_size, preco_total_centavos,
               resposta, timestamp
        FROM '{path}'
        WHERE evento = 'confirmar'
        ORDER BY timestamp DESC
    """
    return _executar_query(query)


def pedidos_cancelados(csv_negocio: str) -> list[dict]:
    """Retorna todos os pedidos cancelados com valores descartados."""
    path = _sanitizar_path(csv_negocio)
    query = f"""
        SELECT thread_id, turn_id, carrinho_size, preco_total_centavos,
               resposta, timestamp
        FROM '{path}'
        WHERE evento = 'cancelar'
        ORDER BY timestamp DESC
    """
    return _executar_query(query)


def ticket_medio(csv_negocio: str) -> dict:
    """Calcula ticket medio dos pedidos confirmados."""
    confirmados = pedidos_confirmados(csv_negocio)
    if not confirmados:
        return {'ticket_medio_centavos': 0, 'total_pedidos': 0}
    total = sum(p['preco_total_centavos'] for p in confirmados)
    return {
        'ticket_medio_centavos': total / len(confirmados),
        'total_pedidos': len(confirmados),
    }


def taxa_cancelamento(csv_negocio: str) -> dict:
    """Calcula taxa de cancelamento vs confirmacoes."""
    path = _sanitizar_path(csv_negocio)
    query = f"""
        SELECT
            COUNT(CASE WHEN evento = 'confirmar' THEN 1 END) as confirmacoes,
            COUNT(CASE WHEN evento = 'cancelar' THEN 1 END) as cancelamentos
        FROM '{path}'
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


def itens_desconhecidos(csv_negocio: str, limit: int = 20) -> list[dict]:
    """Retorna intents desconhecidas para analise."""
    path = _sanitizar_path(csv_negocio)
    query = f"""
        SELECT thread_id, turn_id, resposta, timestamp
        FROM '{path}'
        WHERE evento = 'desconhecido'
        ORDER BY timestamp DESC
        LIMIT ?
    """
    return _executar_query(query, [limit])


def sessao_completa(
    csv_classificacoes: str,
    csv_extracoes: str,
    csv_pedidos: str,
    csv_negocio: str,
    csv_handlers: str,
    csv_funil: str,
    thread_id: str,
    turn_id: str,
) -> dict:
    """Junta todos os eventos de um turno para debugging.

    Faz LEFT JOIN entre todos os CSVs por thread_id + turn_id.
    """
    c = _sanitizar_path(csv_classificacoes)
    e = _sanitizar_path(csv_extracoes)
    p = _sanitizar_path(csv_pedidos)
    n = _sanitizar_path(csv_negocio)
    h = _sanitizar_path(csv_handlers)
    f = _sanitizar_path(csv_funil)

    query = f"""
        SELECT
            c.intent, c.confidence, c.caminho,
            c.top1_texto, c.top1_intencao,
            e.itens_encontrados, e.tempo_ms as extracao_tempo_ms,
            p.itens_adicionados, p.preco_total_centavos as pedido_preco,
            p.modo_saida,
            n.evento as negocio_evento, n.resposta as negocio_resposta,
            h.handler, h.tempo_ms as handler_tempo_ms, h.erro,
            f.modo_atual, f.carrinho_size
        FROM '{c}' c
        LEFT JOIN '{e}' e ON c.thread_id = e.thread_id AND c.turn_id = e.turn_id
        LEFT JOIN '{p}' p ON c.thread_id = p.thread_id AND c.turn_id = p.turn_id
        LEFT JOIN '{n}' n ON c.thread_id = n.thread_id AND c.turn_id = n.turn_id
        LEFT JOIN '{h}' h ON c.thread_id = h.thread_id AND c.turn_id = h.turn_id
        LEFT JOIN '{f}' f ON c.thread_id = f.thread_id AND c.turn_id = f.turn_id
        WHERE c.thread_id = ? AND c.turn_id = ?
    """
    results = _executar_query(query, [thread_id, turn_id])
    return results[0] if results else {}


def distribuicao_eventos_negocio(csv_negocio: str) -> list[dict]:
    """Retorna distribuicao de eventos de negocio."""
    path = _sanitizar_path(csv_negocio)
    query = f"""
        SELECT evento, COUNT(*) as total
        FROM '{path}'
        GROUP BY evento
        ORDER BY total DESC
    """
    return _executar_query(query)


def top_intents(csv_classificacoes: str, limit: int = 10) -> list[dict]:
    """Retorna as intents mais classificadas."""
    path = _sanitizar_path(csv_classificacoes)
    query = f"""
        SELECT intent, COUNT(*) as total, AVG(confidence) as avg_confidence
        FROM '{path}'
        GROUP BY intent
        ORDER BY total DESC
        LIMIT ?
    """
    return _executar_query(query, [limit])
