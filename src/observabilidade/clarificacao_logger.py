"""Logger para eventos de clarificacao de variantes."""

from __future__ import annotations

from datetime import UTC, datetime

from src.observabilidade.base_logger import BaseCsvLogger

RESULTADOS_VALIDOS = frozenset({'sucesso', 'invalida_reprompt', 'invalida_desistiu'})

HEADERS = [
    'timestamp',
    'thread_id',
    'item_id',
    'nome_item',
    'campo',
    'opcoes',
    'mensagem',
    'tentativas',
    'resultado',
    'variante_escolhida',
]


class ClarificacaoLogger(BaseCsvLogger):
    """Logger thread-safe para registrar eventos de clarificacao."""

    @property
    def headers(self) -> list[str]:
        return HEADERS

    def _to_row(self, **kwargs) -> list:
        resultado = kwargs.get('resultado', '')
        if resultado not in RESULTADOS_VALIDOS:
            raise ValueError(
                f'Resultado invalido: {resultado}. Validos: {RESULTADOS_VALIDOS}'
            )

        return [
            datetime.now(UTC).isoformat(),
            kwargs.get('thread_id', ''),
            kwargs.get('item_id', ''),
            kwargs.get('nome_item', ''),
            kwargs.get('campo', ''),
            ','.join(kwargs.get('opcoes', [])),
            kwargs.get('mensagem', ''),
            kwargs.get('tentativas', 0),
            resultado,
            kwargs.get('variante_escolhida', ''),
        ]

    def registrar(
        self,
        thread_id: str,
        item_id: str,
        nome_item: str,
        campo: str,
        opcoes: list[str],
        mensagem: str,
        tentativas: int,
        resultado: str,
        variante_escolhida: str = '',
    ) -> None:
        super().registrar(
            thread_id=thread_id,
            item_id=item_id,
            nome_item=nome_item,
            campo=campo,
            opcoes=opcoes,
            mensagem=mensagem,
            tentativas=tentativas,
            resultado=resultado,
            variante_escolhida=variante_escolhida,
        )
