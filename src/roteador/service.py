"""Orquestrador do classificador de intencoes.

Coordena a cadeia de classificadores: lookup -> RAG -> LLM fallback.
Ponto de entrada principal para classificacao de intencoes.

Example:
    ```python
    from src.roteador.service import ClassificadorIntencoes

    classificador = ClassificadorIntencoes(
        llm, embedding_service, config, prompt, intencoes
    )
    resultado = classificador.classificar('quero um xbacon')
    resultado.intent  # 'pedir'
    ```
"""

from __future__ import annotations

import re

from src.config.roteador_config import RoteadorConfig
from src.roteador.classificadores.llm import ClassificadorLLM
from src.roteador.classificadores.lookup import ClassificadorLookup, TOKENS_UNICOS
from src.roteador.classificadores.rag import ClassificadorRAG
from src.roteador.embedding_service import EmbeddingService
from src.roteador.modelos import ResultadoClassificacao
from src.roteador.protocolos import LLMProvider


def _get_exception_logger():
    """Lazy import para evitar dependencia circular."""
    from src.observabilidade.registry import get_exception_logger
    return get_exception_logger()


class ClassificadorIntencoes:
    """Classificador de intencoes com cadeia lookup -> RAG -> LLM.

    Orquestra tres estrategias de classificacao em ordem de confianca:
    1. Lookup direto de tokens unicos (exato, confianca 1.0)
    2. RAG com similaridade de embeddings (probabilistico)
    3. LLM puro como fallback definitivo (sempre retorna algo)
    """

    def __init__(
        self,
        llm: LLMProvider,
        embedding_service: EmbeddingService,
        config: RoteadorConfig,
        prompt_template: str,
        intencoes_validas: list[str],
    ) -> None:
        """Inicializa o classificador com todos os componentes.

        Args:
            llm: Provider concreto de LLM para validacao e fallback.
            embedding_service: Servico de embeddings para busca RAG.
            config: Configuracao com thresholds e prioridades.
            prompt_template: Template do prompt de classificacao LLM.
            intencoes_validas: Lista de intents validas para validacao.
        """
        self._lookup = ClassificadorLookup(TOKENS_UNICOS)
        self._rag = ClassificadorRAG(
            embedding_service=embedding_service,
            config=config,
            llm=llm,
            prompt_template=prompt_template,
            intencoes_validas=intencoes_validas,
        )
        self._llm = ClassificadorLLM(
            llm=llm,
            prompt_template=prompt_template,
            intencoes_validas=intencoes_validas,
        )
        self._config = config

    def classificar(self, mensagem: str) -> ResultadoClassificacao:
        """Classifica a intencao da mensagem usando cadeia de estrategias.

        Tenta lookup direto, depois RAG, e por fim LLM como fallback.

        Args:
            mensagem: Texto bruto da mensagem do usuario.

        Returns:
            ResultadoClassificacao com intent, confianca e metadata.

        Example:
            ```python
            resultado = classificador.classificar('oi')
            resultado.intent  # 'saudacao'
            resultado.caminho  # 'lookup'
            ```
        """
        try:
            return self._classificar_interno(mensagem)
        except Exception as e:
            exc_logger = _get_exception_logger()
            if exc_logger:
                exc_logger.registrar(
                    thread_id='',
                    turn_id='',
                    componente='ClassificadorIntencoes.classificar',
                    exception=e,
                    estado={'mensagem': mensagem, 'mensagem_len': len(mensagem)},
                )
            # Fallback definitivo — nunca quebrar
            return ResultadoClassificacao(
                intent='desconhecido',
                confidence=0.0,
                caminho='erro',
                top1_texto='',
                top1_intencao='',
                mensagem_norm='',
                metadados={'erro': str(e)},
            )

    def _classificar_interno(self, mensagem: str) -> ResultadoClassificacao:
        """Logica interna de classificacao — separada para exception handling."""
        mensagem_norm = self._normalizar(mensagem)
        meta: dict = {}

        # Mensagem vazia ou so espacos: LLM fallback
        if not mensagem_norm or not mensagem_norm.strip():
            resultado = self._llm.classificar(mensagem)
            meta['llm_raw'] = resultado.metadados.get('llm_raw', '')
            meta['llm_intent'] = resultado.metadados.get('llm_intent', '')
            return ResultadoClassificacao(
                **{
                    'intent': resultado.intent,
                    'confidence': resultado.confidence,
                    'caminho': resultado.caminho,
                    'top1_texto': resultado.top1_texto,
                    'top1_intencao': resultado.top1_intencao,
                    'mensagem_norm': resultado.mensagem_norm,
                    'metadados': meta,
                }
            )

        # 1. Lookup direto
        resultado = self._lookup.classificar(mensagem_norm)
        if resultado is not None:
            return resultado

        meta['lookup'] = None

        # 2. RAG
        resultado = self._rag.classificar(mensagem_norm)
        if resultado is not None:
            return resultado

        meta['rag'] = None

        # 3. LLM fallback
        resultado = self._llm.classificar(mensagem_norm)
        meta['llm_raw'] = resultado.metadados.get('llm_raw', '')
        meta['llm_intent'] = resultado.metadados.get('llm_intent', '')
        return ResultadoClassificacao(
            **{
                'intent': resultado.intent,
                'confidence': resultado.confidence,
                'caminho': resultado.caminho,
                'top1_texto': resultado.top1_texto,
                'top1_intencao': resultado.top1_intencao,
                'mensagem_norm': resultado.mensagem_norm,
                'metadados': meta,
            }
        )

    def classificar_simples(self, mensagem: str) -> str:
        """API compativel — retorna so a intent.

        Mantem compatibilidade com a API antiga
        classificar_intencao(mensagem) -> str.

        Args:
            mensagem: Texto bruto da mensagem do usuario.

        Returns:
            Nome da intencao classificada.

        Example:
            ```python
            classificador.classificar_simples('quero xbacon')
            'pedir'
            ```
        """
        return self.classificar(mensagem).intent

    def _normalizar(self, mensagem: str) -> str:
        """Normaliza e trunca a mensagem para classificacao.

        Remove pontuacao, normaliza espacos, converte para lowercase
        e trunca para max_chars configurado.

        Args:
            mensagem: Texto bruto da mensagem.

        Returns:
            Texto normalizado e truncado.
        """
        if not mensagem:
            return ''

        texto = mensagem.lower().strip()
        # Remove pontuacao do final de palavras
        texto = re.sub(r'[!?.,]+$', '', texto)
        texto = re.sub(r'([a-z])[!?.,]+([a-z])', r'\1\2', texto)
        # Normaliza multiplos espacos
        texto = re.sub(r'\s+', ' ', texto)
        # Trunca
        return texto[: self._config.max_chars]
