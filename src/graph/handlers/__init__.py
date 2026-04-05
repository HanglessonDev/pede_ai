"""Handlers de processamento do grafo de atendimento.

Cada handler encapsula a logica de um tipo especifico de
processamento no fluxo de atendimento.

Example:
    ```python
    from src.graph.handlers import (
        processar_pedido,
        processar_troca,
        processar_remocao,
        processar_saudacao,
        processar_carrinho,
        processar_confirmacao,
        processar_cancelamento,
    )
    ```
"""

from src.graph.handlers.cancelar_handler import processar_cancelamento
from src.graph.handlers.carrinho_handler import processar_carrinho
from src.graph.handlers.clarificacao import ResultadoClarificacao, clarificar
from src.graph.handlers.confirmar_handler import processar_confirmacao
from src.graph.handlers.pedido_handler import ResultadoPedir, processar_pedido
from src.graph.handlers.remocao_handler import ResultadoRemover, processar_remocao
from src.graph.handlers.saudacao_handler import processar_saudacao
from src.graph.handlers.troca_handler import ResultadoTrocar, processar_troca

__all__ = [
    'ResultadoClarificacao',
    'ResultadoPedir',
    'ResultadoRemover',
    'ResultadoTrocar',
    'clarificar',
    'processar_cancelamento',
    'processar_carrinho',
    'processar_confirmacao',
    'processar_pedido',
    'processar_remocao',
    'processar_saudacao',
    'processar_troca',
]
