"""Roteador de intencoes do Pede AI.

Classifica mensagens do usuario em intencoes pre-definidas
utilizando cadeia de estrategias: lookup direto, RAG com embeddings
e LLM como fallback.

Example:
    ```python
    from src.roteador import ClassificadorIntencoes, ResultadoClassificacao

    # classificador = ClassificadorIntencoes(llm, embedding_service, config, ...)
    # resultado = classificador.classificar('quero um xbacon')
    # resultado.intent  # 'pedir'
    ```
"""

from src.roteador.modelos import ResultadoClassificacao
from src.roteador.service import ClassificadorIntencoes

__all__ = ['ClassificadorIntencoes', 'ResultadoClassificacao']
