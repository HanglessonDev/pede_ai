"""Classificador por similaridade de embeddings (RAG).

Busca exemplos similares via embedding, vota com prioridade,
e valida com LLM quando confianca e media.

Example:
    ```python
    from src.roteador.classificadores.rag import ClassificadorRAG

    rag = ClassificadorRAG(embedding_service, config, llm)
    resultado = rag.classificar('quero um lanche')
    ```
"""

from __future__ import annotations

from src.roteador.classificadores.base import ClassificadorBase
from src.roteador.embedding_service import EmbeddingService
from src.roteador.modelos import ResultadoClassificacao
from src.roteador.protocolos import LLMProvider
from src.config.roteador_config import RoteadorConfig
from src.roteador.voting import votar_com_prioridade


class ClassificadorRAG(ClassificadorBase):
    """Classificacao por similaridade de embeddings (RAG).

    Fluxo:
    1. Busca top-K exemplos similares via EmbeddingService.
    2. Se nenhum similar >= min_similarity: retorna None (proximo classificador).
    3. Se confidence >= rag_forte_threshold: vota e retorna direto.
    4. Se confidence >= rag_fraco_threshold: valida com LLM e retorna.
    5. Se confidence < rag_fraco_threshold: retorna None (LLM fallback assume).
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        config: RoteadorConfig,
        llm: LLMProvider,
        prompt_template: str,
        intencoes_validas: list[str],
    ) -> None:
        """Inicializa o classificador RAG.

        Args:
            embedding_service: Servico de embeddings para busca.
            config: Configuracao do roteador com thresholds.
            llm: Provider LLM para validacao.
            prompt_template: Template do prompt de classificacao.
            intencoes_validas: Lista de intents validas.
        """
        self._embedding_service = embedding_service
        self._config = config
        self._llm = llm
        self._prompt_template = prompt_template
        self._intencoes_validas = intencoes_validas
        self._votar = votar_com_prioridade

    def classificar(self, mensagem: str) -> ResultadoClassificacao | None:
        """Classifica via RAG com similaridade de embeddings.

        Args:
            mensagem: Texto normalizado do usuario.

        Returns:
            ResultadoClassificacao se classificou, None se nao ha confianca.
        """
        if not self._embedding_service.tem_embeddings:
            return None

        similares = self._embedding_service.buscar_similares(
            mensagem,
            top_k=self._config.top_k,
            min_similarity=self._config.min_similarity,
        )

        if not similares:
            return None

        confidence = similares[0].similaridade
        top1_texto = similares[0].texto
        top1_intencao = similares[0].intencao

        # RAG forte: confianca acima do threshold, usa direto
        if confidence >= self._config.rag_forte_threshold:
            intent = self._votar(similares, self._config.alta_prioridade)
            return ResultadoClassificacao(
                intent=intent,
                confidence=confidence,
                caminho='rag_forte',
                top1_texto=top1_texto,
                top1_intencao=top1_intencao,
                mensagem_norm=mensagem,
            )

        # RAG fraco: abaixo do threshold minimo, delega para LLM fallback
        if confidence < self._config.rag_fraco_threshold:
            return None

        # RAG medio: valida com LLM
        intent = self._validar_com_llm(mensagem, similares)

        return ResultadoClassificacao(
            intent=intent,
            confidence=confidence,
            caminho='llm_rag',
            top1_texto=top1_texto,
            top1_intencao=top1_intencao,
            mensagem_norm=mensagem,
        )

    def _validar_com_llm(self, mensagem: str, similares: list) -> str:
        """Valida classificacao RAG com LLM.

        Args:
            mensagem: Texto da mensagem.
            similares: Lista de exemplos similares.

        Returns:
            Intencao validada pelo LLM.
        """
        intencao_dominante = votar_com_prioridade(
            similares, self._config.alta_prioridade
        )

        exemplos_formatados = '\n'.join(
            f'"{s.texto}" -> {s.intencao}' for s in similares[:5]
        )

        prompt = (
            f'Classifique a intencao do usuario em UMA palavra.\n'
            f'Responda APENAS o NOME DA INTENCAO exatamente como listado abaixo.\n\n'
            f'INTENCOES VALIDAS: {", ".join(self._intencoes_validas)}\n\n'
            f'Analise os exemplos abaixo e classifique a nova mensagem.\n'
            f'Cada exemplo mostra a intencao correta para aquela frase.\n\n'
            f'EXEMPLOS:\n{exemplos_formatados}\n\n'
            f'Agora classifique esta mensagem:\n'
            f'"{mensagem}" ->\n'
        )

        resposta = self._llm.completar(prompt, max_tokens=10)
        intencao = resposta.strip().lower().split()[0] if resposta.strip() else ''

        if intencao not in self._intencoes_validas:
            # Fallback: usa votacao RAG se LLM falhar
            return intencao_dominante

        return intencao
