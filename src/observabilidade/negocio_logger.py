"""Logger para eventos de negocio.

Registra eventos de metricas de negocio (confirmar, cancelar, etc)
em CSV tabular para análise com DuckDB.

Sem validação rígida de enums — logger nunca crasha.

Example:
    ```python
    from src.observabilidade.negocio_logger import NegocioLogger

    logger = NegocioLogger('logs/negocio.csv')
    logger.registrar(
        thread_id='sessao_001',
        turn_id='turn_0003',
        evento='confirmar',
        carrinho_size=3,
        preco_total_centavos=4500,
        intent='confirmar',
        resposta='Pedido confirmado!',
    )
    ```
"""

from __future__ import annotations

from src.observabilidade.base_logger import BaseCsvLogger

HEADERS = [
    'timestamp',
    'thread_id',
    'turn_id',
    'evento',
    'carrinho_size',
    'preco_total_centavos',
    'intent',
    'resposta',
    'tentativas_clarificacao',
]
"""Cabecalhos do CSV de negocio."""


class NegocioLogger(BaseCsvLogger):
    """Logger thread-safe para registrar eventos de negocio.

    Eventos: confirmar, cancelar, saudacao, desconhecido,
    carrinho, remover, trocar, etc.
    """

    @property
    def headers(self) -> list[str]:
        return HEADERS

    def _to_row(self, **kwargs) -> list:
        return [
            self._timestamp_utc(),
            kwargs.get('thread_id', ''),
            kwargs.get('turn_id', ''),
            kwargs.get('evento', ''),
            kwargs.get('carrinho_size', 0),
            kwargs.get('preco_total_centavos', 0),
            kwargs.get('intent', ''),
            kwargs.get('resposta', ''),
            kwargs.get('tentativas_clarificacao', 0),
        ]

    def registrar(
        self,
        thread_id: str,
        turn_id: str,
        evento: str,
        carrinho_size: int,
        preco_total_centavos: int,
        intent: str,
        resposta: str = '',
        tentativas_clarificacao: int = 0,
    ) -> None:
        """Registra um evento de negocio no CSV.

        Args:
            thread_id: ID da sessao.
            turn_id: ID do turno para correlacao.
            evento: Tipo do evento (confirmar, cancelar, saudacao, etc).
            carrinho_size: Tamanho do carrinho no momento do evento.
            preco_total_centavos: Valor total em centavos.
            intent: Intencao classificada.
            resposta: Texto gerado para o usuario.
            tentativas_clarificacao: Contador de tentativas de clarificacao.
        """
        super().registrar(
            thread_id=thread_id,
            turn_id=turn_id,
            evento=evento,
            carrinho_size=carrinho_size,
            preco_total_centavos=preco_total_centavos,
            intent=intent,
            resposta=resposta,
            tentativas_clarificacao=tentativas_clarificacao,
        )
