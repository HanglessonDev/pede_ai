"""Providers concretos de LLM.

Implementacoes do protocolo LLMProvider para diferentes backends.

Example:
    ```python
    from src.infra.llm_providers import GroqProvider

    llm = GroqProvider(api_key='sua-chave')
    llm.completar('Classifique: "quero um lanche"')
    ```
"""

from __future__ import annotations

import os


class GroqProvider:
    """LLM via Groq API — cloud, rapido, producao.

    Usa o modelo Llama 3.1 8B Instant por padrao.
    Requer GROQ_API_KEY no ambiente ou passada explicitamente.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = 'llama-3.1-8b-instant',
    ) -> None:
        """Inicializa o provider Groq.

        Args:
            api_key: Chave da API Groq. Se None, le de GROQ_API_KEY.
            model: Nome do modelo a usar.
        """
        from groq import Groq  # noqa: PLC0415 — lazy loading

        self._client = Groq(api_key=api_key or os.environ['GROQ_API_KEY'])
        self._model = model

    def completar(self, prompt: str, max_tokens: int = 10) -> str:
        """Envia prompt ao Groq e retorna resposta texto.

        Args:
            prompt: Texto do prompt para o LLM.
            max_tokens: Maximo de tokens na resposta.

        Returns:
            Texto da resposta do LLM.
        """
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ''


class OllamaProvider:
    """LLM via Ollama local — dev/testing, sem API key.

    Usa qwen3.5:2b por padrao. Requer Ollama rodando localmente.
    """

    def __init__(
        self,
        model: str = 'qwen3.5:2b',
        num_predict: int = 10,
    ) -> None:
        """Inicializa o provider Ollama.

        Args:
            model: Nome do modelo Ollama a usar.
            num_predict: Maximo de tokens na resposta.
        """
        from langchain_ollama import OllamaLLM  # noqa: PLC0415 — lazy loading

        self._model = model
        self._llm = OllamaLLM(
            model=model,
            temperature=0,
            reasoning=False,
            num_ctx=512,
            num_predict=num_predict,
        )

    def completar(self, prompt: str, max_tokens: int = 10) -> str:
        """Envia prompt ao Ollama e retorna resposta texto.

        Args:
            prompt: Texto do prompt para o LLM.
            max_tokens: Ignorado (Ollama usa num_predict do construtor).

        Returns:
            Texto da resposta do LLM.
        """
        return self._llm.invoke(prompt)
