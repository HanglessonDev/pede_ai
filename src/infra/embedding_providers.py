"""Providers concretos de Embedding.

Implementacoes do protocolo EmbeddingProvider para diferentes backends.

Example:
    ```python
    from src.infra.embedding_providers import SentenceTransformerEmbeddings

    emb = SentenceTransformerEmbeddings()
    emb.embed('quero um lanche')
    ```
"""

from __future__ import annotations


class SentenceTransformerEmbeddings:
    """Embeddings via sentence-transformers — local, sem Ollama.

    Usa o modelo all-MiniLM-L6-v2 por padrao (~80MB).
    O modelo e baixado automaticamente na primeira execucao.
    """

    def __init__(
        self,
        model_name: str = 'sentence-transformers/all-MiniLM-L6-v2',
    ) -> None:
        """Inicializa o provider de embeddings.

        Args:
            model_name: Nome do modelo sentence-transformers.
        """
        from sentence_transformers import SentenceTransformer  # noqa: PLC0415 — lazy loading

        self._model = SentenceTransformer(model_name)

    def embed(self, texto: str) -> list[float]:
        """Gera embedding para um texto.

        Args:
            texto: Texto para gerar embedding.

        Returns:
            Lista de floats representando o embedding.
        """
        return self._model.encode(texto).tolist()

    def embed_batch(self, textos: list[str]) -> list[list[float]]:
        """Gera embeddings para multiplos textos.

        Args:
            textos: Lista de textos para gerar embeddings.

        Returns:
            Lista de embeddings (lista de listas de floats).
        """
        return self._model.encode(textos).tolist()
