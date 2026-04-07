"""Logger para decisoes do dispatcher de modificacao."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from src.observabilidade.base_logger import BaseCsvLogger

JSON_TRUNCATE_LIMIT = 500

HEADERS = [
    'timestamp',
    'thread_id',
    'turn_id',
    'nivel',
    'acao_final',
    'passos',
    'tempo_ms',
]


class DispatcherLogger(BaseCsvLogger):
    """Logger thread-safe para decisoes do dispatcher."""

    @property
    def headers(self) -> list[str]:
        return HEADERS

    def _to_row(self, **kwargs) -> list:
        return [
            datetime.now(UTC).isoformat(),
            kwargs.get('thread_id', ''),
            kwargs.get('turn_id', ''),
            kwargs.get('nivel', 'INFO'),
            kwargs.get('acao_final', ''),
            json.dumps(kwargs.get('passos', {}), ensure_ascii=False)[
                :JSON_TRUNCATE_LIMIT
            ],
            f'{kwargs.get("tempo_ms", 0.0):.2f}',
        ]

    def registrar(
        self,
        thread_id: str,
        turn_id: str,
        acao_final: str,
        passos: dict,
        tempo_ms: float,
        nivel: str = 'INFO',
    ) -> None:
        """Registra decisao do dispatcher no CSV.

        Args:
            thread_id: ID da sessao.
            turn_id: ID do turno para correlacao.
            acao_final: Acao decidida (adicionar_item, trocar_variante, etc).
            passos: Estado de cada passo do dispatcher (JSON).
            tempo_ms: Tempo total do dispatcher.
            nivel: Nivel de log.
        """
        if not self.deve_logar(nivel):
            return
        super().registrar(
            thread_id=thread_id,
            turn_id=turn_id,
            nivel=nivel,
            acao_final=acao_final,
            passos=passos,
            tempo_ms=tempo_ms,
        )
