"""Logger para eventos de negocio."""

from __future__ import annotations

from datetime import UTC, datetime

from src.observabilidade.base_logger import BaseCsvLogger

HEADERS = [
    'timestamp',
    'thread_id',
    'turn_id',
    'nivel',
    'evento',
    'carrinho_size',
    'preco_total_centavos',
    'intent',
    'resposta',
    'tentativas_clarificacao',
]


class NegocioLogger(BaseCsvLogger):
    """Logger thread-safe para registrar eventos de negocio.

    Eventos: confirmar, cancelar, saudacao, desconhecido,
    carrinho, remover, trocar.
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
        nivel: str = 'INFO',
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
            nivel: Nivel de log (INFO, DEBUG, TRACE).
        """
        if not self.deve_logar(nivel):
            return
        super().registrar(
            thread_id=thread_id,
            turn_id=turn_id,
            nivel=nivel,
            evento=evento,
            carrinho_size=carrinho_size,
            preco_total_centavos=preco_total_centavos,
            intent=intent,
            resposta=resposta,
            tentativas_clarificacao=tentativas_clarificacao,
        )
