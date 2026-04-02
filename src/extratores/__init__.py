"""
Módulo de extratores do Pede AI.

Fornece ferramentas de processamento de linguagem natural (NLP)
para extrair informações de mensagens do usuário.

Example:
    ```python
    from src.extratores import extrair, extrair_variante

    resultado = extrair('um x-salada sem tomate')
    extrair_variante('duplo', 'lanche_001')
    'duplo'
    ```
"""

from src.extratores.spacy_extrator import extrair, extrair_variante

__all__ = ['extrair', 'extrair_variante']
