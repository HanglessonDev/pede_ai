"""Logger para rastreamento de fluxo de execução.

Registra por quais componentes uma sessao passou, tempos de execução,
e estado antes/depois de cada componente. Usado para:
- Identificar gargalos de performance
- Rastrear caminho completo de uma sessao
- Detectar componentes que foram (ou não) chamados

Example:
    ```python
    from src.observabilidade.fluxo_logger import FluxoLogger

    logger = FluxoLogger('logs/fluxo.csv')
    logger.registrar(
        thread_id='sessao_001',
        turn_id='turn_0003',
        componente='node_router',
        acao='classificar_mensagem',
        tempo_ms=245.3,
        estado_antes={'modo': 'ocioso', 'carrinho_size': 0},
        estado_depois={'intent': 'pedir', 'confidence': 0.95},
        observacao='caminho=rag_forte',
    )
    ```
"""

from __future__ import annotations

import json

from src.observabilidade.base_logger import BaseCsvLogger

JSON_TRUNCATE_LIMIT = 500
"""Limite maximo de caracteres para campos JSON."""

HEADERS = [
    'timestamp',
    'thread_id',
    'turn_id',
    'componente',
    'acao',
    'tempo_ms',
    'estado_antes',
    'estado_depois',
    'observacao',
]
"""Cabecalhos do CSV de fluxo."""


class FluxoLogger(BaseCsvLogger):
    """Logger thread-safe para rastreamento de fluxo de execução."""

    @property
    def headers(self) -> list[str]:
        return HEADERS

    def _to_row(self, **kwargs) -> list:
        estado_antes = kwargs.get('estado_antes')
        estado_depois = kwargs.get('estado_depois')

        # Serializar estados como JSON
        estado_antes_str = (
            json.dumps(estado_antes, ensure_ascii=False) if estado_antes else ''
        )
        estado_depois_str = (
            json.dumps(estado_depois, ensure_ascii=False) if estado_depois else ''
        )

        # Truncar campos grandes
        if len(estado_antes_str) > JSON_TRUNCATE_LIMIT:
            estado_antes_str = estado_antes_str[:JSON_TRUNCATE_LIMIT] + '...}'
        if len(estado_depois_str) > JSON_TRUNCATE_LIMIT:
            estado_depois_str = estado_depois_str[:JSON_TRUNCATE_LIMIT] + '...}'

        return [
            self._timestamp_utc(),
            kwargs.get('thread_id', ''),
            kwargs.get('turn_id', ''),
            kwargs.get('componente', ''),
            kwargs.get('acao', ''),
            f'{kwargs.get("tempo_ms", 0.0):.2f}',
            estado_antes_str,
            estado_depois_str,
            kwargs.get('observacao', ''),
        ]

    def registrar(
        self,
        thread_id: str,
        turn_id: str,
        componente: str,
        acao: str,
        tempo_ms: float,
        estado_antes: dict | None = None,
        estado_depois: dict | None = None,
        observacao: str = '',
    ) -> None:
        """Registra passagem por um componente.

        Args:
            thread_id: ID da sessao.
            turn_id: ID do turno para correlacao.
            componente: Quem executou (ex: node_router, node_extrator).
            acao: O que fez (ex: classificar_mensagem, extrair_itens).
            tempo_ms: Tempo de execução em milissegundos.
            estado_antes: Estado relevante antes da execução.
            estado_depois: Estado relevante depois da execução.
            observacao: Notas adicionais (ex: caminho=rag_forte).
        """
        super().registrar(
            thread_id=thread_id,
            turn_id=turn_id,
            componente=componente,
            acao=acao,
            tempo_ms=tempo_ms,
            estado_antes=estado_antes,
            estado_depois=estado_depois,
            observacao=observacao,
        )
