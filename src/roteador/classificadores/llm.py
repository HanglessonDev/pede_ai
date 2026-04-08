"""Classificador LLM puro — fallback definitivo.

Quando RAG e lookup nao conseguem classificar, o LLM assume.
Sempre retorna um resultado — nunca retorna None.

Example:
    ```python
    from src.roteador.classificadores.llm import ClassificadorLLM

    llm = ClassificadorLLM(provider, prompt_template, intencoes_validas)
    resultado = llm.classificar('mensagem estranha')
    resultado.intent  # 'desconhecido' ou intencao valida
    ```
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.roteador.classificadores.base import ClassificadorBase
from src.roteador.modelos import ResultadoClassificacao
from src.roteador.protocolos import LLMProvider

if TYPE_CHECKING:
    from src.observabilidade.loggers import ObservabilidadeLoggers


class ClassificadorLLM(ClassificadorBase):
    """Fallback com LLM puro.

    Usa prompt fixo para classificar a mensagem.
    Nunca retorna None — e o fallback definitivo.
    """

    def __init__(
        self,
        llm: LLMProvider,
        prompt_template: str,
        intencoes_validas: list[str],
        loggers: ObservabilidadeLoggers | None = None,
    ) -> None:
        """Inicializa o classificador LLM.

        Args:
            llm: Provider concreto de LLM.
            prompt_template: Template do prompt com placeholder {mensagem}.
            intencoes_validas: Lista de intents validas para validacao.
            loggers: Loggers de observabilidade para decision tracing.
        """
        self._llm = llm
        self._prompt_template = prompt_template
        self._intencoes_validas = intencoes_validas
        self._loggers = loggers

    def classificar(
        self,
        mensagem: str,
        thread_id: str = '',
        turn_id: str = '',
    ) -> ResultadoClassificacao:
        """Classifica via LLM puro — sempre retorna algo.

        Args:
            mensagem: Texto da mensagem do usuario.
            thread_id: ID da sessao para correlacao de logs.
            turn_id: ID do turno para correlacao de logs.

        Returns:
            ResultadoClassificacao com intent do LLM.
            Confidence 1.0 (confianca total no fallback).

        Example:
            ```python
            llm = ClassificadorLLM(provider, prompt, intencoes)
            llm.classificar('xyz123')
            ResultadoClassificacao(intent='desconhecido', ...)
            ```
        """
        prompt = self._prompt_template.format(mensagem=mensagem)
        resposta = self._llm.completar(prompt, max_tokens=10)

        intencao = self._extrair_intencao(resposta)

        if self._loggers and self._loggers.decisor:
            self._loggers.decisor.registrar(
                thread_id=thread_id,
                turn_id=turn_id,
                componente='classificacao_llm_fallback',
                decisao='retornar_llm',
                alternativas=list(self._intencoes_validas)[:5],
                criterio=f"llm_retornou='{resposta.strip()}'",
                threshold='llm_fixo',
                resultado=intencao,
                contexto={
                    'mensagem': mensagem,
                    'llm_raw': resposta.strip(),
                },
            )

        return ResultadoClassificacao(
            intent=intencao,
            confidence=1.0,
            caminho='llm_fixo',
            top1_texto='',
            top1_intencao='',
            mensagem_norm=mensagem,
            metadados={
                'llm_raw': resposta.strip(),
                'llm_intent': intencao,
            },
        )

    def _extrair_intencao(self, resposta: str) -> str:
        """Extrai intencao valida da resposta do LLM.

        Args:
            resposta: Texto bruto da resposta do LLM.

        Returns:
            Intencao valida ou 'desconhecido'.
        """
        if not resposta or not resposta.strip():
            return 'desconhecido'

        intencao = resposta.strip().lower().split()[0]

        if intencao not in self._intencoes_validas:
            return 'desconhecido'

        return intencao
