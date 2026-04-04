"""
Módulo de extratores do Pede AI.

Fornece ferramentas de processamento de linguagem natural (NLP)
para extrair informações de mensagens do usuário.

Example:
    ```python
    from src.extratores import extrair, extrair_variante, extrair_item_carrinho

    resultado = extrair('um x-salada sem tomate')
    extrair_variante('duplo', 'lanche_001')
    'duplo'
    ```
"""

from src.extratores.fuzzy_extrator import (
    extrair_tokens_significativos,
    fuzzy_match_item,
    fuzzy_match_variante,
    match_variante_numerica,
)
from src.extratores.spacy_extrator import (
    extrair,
    extrair_item_carrinho,
    extrair_itens_troca,
    extrair_variante,
)

__all__ = [
    'extrair',
    'extrair_item_carrinho',
    'extrair_itens_troca',
    'extrair_tokens_significativos',
    'extrair_variante',
    'fuzzy_match_item',
    'fuzzy_match_variante',
    'match_variante_numerica',
]
