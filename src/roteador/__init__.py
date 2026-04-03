"""Roteador de intenções do Pede AI.

Classifica mensagens do usuário em intenções pré-definidas
utilizando um modelo de linguagem (LLM) via Ollama.

Example:
    ```python
    from src.roteador import classificar_intencao, INTENCOES_VALIDAS

    'pedir' in INTENCOES_VALIDAS
    True
    ```
"""

from src.roteador.classificador_intencoes import INTENCOES_VALIDAS, classificar_intencao


__all__ = ['INTENCOES_VALIDAS', 'classificar_intencao']
