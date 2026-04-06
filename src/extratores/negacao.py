"""Detecção de negação em pedidos.

Identifica quando o usuario está cancelando ou negando um pedido,
em vez de solicitar itens.

Example:
    ```python
    from src.extratores.negacao import detectar_negacao
    from src.extratores.config import get_extrator_config

    config = get_extrator_config()
    detectar_negacao('nao quero hamburguer', config)  # True
    detectar_negacao('hamburguer sem cebola', config)  # False
    ```
"""

from __future__ import annotations

from src.extratores.config import ExtratorConfig


def detectar_negacao(mensagem: str, config: ExtratorConfig) -> bool:
    """Detecta se a mensagem contém negação/cancelamento de pedido.

    Verifica se a mensagem começa com palavras de negação seguidas
    de verbos de desejo (quero, quer, etc.) ou se contém expressões
    completas de cancelamento.

    Args:
        mensagem: Texto da mensagem do usuario.
        config: Configuracao com palavras de negacao.

    Returns:
        True se a mensagem indica negacao/cancelamento.
    """
    texto = mensagem.lower().strip()

    if not texto:
        return False

    # Verifica expressoes compostas de negacao primeiro
    # (ex: 'nao quero', 'quero nao', 'deixa pra la')
    for expressao in config.palavras_negacao:
        if expressao in texto:
            # 'sem' está em palavras_negacao? Nao deveria —
            # 'sem' e palavra de remocao, nao de negacao de pedido.
            # Mas se estiver na lista, precisamos de contexto extra.
            if expressao in ('sem',):
                continue
            return True

    return False
