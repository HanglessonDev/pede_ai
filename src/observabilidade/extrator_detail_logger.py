"""Logger para detalhes internos dos extratores."""

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
    'extrator',
    'estrategia',
    'itens_encontrados',
    'detalhes',
    'tempo_ms',
]


class ExtratorDetailLogger(BaseCsvLogger):
    """Logger thread-safe para detalhes de extracao."""

    @property
    def headers(self) -> list[str]:
        return HEADERS

    def _to_row(self, **kwargs) -> list:
        return [
            datetime.now(UTC).isoformat(),
            kwargs.get('thread_id', ''),
            kwargs.get('turn_id', ''),
            kwargs.get('nivel', 'INFO'),
            kwargs.get('extrator', ''),
            kwargs.get('estrategia', ''),
            kwargs.get('itens_encontrados', 0),
            json.dumps(kwargs.get('detalhes', {}), ensure_ascii=False)[
                :JSON_TRUNCATE_LIMIT
            ],
            f'{kwargs.get("tempo_ms", 0.0):.2f}',
        ]

    def registrar(
        self,
        thread_id: str,
        turn_id: str,
        extrator: str,
        estrategia: str,
        itens_encontrados: int,
        detalhes: dict,
        tempo_ms: float,
        nivel: str = 'INFO',
    ) -> None:
        """Registra detalhe de extracao no CSV.

        Args:
            thread_id: ID da sessao.
            turn_id: ID do turno para correlacao.
            extrator: Nome do extrator (extrator, carrinho_extrator, troca_extrator).
            estrategia: Estrategia usada (spacy, fuzzy, fuzzy_total, etc).
            itens_encontrados: Quantidade de itens encontrados.
            detalhes: Dados especificos do extrator (JSON).
            tempo_ms: Tempo de execucao.
            nivel: Nivel de log.
        """
        if not self.deve_logar(nivel):
            return
        super().registrar(
            thread_id=thread_id,
            turn_id=turn_id,
            nivel=nivel,
            extrator=extrator,
            estrategia=estrategia,
            itens_encontrados=itens_encontrados,
            detalhes=detalhes,
            tempo_ms=tempo_ms,
        )
