"""Módulo de observabilidade para classificação de intents.

Este módulo fornece ferramentas para registrar e analisar eventos de
classificação do Pede AI. Permite:

- **Registrar eventos**: Cada classificação é logada em um CSV com
  detalhes como confiança, caminho usado (lookup, RAG, LLM) e o
  exemplo mais similar.
- **Analisar dados**: Consultas DuckDB prontas para extrair insights
  dos logs, como casos de baixa confiança e distribuição de caminhos.

Componentes principais:

- `ObservabilidadeLogger`: Logger thread-safe para registrar eventos
  de classificação em CSV.

Example:
    ```python
    from src.observabilidade import ObservabilidadeLogger
    from src.observabilidade.consultas import distribuicao_caminhos

    # Registrar evento
    logger = ObservabilidadeLogger('logs/eventos.csv')
    logger.registrar(
        thread_id='sessao_123',
        mensagem='Quero um X-Burguer',
        mensagem_norm='querer x-burguer',
        intent='pedido_lanche',
        confidence=0.95,
        caminho='rag_forte',
        top1_texto='quero um x-burguer',
        top1_intencao='pedido_lanche',
    )

    # Analisar distribuição de caminhos
    dist = distribuicao_caminhos('logs/eventos.csv')
    for item in dist:
        print(f'{item["caminho"]}: {item["total"]} eventos')
    ```

Note:
    Os logs são armazenados em CSV para facilitar análise posterior
    com DuckDB, pandas ou ferramentas de visualização.

See Also:
    - `ObservabilidadeLogger`: Classe principal para registrar eventos.
    - `src.observabilidade.consultas`: Funções de análise com DuckDB.
"""

from src.observabilidade.clarificacao_logger import ClarificacaoLogger
from src.observabilidade.extracao_logger import ExtracaoLogger
from src.observabilidade.funil_logger import FunilLogger
from src.observabilidade.handler_logger import HandlerLogger
from src.observabilidade import registry
from src.observabilidade.logger import ObservabilidadeLogger
from src.observabilidade.negocio_logger import NegocioLogger
from src.observabilidade.pedido_logger import PedidoLogger
from src.observabilidade.classificador_logger import ClassificadorLogger
from src.observabilidade.dispatcher_logger import DispatcherLogger
from src.observabilidade.extrator_detail_logger import ExtratorDetailLogger
from src.observabilidade.registry import (
    get_classificador_logger,
    get_clarificacao_logger,
    get_dispatcher_logger,
    get_extracao_logger,
    get_extrator_detail_logger,
    get_funil_logger,
    get_handler_logger,
    get_negocio_logger,
    get_obs_logger,
    get_pedido_logger,
    set_classificador_logger,
    set_clarificacao_logger,
    set_dispatcher_logger,
    set_extracao_logger,
    set_extrator_detail_logger,
    set_funil_logger,
    set_handler_logger,
    set_negocio_logger,
    set_obs_logger,
    set_pedido_logger,
)

__all__ = [
    'ClassificadorLogger',
    'ClarificacaoLogger',
    'DispatcherLogger',
    'ExtracaoLogger',
    'ExtratorDetailLogger',
    'FunilLogger',
    'HandlerLogger',
    'NegocioLogger',
    'ObservabilidadeLogger',
    'PedidoLogger',
    'get_classificador_logger',
    'get_clarificacao_logger',
    'get_dispatcher_logger',
    'get_extracao_logger',
    'get_extrator_detail_logger',
    'get_funil_logger',
    'get_handler_logger',
    'get_negocio_logger',
    'get_obs_logger',
    'get_pedido_logger',
    'registry',
    'set_classificador_logger',
    'set_clarificacao_logger',
    'set_dispatcher_logger',
    'set_extracao_logger',
    'set_extrator_detail_logger',
    'set_funil_logger',
    'set_handler_logger',
    'set_negocio_logger',
    'set_obs_logger',
    'set_pedido_logger',
]
