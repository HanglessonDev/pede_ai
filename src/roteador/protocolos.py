"""Protocolos (interfaces) para providers de LLM e Embedding.

Define contratos que qualquer implementacao concreta deve seguir.
Usa typing.Protocol para duck typing — nao requer heranca.

Example:
    ```python
    from src.roteador.protocolos import LLMProvider


    class MeuProvider:
        def completar(self, prompt: str, max_tokens: int = 10) -> str:
            return 'minha resposta'


    # MeuProvider e compativel com LLMProvider automaticamente
    def usar(provider: LLMProvider) -> str:
        return provider.completar('teste')
    ```
"""

from __future__ import annotations

from typing import Protocol


class LLMProvider(Protocol):
    """Interface para qualquer provedor de LLM.

    Qualquer classe com o metodo 'completar' e compativel,
    independente de heranca (duck typing via Protocol).
    """

    def completar(self, prompt: str, max_tokens: int = 10) -> str:
        """Envia prompt ao LLM e retorna resposta texto.

        Args:
            prompt: Texto do prompt para o LLM.
            max_tokens: Maximo de tokens na resposta.

        Returns:
            Texto da resposta do LLM.
        """
        ...


class EmbeddingProvider(Protocol):
    """Interface para qualquer servico de embeddings.

    Qualquer classe com os metodos 'embed' e 'embed_batch'
    e compativel, independente de heranca.
    """

    def embed(self, texto: str) -> list[float]:
        """Gera embedding para um texto.

        Args:
            texto: Texto para gerar embedding.

        Returns:
            Lista de floats representando o embedding.
        """
        ...

    def embed_batch(self, textos: list[str]) -> list[list[float]]:
        """Gera embeddings para multiplos textos.

        Args:
            textos: Lista de textos para gerar embeddings.

        Returns:
            Lista de embeddings (lista de listas de floats).
        """
        ...
