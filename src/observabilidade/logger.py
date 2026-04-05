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
    'lookup',
    'rag_top1',
    'rag_sim',
    'rag_intent',
    'llm_raw',
    'llm_intent',
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
            kwargs.get('lookup', ''),
            kwargs.get('rag_top1', ''),
            kwargs.get('rag_sim', ''),
            kwargs.get('rag_intent', ''),
            kwargs.get('llm_raw', ''),
            kwargs.get('llm_intent', ''),
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
        lookup: str = '',
        rag_top1: str = '',
        rag_sim: str = '',
        rag_intent: str = '',
        llm_raw: str = '',
        llm_intent: str = '',
    ) -> None:
        """Registra um evento de classificacao no CSV.

        Args:
            lookup: Intencao encontrada por lookup (ou vazio).
            rag_top1: Texto do top1 do RAG (ou vazio).
            rag_sim: Similaridade do top1 do RAG (ou vazio).
            rag_intent: Intencao do top1 do RAG (ou vazio).
            llm_raw: Resposta crua do LLM (ou vazio).
            llm_intent: Intencao extraida do LLM (ou vazio).

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
            lookup=lookup,
            rag_top1=rag_top1,
            rag_sim=rag_sim,
            rag_intent=rag_intent,
            llm_raw=llm_raw,
            llm_intent=llm_intent,
        )
