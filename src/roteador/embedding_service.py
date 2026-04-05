"""Servico de embeddings com cache e busca por similaridade.

Gerencia exemplos, embeddings cacheados e busca por similaridade cosseno via numpy.

Example:
    ```python
    from src.infra.embedding_providers import SentenceTransformerEmbeddings
    from src.roteador.embedding_service import EmbeddingService

    provider = SentenceTransformerEmbeddings()
    service = EmbeddingService(provider, exemplos_path, cache_path)
    service.buscar_similares('quero um lanche')
    ```
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from src.roteador.modelos import ExemploClassificacao, ExemploSimilar
from src.roteador.protocolos import EmbeddingProvider


class EmbeddingService:
    """Gerencia exemplos, embeddings e busca por similaridade.

    Carrega exemplos de JSON e embeddings do cache na inicializacao.
    Gera embeddings sob demanda via provider injetado.
    """

    def __init__(
        self,
        provider: EmbeddingProvider,
        exemplos_path: Path,
        cache_path: Path,
    ) -> None:
        """Inicializa o servico de embeddings.

        Args:
            provider: Provider concreto de embeddings.
            exemplos_path: Caminho do arquivo JSON de exemplos.
            cache_path: Caminho do arquivo JSON de embeddings cacheados.
        """
        self._provider = provider
        self._exemplos_path = exemplos_path
        self._cache_path = cache_path
        self._exemplos: list[ExemploClassificacao] = []
        self._embeddings: list[list[float]] = []
        self._carregar()

    def _carregar(self) -> None:
        """Carrega exemplos e embeddings do disco."""
        self._exemplos = self._carregar_exemplos()
        self._embeddings = self._carregar_cache()

    def _carregar_exemplos(self) -> list[ExemploClassificacao]:
        """Le exemplos do JSON.

        Returns:
            Lista de ExemploClassificacao.
        """
        if not self._exemplos_path.exists():
            return []

        with open(self._exemplos_path, encoding='utf-8') as f:
            dados: list[dict[str, Any]] = json.load(f)

        return [
            ExemploClassificacao(texto=d['texto'], intencao=d['intencao'])
            for d in dados
        ]

    def _carregar_cache(self) -> list[list[float]]:
        """Le embeddings do cache JSON.

        Returns:
            Lista de embeddings (listas de floats).
        """
        if not self._cache_path.exists():
            return []

        with open(self._cache_path, encoding='utf-8') as f:
            dados: list[list[float]] = json.load(f)

        return dados

    def buscar_similares(
        self,
        mensagem: str,
        top_k: int = 5,
        min_similarity: float = 0.55,
    ) -> list[ExemploSimilar]:
        """Busca top-k exemplos mais similares a mensagem.

        Args:
            mensagem: Texto da mensagem do usuario.
            top_k: Numero de resultados a retornar.
            min_similarity: Similaridade minima para incluir exemplo.

        Returns:
            Lista de ExemploSimilar ordenada por similaridade decrescente.
        """
        if not self._exemplos or not self._embeddings:
            return []

        query_emb = np.array(self._provider.embed(mensagem))
        embeddings_arr = np.array(self._embeddings)

        dot = np.dot(embeddings_arr, query_emb)
        norms = np.linalg.norm(embeddings_arr, axis=1) * np.linalg.norm(query_emb)
        similarities = np.divide(dot, norms, out=np.zeros_like(dot), where=norms != 0)

        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = [
            ExemploSimilar(
                texto=self._exemplos[idx].texto,
                intencao=self._exemplos[idx].intencao,
                similaridade=float(similarities[idx]),
            )
            for idx in top_indices
        ]

        return [r for r in results if r.similaridade >= min_similarity]

    def gerar_embedding(self, texto: str) -> list[float]:
        """Gera embedding para um texto via provider.

        Args:
            texto: Texto para gerar embedding.

        Returns:
            Lista de floats representando o embedding.
        """
        return self._provider.embed(texto)

    def atualizar_cache(self) -> None:
        """Regenera embeddings faltando e salva cache.

        Gera embeddings para exemplos que ainda nao tem no cache
        e salva o arquivo atualizado.
        """
        existentes = len(self._embeddings)
        total = len(self._exemplos)

        if existentes >= total:
            return

        # Gera embeddings faltando
        textos_faltando = [ex.texto for ex in self._exemplos[existentes:]]
        novos = self._provider.embed_batch(textos_faltando)

        self._embeddings.extend(novos)

        # Salva cache
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._cache_path, 'w', encoding='utf-8') as f:
            json.dump(self._embeddings, f)

    @property
    def exemplos(self) -> list[ExemploClassificacao]:
        """Retorna lista de exemplos carregados."""
        return list(self._exemplos)

    @property
    def tem_embeddings(self) -> bool:
        """Retorna True se ha embeddings carregados."""
        return len(self._embeddings) > 0
