"""Handler de saudacao.

Gera resposta de saudacao com o nome do restaurante.
"""

from __future__ import annotations

from src.config import get_tenant_nome
from src.graph.state import RetornoNode


def processar_saudacao() -> RetornoNode:
    """Gera resposta de saudacao com o nome do restaurante.

    Returns:
        Dicionario com ``resposta`` e ``etapa`` atualizados.
    """
    nome_restaurante = get_tenant_nome()
    resposta = f'Ola! Seja bem-vindo(a) a {nome_restaurante}!\nComo posso ajudar?'
    return {'resposta': resposta, 'etapa': 'saudacao'}
