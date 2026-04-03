"""Registry central para loggers de observabilidade.

Permite configurar e acessar os loggers de forma centralizada,
evitando imports circulares e facilitando testes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.observabilidade.clarificacao_logger import ClarificacaoLogger
    from src.observabilidade.logger import ObservabilidadeLogger

_obs: ObservabilidadeLogger | None = None
_clarificacao: ClarificacaoLogger | None = None


def get_obs_logger() -> ObservabilidadeLogger:
    """Retorna o logger de observabilidade configurado.

    Raises:
        RuntimeError: Se o logger não foi configurado via set_obs_logger().
    """
    if _obs is None:
        raise RuntimeError(
            'ObservabilidadeLogger não inicializado. '
            'Use set_obs_logger() antes de usar o logger.'
        )
    return _obs


def set_obs_logger(logger: ObservabilidadeLogger) -> None:
    """Configura o logger de observabilidade.

    Args:
        logger: Instância de ObservabilidadeLogger.
    """
    global _obs  # noqa: PLW0603
    _obs = logger


def get_clarificacao_logger() -> ClarificacaoLogger | None:
    """Retorna o logger de clarificação configurado.

    Returns:
        ClarificacaoLogger se configurado, None caso contrário.
    """
    return _clarificacao


def set_clarificacao_logger(logger: ClarificacaoLogger | None) -> None:
    """Configura o logger de clarificação.

    Args:
        logger: Instância de ClarificacaoLogger ou None para limpar.
    """
    global _clarificacao  # noqa: PLW0603
    _clarificacao = logger
