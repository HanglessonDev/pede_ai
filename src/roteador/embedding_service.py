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

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from src.roteador.modelos import ExemploClassificacao, ExemploSimilar
from src.roteador.protocolos import EmbeddingProvider


def _hash_texto(texto: str) -> str:
    """Calcula hash SHA256 de texto normalizado (strip + lowercase).

    Args:
        texto: Texto original para hash.

    Returns:
        Hex digest SHA256 do texto normalizado.

    Example:
        ```python
        >>> _hash_texto('  Quero Um Lanche  ')
        'abc123...'  # mesmo hash para 'quero um lanche'
        ```
    """
    return hashlib.sha256(texto.strip().lower().encode()).hexdigest()


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
        self._embeddings_dict: dict[str, list[float]] = {}
        self._embeddings: list[list[float]] = []
        self._exemplo_indices: list[int] = []
        self._carregar()

    def _carregar(self) -> None:
        """Carrega exemplos e embeddings do disco.

        Monta ``_embeddings`` como lista alinhada aos exemplos via hash.
        Quando nao ha exemplos mas o cache e legado (lista pura), usa a lista
        diretamente como fallback.
        """
        self._exemplos = self._carregar_exemplos()
        self._embeddings_dict, raw_fallback = self._carregar_cache()

        if raw_fallback and not self._exemplos:
            # Cache legado sem exemplos: usa lista diretamente
            self._embeddings = raw_fallback
            self._exemplo_indices = list(range(len(raw_fallback)))
        else:
            self._embeddings, self._exemplo_indices = self._montar_lista_alinhada()

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

    def _carregar_cache(
        self,
    ) -> tuple[dict[str, list[float]], list[list[float]] | None]:
        """Le embeddings do cache JSON.

        Suporta dois formatos:
        - Formato 1 (antigo): lista posicional ``[[emb1], [emb2], ...]``
          ou dict ``{"format": 1, "embeddings": [...]}``. Migrado para formato 2.
        - Formato 2 (novo): ``{"format": 2, "embeddings": {"hash1": [emb], ...}}``.

        Returns:
            Tupla (dict_hash_embedding, raw_fallback).
            ``raw_fallback`` e a lista crua quando o cache e legado e nao ha
            exemplos para associar hashes.
        """
        if not self._cache_path.exists():
            return {}, None

        with open(self._cache_path, encoding='utf-8') as f:
            dados: Any = json.load(f)

        # Formato 2: dict com hashes
        if isinstance(dados, dict) and dados.get('format') == 2:
            return dict(dados['embeddings']), None

        # Formato 1: migrar
        if isinstance(dados, dict) and dados.get('format') == 1:
            embeddings_lista: list[list[float]] = dados['embeddings']
        elif isinstance(dados, list):
            embeddings_lista = dados
        else:
            return {}, None

        # Se nao ha exemplos, retorna lista crua como fallback
        if not self._exemplos:
            return {}, embeddings_lista

        # Migrar: associar posicoes aos hashes dos exemplos
        embeddings_dict: dict[str, list[float]] = {}
        for i, emb in enumerate(embeddings_lista):
            if i < len(self._exemplos):
                h = _hash_texto(self._exemplos[i].texto)
                embeddings_dict[h] = emb

        # Salvar no formato novo
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._cache_path, 'w', encoding='utf-8') as f:
            json.dump({'format': 2, 'embeddings': embeddings_dict}, f)

        return embeddings_dict, None

    def _montar_lista_alinhada(self) -> tuple[list[list[float]], list[int]]:
        """Monta lista de embeddings alinhada aos exemplos via hash.

        Para cada exemplo, busca o embedding no dict pelo hash.
        Exemplos sem embedding no cache sao pulados.

        Returns:
            Tupla (lista_embeddings, indices_exemplos) onde:
            - lista_embeddings: lista contigua de embeddings para numpy
            - indices_exemplos: mapeia posicao em lista_embeddings -> indice em _exemplos
        """
        embeddings: list[list[float]] = []
        indices: list[int] = []
        for i, exemplo in enumerate(self._exemplos):
            h = _hash_texto(exemplo.texto)
            if h in self._embeddings_dict:
                embeddings.append(self._embeddings_dict[h])
                indices.append(i)
        return embeddings, indices

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
                texto=self._exemplos[self._exemplo_indices[idx]].texto,
                intencao=self._exemplos[self._exemplo_indices[idx]].intencao,
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

        Gera embeddings apenas para exemplos cujos hashes nao estao no cache,
        e salva no formato 2: ``{"format": 2, "embeddings": {hash: emb, ...}}``.
        """
        # Descobrir quais exemplos nao tem embedding
        faltantes: list[ExemploClassificacao] = []
        for ex in self._exemplos:
            h = _hash_texto(ex.texto)
            if h not in self._embeddings_dict:
                faltantes.append(ex)

        if not faltantes:
            return

        # Gera embeddings faltantes
        textos_faltantes = [ex.texto for ex in faltantes]
        novos = self._provider.embed_batch(textos_faltantes)

        # Adiciona ao dict
        for ex, emb in zip(faltantes, novos, strict=True):
            h = _hash_texto(ex.texto)
            self._embeddings_dict[h] = emb

        # Re-monta lista alinhada
        self._embeddings, self._exemplo_indices = self._montar_lista_alinhada()

        # Salva cache no formato 2
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._cache_path, 'w', encoding='utf-8') as f:
            json.dump({'format': 2, 'embeddings': self._embeddings_dict}, f)

    @property
    def exemplos(self) -> list[ExemploClassificacao]:
        """Retorna lista de exemplos carregados."""
        return list(self._exemplos)

    @property
    def tem_embeddings(self) -> bool:
        """Retorna True se ha embeddings carregados."""
        return len(self._embeddings) > 0
