"""Logger generico para execucao de handlers."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from src.observabilidade.base_logger import BaseCsvLogger

JSON_TRUNCATE_LIMIT = 200
"""Limite maximo de caracteres para campos JSON serializados."""

HEADERS = [
    'timestamp',
    'thread_id',
    'handler',
    'intent',
    'input_resumo',
    'output_resumo',
    'tempo_ms',
    'erro',
]


class HandlerLogger(BaseCsvLogger):
    """Logger thread-safe para registrar execucoes de handlers."""

    @property
    def headers(self) -> list[str]:
        return HEADERS

    def _to_row(self, **kwargs) -> list:
        return [
            datetime.now(UTC).isoformat(),
            kwargs.get('thread_id', ''),
            kwargs.get('handler', ''),
            kwargs.get('intent', ''),
            json.dumps(kwargs.get('input_dados', {}), ensure_ascii=False)[
                :JSON_TRUNCATE_LIMIT
            ],
            json.dumps(kwargs.get('output_dados', {}), ensure_ascii=False)[
                :JSON_TRUNCATE_LIMIT
            ],
            f'{kwargs.get("tempo_ms", 0.0):.2f}',
            kwargs.get('erro') or '',
        ]

    def registrar(
        self,
        thread_id: str,
        handler: str,
        intent: str,
        input_dados: dict,
        output_dados: dict,
        tempo_ms: float,
        erro: str | None = None,
    ) -> None:
        super().registrar(
            thread_id=thread_id,
            handler=handler,
            intent=intent,
            input_dados=input_dados,
            output_dados=output_dados,
            tempo_ms=tempo_ms,
            erro=erro,
        )
