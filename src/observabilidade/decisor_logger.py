"""Logger para decision tracing — registra cada bifurcação de decisão.

Diferente de logs tradicionais que registram apenas o resultado final,
este logger registra CADA decisão com:
- Alternativas consideradas
- Criterio usado para escolher
- Thresholds aplicados
- Contexto no momento da decisão

Isso permite reconstruir EXATAMENTE por que o sistema tomou um caminho
em vez de outro, essencial para caçar bugs de lógica (não apenas exceptions).

Example:
    ```python
    from src.observabilidade.decisor_logger import DecisorLogger

    logger = DecisorLogger('logs/decisoes.csv')
    logger.registrar(
        thread_id='sessao_001',
        turn_id='turn_0003',
        componente='classificacao_lookup',
        decisao='retornar_saudacao',
        alternativas=['saudacao(1.0)', 'pedir(0.0)', 'desconhecido(0.0)'],
        criterio="token_exato_encontrado: 'oi'",
        threshold='match_exato',
        resultado='saudacao',
        contexto={'mensagem': 'oi tira uma duvida'},
    )
    ```
"""

from __future__ import annotations

import json

from src.observabilidade.base_logger import BaseCsvLogger

JSON_TRUNCATE_LIMIT = 1000
"""Limite maximo de caracteres para campos JSON."""

HEADERS = [
    'timestamp',
    'thread_id',
    'turn_id',
    'componente',
    'decisao',
    'alternativas',
    'criterio',
    'threshold',
    'resultado',
    'contexto',
]
"""Cabecalhos do CSV de decisoes."""


class DecisorLogger(BaseCsvLogger):
    """Logger thread-safe para decision tracing.

    Registra cada bifurcação de decisão com alternativas consideradas,
    criterio, threshold e contexto. Essencial para caçar bugs de lógica.
    """

    @property
    def headers(self) -> list[str]:
        return HEADERS

    def _to_row(self, **kwargs) -> list:
        alternativas = kwargs.get('alternativas', [])
        contexto = kwargs.get('contexto', {})

        # Serializar como JSON
        if isinstance(alternativas, list):
            alternativas_str = json.dumps(alternativas, ensure_ascii=False)
        else:
            alternativas_str = str(alternativas)

        contexto_str = json.dumps(contexto, ensure_ascii=False) if contexto else ''

        # Truncar campos grandes
        if len(alternativas_str) > JSON_TRUNCATE_LIMIT:
            alternativas_str = alternativas_str[:JSON_TRUNCATE_LIMIT] + '...]'
        if len(contexto_str) > JSON_TRUNCATE_LIMIT:
            contexto_str = contexto_str[:JSON_TRUNCATE_LIMIT] + '...}'

        return [
            self._timestamp_utc(),
            kwargs.get('thread_id', ''),
            kwargs.get('turn_id', ''),
            kwargs.get('componente', ''),
            kwargs.get('decisao', ''),
            alternativas_str,
            kwargs.get('criterio', ''),
            kwargs.get('threshold', ''),
            kwargs.get('resultado', ''),
            contexto_str,
        ]

    def registrar(
        self,
        thread_id: str,
        turn_id: str,
        componente: str,
        decisao: str,
        alternativas: list[str] | str,
        criterio: str,
        threshold: str = '',
        resultado: str = '',
        contexto: dict | None = None,
    ) -> None:
        """Registra uma decisão com alternativas consideradas.

        Args:
            thread_id: ID da sessao.
            turn_id: ID do turno para correlacao.
            componente: Quem decidiu (ex: classificacao_lookup, dispatcher_passo1).
            decisao: O que foi decidido (ex: retornar_saudacao, sem_entidade).
            alternativas: O que mais poderia ter sido escolhido.
            criterio: POR QUE escolheu isso.
            threshold: Threshold usado (se aplicavel).
            resultado: Resultado final da decisao.
            contexto: Estado relevante no momento (serializado JSON).
        """
        super().registrar(
            thread_id=thread_id,
            turn_id=turn_id,
            componente=componente,
            decisao=decisao,
            alternativas=alternativas,
            criterio=criterio,
            threshold=threshold,
            resultado=resultado,
            contexto=contexto or {},
        )
