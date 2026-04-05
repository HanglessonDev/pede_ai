"""Logger para eventos de extracao de itens do cardapio."""

from __future__ import annotations

from datetime import UTC, datetime

from src.observabilidade.base_logger import BaseCsvLogger

HEADERS = [
    'timestamp',
    'thread_id',
    'mensagem',
    'itens_encontrados',
    'itens_ids',
    'variantes_encontradas',
    'tempo_ms',
]


class ExtracaoLogger(BaseCsvLogger):
    """Logger thread-safe para registrar eventos de extracao de itens."""

    @property
    def headers(self) -> list[str]:
        return HEADERS

    def _to_row(self, **kwargs) -> list:
        itens = kwargs.get('itens_extraidos', [])
        return [
            datetime.now(UTC).isoformat(),
            kwargs.get('thread_id', ''),
            kwargs.get('mensagem', ''),
            len(itens),
            '|'.join(i.get('item_id', '') for i in itens),
            '|'.join(i.get('variante', '') or 'None' for i in itens),
            f'{kwargs.get("tempo_ms", 0.0):.2f}',
        ]

    def registrar(
        self,
        thread_id: str,
        mensagem: str,
        itens_extraidos: list[dict],
        tempo_ms: float,
    ) -> None:
        super().registrar(
            thread_id=thread_id,
            mensagem=mensagem,
            itens_extraidos=itens_extraidos,
            tempo_ms=tempo_ms,
        )
