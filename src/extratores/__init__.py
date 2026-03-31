"""
Módulo de extratores do Pede AI.

Fornece ferramentas de processamento de linguagem natural (NLP)
para extrair informações de mensagens do usuário.

Example:
    >>> from src.extratores import extrair
    >>> resultado = extrair('um x-salada sem tomate')
"""

from src.extratores.spacy_extrator import extrair

__all__ = ['extrair']
