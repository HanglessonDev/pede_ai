"""Logger para progressao no funil de pedidos."""

from __future__ import annotations

from datetime import UTC, datetime

from src.observabilidade.base_logger import BaseCsvLogger

HEADERS = [
    'timestamp',
    'thread_id',
    'modo_anterior',
    'modo_atual',
    'intent',
    'carrinho_size',
]


class FunilLogger(BaseCsvLogger):
    """Logger thread-safe para registrar transicoes no funil."""

    @property
    def headers(self) -> list[str]:
        return HEADERS

    def _to_row(self, **kwargs) -> list:
        return [
            datetime.now(UTC).isoformat(),
            kwargs.get('thread_id', ''),
            kwargs.get('modo_anterior', ''),
            kwargs.get('modo_atual', ''),
            kwargs.get('intent', ''),
            kwargs.get('carrinho_size', 0),
        ]

    def registrar(
        self,
        thread_id: str,
        modo_anterior: str,
        modo_atual: str,
        intent: str,
        carrinho_size: int = 0,
    ) -> None:
        super().registrar(
            thread_id=thread_id,
            modo_anterior=modo_anterior,
            modo_atual=modo_atual,
            intent=intent,
            carrinho_size=carrinho_size,
        )
