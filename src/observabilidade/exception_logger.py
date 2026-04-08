"""Logger para excecoes com stack trace.

Registra exceções em JSONL com estado completo no momento do erro.
Inclui decorator para captura automatica.

Example:
    ```python
    from src.observabilidade.exception_logger import ExceptionLogger

    logger = ExceptionLogger('logs/erros.jsonl')

    # Uso direto
    try:
        processar()
    except Exception as e:
        logger.registrar(
            thread_id='sessao_001',
            turn_id='turn_0003',
            componente='node_handler_pedir',
            exception=e,
            estado={'carrinho': carrinho},
        )
        raise
    ```
"""

from __future__ import annotations

import functools
import json
import threading
import traceback
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar


if TYPE_CHECKING:
    from src.observabilidade.loggers import ObservabilidadeLoggers

JSON_TRUNCATE_LIMIT = 1000
"""Limite maximo de caracteres para campos JSON."""

T = TypeVar('T')


class ExceptionLogger:
    """Logger thread-safe para registrar exceoes em JSONL."""

    def __init__(self, jsonl_path: Path | str) -> None:
        self._jsonl_path = Path(jsonl_path).resolve()
        self._jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    @property
    def jsonl_path(self) -> Path:
        return self._jsonl_path

    def registrar(
        self,
        thread_id: str,
        turn_id: str,
        componente: str,
        exception: BaseException,
        estado: dict | None = None,
    ) -> None:
        """Registra uma excecao no JSONL.

        Args:
            thread_id: ID da sessao.
            turn_id: ID do turno para correlacao.
            componente: Nome do componente onde ocorreu o erro.
            exception: A excecao capturada.
            estado: Estado do sistema no momento do erro.
        """
        registro = {
            'timestamp': datetime.now(UTC).isoformat(),
            'thread_id': thread_id,
            'turn_id': turn_id,
            'componente': componente,
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'traceback': traceback.format_exc(),
            'estado': estado or {},
        }
        linha = json.dumps(registro, ensure_ascii=False, default=str)
        with self._lock, open(self._jsonl_path, 'a', encoding='utf-8') as f:
            f.write(linha + '\n')


def captura_excecao(
    componente: str,
    loggers: ObservabilidadeLoggers | None = None,
    estado_extractor: Callable[..., dict] | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator para capturar exceções automaticamente com contexto.

    Args:
        componente: Nome do componente para logging.
        loggers: Container de loggers. Se None, tenta obter do registry legado.
        estado_extractor: Funcao para extrair estado dos args/kwargs.

    Returns:
        Decorador que captura exceções e logga.

    Example:
        ```python
        @captura_excecao('node_handler_pedir', loggers, _estado_pedir)
        def node_handler_pedir(state: State) -> RetornoNode: ...
        ```
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Obter logger
                exc_logger = None
                if loggers:
                    exc_logger = loggers.excecoes

                if exc_logger:
                    # Extrair thread_id e turn_id dos args
                    thread_id = _extract_thread_id(args, kwargs)
                    turn_id = _extract_turn_id(args, kwargs)
                    estado = (
                        estado_extractor(*args, **kwargs) if estado_extractor else {}
                    )

                    exc_logger.registrar(
                        thread_id=thread_id,
                        turn_id=turn_id,
                        componente=componente,
                        exception=e,
                        estado=estado,
                    )
                raise  # Re-raise para o caller tratar

        return wrapper

    return decorator


def _extract_thread_id(args: tuple, kwargs: dict) -> str:
    """Extrai thread_id de args/kwargs (convencao LangGraph)."""
    # Se primeiro arg é state dict
    if args and isinstance(args[0], dict):
        return args[0].get('thread_id', '')
    return kwargs.get('thread_id', '')


def _extract_turn_id(args: tuple, kwargs: dict) -> str:
    """Extrai turn_id de args/kwargs."""
    if args and isinstance(args[0], dict):
        return args[0].get('turn_id', '')
    return kwargs.get('turn_id', '')
