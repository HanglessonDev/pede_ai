"""Modulo de observabilidade para o Pede AI.

Fornece ferramentas para registrar e analisar eventos do sistema:
- **Decision tracing**: Cada bifurcação de decisão com alternativas consideradas
- **Fluxo de execução**: Por onde passou, tempos, estado antes/depois
- **Metricas de negocio**: Confirmacoes, cancelamentos, ticket medio
- **Exception handling**: Stack traces com estado no momento do erro

Componentes principais:

- `DecisorLogger`: Registra CADA decisão com alternativas, criterio, threshold
- `FluxoLogger`: Registra caminho de execução e tempos
- `NegocioLogger`: Metricas de negocio (confirmar, cancelar, etc)
- `ExceptionLogger`: Exceções com stack trace + estado
- `ObservabilidadeLoggers`: Container para injeção direta (zero registry)

Example:
    ```python
    from src.observabilidade.loggers import ObservabilidadeLoggers

    # Criar todos os loggers
    loggers = ObservabilidadeLoggers.criar_padrao('logs')

    # Decision tracing
    loggers.decisor.registrar(
        thread_id='sessao_001',
        turn_id='turn_0003',
        componente='classificacao_lookup',
        decisao='retornar_saudacao',
        alternativas=['saudacao(1.0)', 'pedir(0.0)'],
        criterio="token_exato: 'oi'",
        threshold='match_exato',
        resultado='saudacao',
    )

    # Fluxo
    loggers.fluxo.registrar(
        thread_id='sessao_001',
        turn_id='turn_0003',
        componente='node_router',
        acao='classificar_mensagem',
        tempo_ms=245.3,
    )
    ```
"""

from src.observabilidade.base_logger import BaseCsvLogger
from src.observabilidade.contexto import (
    extrair_contexto_classificacao,
    extrair_contexto_dispatcher,
    extrair_contexto_extracao,
    extrair_contexto_negacao,
)
from src.observabilidade.decisor_logger import DecisorLogger
from src.observabilidade.exception_logger import ExceptionLogger, captura_excecao
from src.observabilidade.fluxo_logger import FluxoLogger
from src.observabilidade.loggers import ObservabilidadeLoggers
from src.observabilidade.negocio_logger import NegocioLogger

# Manter compatibilidade com código legado durante transição
import contextlib

with contextlib.suppress(ImportError):
    from src.observabilidade.registry import (
        get_clarificacao_logger,
        get_classificador_logger,
        get_debug_session_logger,
        get_dispatcher_logger,
        get_exception_logger,
        get_extracao_logger,
        get_extrator_detail_logger,
        get_funil_logger,
        get_handler_logger,
        get_negocio_logger,
        get_obs_logger,
        get_pedido_logger,
        set_clarificacao_logger,
        set_classificador_logger,
        set_dispatcher_logger,
        set_exception_logger,
        set_extracao_logger,
        set_extrator_detail_logger,
        set_funil_logger,
        set_handler_logger,
        set_negocio_logger,
        set_obs_logger,
        set_pedido_logger,
    )

__all__ = [
    'BaseCsvLogger',
    'DecisorLogger',
    'ExceptionLogger',
    'FluxoLogger',
    'NegocioLogger',
    'ObservabilidadeLoggers',
    'captura_excecao',
    'extrair_contexto_classificacao',
    'extrair_contexto_dispatcher',
    'extrair_contexto_extracao',
    'extrair_contexto_negacao',
    'get_clarificacao_logger',
    'get_classificador_logger',
    'get_debug_session_logger',
    'get_dispatcher_logger',
    'get_exception_logger',
    'get_extracao_logger',
    'get_extrator_detail_logger',
    'get_funil_logger',
    'get_handler_logger',
    'get_negocio_logger',
    'get_obs_logger',
    'get_pedido_logger',
    'set_clarificacao_logger',
    'set_classificador_logger',
    'set_dispatcher_logger',
    'set_exception_logger',
    'set_extracao_logger',
    'set_extrator_detail_logger',
    'set_funil_logger',
    'set_handler_logger',
    'set_negocio_logger',
    'set_obs_logger',
    'set_pedido_logger',
]
