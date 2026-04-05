"""Logger de observabilidade para classificacao de intents.

Herda BaseCsvLogger — boilerplate CSV e thread safety sao herdados.
"""

from __future__ import annotations

from datetime import UTC, datetime

from src.observabilidade.base_logger import BaseCsvLogger

CAMINHOS_VALIDOS = frozenset(
    {'lookup', 'rag_forte', 'llm_rag', 'llm_fixo', 'desconhecido'}
)
"""Caminhos validos para o parametro ``caminho``."""

HEADERS = [
    'timestamp',
    'thread_id',
    'mensagem',
    'mensagem_norm',
    'intent',
    'confidence',
    'caminho',
    'top1_texto',
    'top1_intencao',
]
"""Cabecalhos do CSV de eventos de classificacao."""


class ObservabilidadeLogger(BaseCsvLogger):
    """Logger thread-safe para registrar eventos de classificacao."""

    @property
    def headers(self) -> list[str]:
        return HEADERS

    def _to_row(self, **kwargs) -> list:
        caminho = kwargs.get('caminho', '')
        if caminho not in CAMINHOS_VALIDOS:
            raise ValueError(
                f'Caminho invalido: {caminho}. Validos: {CAMINHOS_VALIDOS}'
            )

        return [
            datetime.now(UTC).isoformat(),
            kwargs.get('thread_id', ''),
            kwargs.get('mensagem', ''),
            kwargs.get('mensagem_norm', ''),
            kwargs.get('intent', ''),
            kwargs.get('confidence', 0.0),
            caminho,
            kwargs.get('top1_texto', ''),
            kwargs.get('top1_intencao', ''),
        ]

    def registrar(
        self,
        thread_id: str,
        mensagem: str,
        mensagem_norm: str,
        intent: str,
        confidence: float,
        caminho: str,
        top1_texto: str,
        top1_intencao: str,
    ) -> None:
        """Registra um evento de classificacao no CSV.

        Raises:
            ValueError: Se ``caminho`` nao estiver em ``CAMINHOS_VALIDOS``.
        """
        super().registrar(
            thread_id=thread_id,
            mensagem=mensagem,
            mensagem_norm=mensagem_norm,
            intent=intent,
            confidence=confidence,
            caminho=caminho,
            top1_texto=top1_texto,
            top1_intencao=top1_intencao,
        )
