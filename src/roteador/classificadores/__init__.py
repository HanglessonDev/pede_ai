"""Classificadores de intencao.

Re-exporta todos os classificadores disponiveis.

Example:
    ```python
    from src.roteador.classificadores import (
        ClassificadorBase,
        ClassificadorLLM,
        ClassificadorLookup,
        ClassificadorRAG,
    )
    ```
"""

from src.roteador.classificadores.base import ClassificadorBase
from src.roteador.classificadores.llm import ClassificadorLLM
from src.roteador.classificadores.lookup import ClassificadorLookup, TOKENS_UNICOS
from src.roteador.classificadores.rag import ClassificadorRAG

__all__ = [
    'TOKENS_UNICOS',
    'ClassificadorBase',
    'ClassificadorLLM',
    'ClassificadorLookup',
    'ClassificadorRAG',
]
