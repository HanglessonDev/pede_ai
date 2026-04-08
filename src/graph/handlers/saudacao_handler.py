"""Handler de saudacao.

Gera resposta de saudacao com o nome do restaurante.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.config import get_tenant_nome
from src.graph.state import RetornoNode

if TYPE_CHECKING:
    from src.observabilidade.loggers import ObservabilidadeLoggers


def processar_saudacao(
    loggers: ObservabilidadeLoggers | None = None,
    thread_id: str = '',
    turn_id: str = '',
) -> RetornoNode:
    """Gera resposta de saudacao com o nome do restaurante.

    Args:
        loggers: Loggers de observabilidade (opcional).
        thread_id: ID da sessao (opcional).
        turn_id: ID do turno (opcional).

    Returns:
        Dicionario com ``resposta`` e ``etapa`` atualizados.
    """
    nome_restaurante = get_tenant_nome()
    resposta = f'Ola! Seja bem-vindo(a) a {nome_restaurante}!\nComo posso ajudar?'

    resultado: RetornoNode = {'resposta': resposta, 'modo': 'ocioso'}

    if loggers and loggers.negocio is not None:
        loggers.negocio.registrar(
            thread_id=thread_id,
            turn_id=turn_id,
            evento='saudacao',
            carrinho_size=0,
            preco_total_centavos=0,
            intent='saudacao',
            resposta=resposta,
            tentativas_clarificacao=0,
        )

    return resultado
