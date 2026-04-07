"""Logger para pedidos processados."""

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
    'itens_adicionados',
    'itens_fila',
    'total_itens',
    'preco_total_centavos',
    'modo_saida',
    'resposta',
]


class PedidoLogger(BaseCsvLogger):
    """Logger thread-safe para registrar pedidos processados."""

    @property
    def headers(self) -> list[str]:
        return HEADERS

    def _to_row(self, **kwargs) -> list:
        itens = kwargs.get('itens_adicionados', [])
        fila = kwargs.get('itens_fila', [])
        return [
            datetime.now(UTC).isoformat(),
            kwargs.get('thread_id', ''),
            kwargs.get('turn_id', ''),
            kwargs.get('nivel', 'INFO'),
            json.dumps(itens, ensure_ascii=False)[:JSON_TRUNCATE_LIMIT],
            json.dumps(fila, ensure_ascii=False)[:JSON_TRUNCATE_LIMIT],
            kwargs.get('total_itens', 0),
            kwargs.get('preco_total_centavos', 0),
            kwargs.get('modo_saida', ''),
            kwargs.get('resposta', ''),
        ]

    def registrar(
        self,
        thread_id: str,
        turn_id: str,
        itens_adicionados: list[dict],
        itens_fila: list[dict],
        total_itens: int,
        preco_total_centavos: int,
        modo_saida: str,
        resposta: str = '',
        nivel: str = 'INFO',
    ) -> None:
        """Registra um pedido processado no CSV.

        Args:
            thread_id: ID da sessao.
            turn_id: ID do turno para correlacao.
            itens_adicionados: Lista de itens adicionados ao carrinho.
            itens_fila: Lista de itens pendentes de clarificacao.
            total_itens: Quantidade de itens adicionados.
            preco_total_centavos: Soma dos precos em centavos.
            modo_saida: Modo resultante ('coletando' ou 'clarificando').
            resposta: Texto gerado para o usuario.
            nivel: Nivel de log (INFO, DEBUG, TRACE).
        """
        if not self.deve_logar(nivel):
            return
        super().registrar(
            thread_id=thread_id,
            turn_id=turn_id,
            nivel=nivel,
            itens_adicionados=itens_adicionados,
            itens_fila=itens_fila,
            total_itens=total_itens,
            preco_total_centavos=preco_total_centavos,
            modo_saida=modo_saida,
            resposta=resposta,
        )
