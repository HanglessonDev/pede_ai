"""Logger para detalhes internos dos classificadores."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from src.observabilidade.base_logger import BaseCsvLogger

JSON_TRUNCATE_LIMIT = 500
"""Limite maximo de caracteres para campos JSON."""

HEADERS = [
    'timestamp',
    'thread_id',
    'turn_id',
    'nivel',
    'classificador',
    'resultado',
    'intent',
    'confidence',
    'detalhes',
    'tempo_ms',
]


class ClassificadorLogger(BaseCsvLogger):
    """Logger thread-safe para detalhes de classificacao.

    Classificadores: lookup, rag, llm, service.
    """

    @property
    def headers(self) -> list[str]:
        return HEADERS

    def _to_row(self, **kwargs) -> list:
        return [
            datetime.now(UTC).isoformat(),
            kwargs.get('thread_id', ''),
            kwargs.get('turn_id', ''),
            kwargs.get('nivel', 'INFO'),
            kwargs.get('classificador', ''),
            kwargs.get('resultado', ''),
            kwargs.get('intent', ''),
            kwargs.get('confidence', 0.0),
            json.dumps(kwargs.get('detalhes', {}), ensure_ascii=False)[:JSON_TRUNCATE_LIMIT],
            f'{kwargs.get("tempo_ms", 0.0):.2f}',
        ]

    def registrar(
        self,
        thread_id: str,
        turn_id: str,
        classificador: str,
        resultado: str,
        intent: str,
        confidence: float,
        detalhes: dict,
        tempo_ms: float,
        nivel: str = 'INFO',
    ) -> None:
        """Registra detalhe de classificacao no CSV.

        Args:
            thread_id: ID da sessao.
            turn_id: ID do turno para correlacao.
            classificador: Nome do classificador (lookup, rag, llm, service).
            resultado: 'sucesso' ou 'falha'.
            intent: Intent classificada (vazia se falha).
            confidence: Confianca da classificacao.
            detalhes: Dados especificos do classificador (serializado JSON).
            tempo_ms: Tempo de execucao em milissegundos.
            nivel: Nivel de log (INFO, DEBUG, TRACE).
        """
        if not self.deve_logar(nivel):
            return
        super().registrar(
            thread_id=thread_id,
            turn_id=turn_id,
            nivel=nivel,
            classificador=classificador,
            resultado=resultado,
            intent=intent,
            confidence=confidence,
            detalhes=detalhes,
            tempo_ms=tempo_ms,
        )
