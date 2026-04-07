"""Logger para excecoes com stack trace."""

from __future__ import annotations

import json
import threading
import traceback
from datetime import UTC, datetime
from pathlib import Path

JSON_TRUNCATE_LIMIT = 1000
"""Limite maximo de caracteres para campos JSON."""


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
