"""Registry central para loggers de observabilidade.

Usa dict interno em vez de variaveis de modulo — zero ``global`` statements.
Mantem aliases retroativos para compatibilidade com codigo existente.

Example:
    ```python
    from src.observabilidade.registry import set_logger, get_logger

    set_logger('observabilidade', ObservabilidadeLogger('logs/obs.csv'))
    logger = get_logger('observabilidade')
    ```
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.observabilidade.clarificacao_logger import ClarificacaoLogger
    from src.observabilidade.extracao_logger import ExtracaoLogger
    from src.observabilidade.funil_logger import FunilLogger
    from src.observabilidade.handler_logger import HandlerLogger
    from src.observabilidade.logger import ObservabilidadeLogger


class LoggerRegistry:
    """Registry central para loggers — sem globals.

    Usa dict interno para armazenar loggers por nome.
    """

    def __init__(self) -> None:
        self._loggers: dict[str, object] = {}

    def get(self, nome: str) -> object | None:
        """Retorna logger por nome, ou None se nao configurado."""
        return self._loggers.get(nome)

    def set(self, nome: str, logger: object) -> None:
        """Configura logger por nome."""
        self._loggers[nome] = logger

    def get_required(self, nome: str) -> object:
        """Retorna logger ou levanta RuntimeError se nao configurado."""
        logger = self._loggers.get(nome)
        if logger is None:
            raise RuntimeError(f'Logger "{nome}" nao configurado. Use set_logger().')
        return logger

    def reset(self) -> None:
        """Limpa todos os loggers (util para testes)."""
        self._loggers.clear()


# Singleton global — unico global aceitavel (ponto de entrada)
_registry = LoggerRegistry()


def get_logger(nome: str) -> object | None:
    """Retorna logger por nome, ou None se nao configurado."""
    return _registry.get(nome)


def set_logger(nome: str, logger: object) -> None:
    """Configura logger por nome."""
    _registry.set(nome, logger)


def get_required_logger(nome: str) -> object:
    """Retorna logger ou levanta RuntimeError se nao configurado."""
    return _registry.get_required(nome)


def reset_loggers() -> None:
    """Limpa todos os loggers (util para testes)."""
    _registry.reset()


# ── Aliases retroativos para compatibilidade ────────────────────────────────


def get_obs_logger() -> ObservabilidadeLogger:
    """Retorna o logger de observabilidade configurado."""
    return _registry.get_required('observabilidade')  # type: ignore[return-value]


def set_obs_logger(logger: ObservabilidadeLogger) -> None:
    """Configura o logger de observabilidade."""
    _registry.set('observabilidade', logger)


def get_clarificacao_logger() -> ClarificacaoLogger | None:
    """Retorna o logger de clarificacao configurado."""
    return _registry.get('clarificacao')  # type: ignore[return-value]


def set_clarificacao_logger(logger: ClarificacaoLogger | None) -> None:
    """Configura o logger de clarificacao."""
    _registry.set('clarificacao', logger)


def get_extracao_logger() -> ExtracaoLogger | None:
    """Retorna o logger de extracao configurado."""
    return _registry.get('extracao')  # type: ignore[return-value]


def set_extracao_logger(logger: ExtracaoLogger | None) -> None:
    """Configura o logger de extracao."""
    _registry.set('extracao', logger)


def get_handler_logger() -> HandlerLogger | None:
    """Retorna o logger de handler configurado."""
    return _registry.get('handler')  # type: ignore[return-value]


def set_handler_logger(logger: HandlerLogger | None) -> None:
    """Configura o logger de handler."""
    _registry.set('handler', logger)


def get_funil_logger() -> FunilLogger | None:
    """Retorna o logger de funil configurado."""
    return _registry.get('funil')  # type: ignore[return-value]


def set_funil_logger(logger: FunilLogger | None) -> None:
    """Configura o logger de funil."""
    _registry.set('funil', logger)
