"""Registry central para loggers de observabilidade.

Permite configurar e acessar os loggers de forma centralizada,
evitando imports circulares e facilitando testes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.observabilidade.clarificacao_logger import ClarificacaoLogger
    from src.observabilidade.extracao_logger import ExtracaoLogger
    from src.observabilidade.funil_logger import FunilLogger
    from src.observabilidade.handler_logger import HandlerLogger
    from src.observabilidade.logger import ObservabilidadeLogger

_obs: ObservabilidadeLogger | None = None
_clarificacao: ClarificacaoLogger | None = None
_extracao: ExtracaoLogger | None = None
_handler: HandlerLogger | None = None
_funil: FunilLogger | None = None


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


def get_extracao_logger() -> ExtracaoLogger | None:
    """Retorna o logger de extração configurado.

    Returns:
        ExtracaoLogger se configurado, None caso contrário.
    """
    return _extracao


def set_extracao_logger(logger: ExtracaoLogger | None) -> None:
    """Configura o logger de extração.

    Args:
        logger: Instância de ExtracaoLogger ou None para limpar.
    """
    global _extracao  # noqa: PLW0603
    _extracao = logger


def get_handler_logger() -> HandlerLogger | None:
    """Retorna o logger de handler configurado.

    Returns:
        HandlerLogger se configurado, None caso contrário.
    """
    return _handler


def set_handler_logger(logger: HandlerLogger | None) -> None:
    """Configura o logger de handler.

    Args:
        logger: Instância de HandlerLogger ou None para limpar.
    """
    global _handler  # noqa: PLW0603
    _handler = logger


def get_funil_logger() -> FunilLogger | None:
    """Retorna o logger de funil configurado.

    Returns:
        FunilLogger se configurado, None caso contrário.
    """
    return _funil


def set_funil_logger(logger: FunilLogger | None) -> None:
    """Configura o logger de funil.

    Args:
        logger: Instância de FunilLogger ou None para limpar.
    """
    global _funil  # noqa: PLW0603
    _funil = logger
