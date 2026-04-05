"""Normalizacao de texto para extracao.

Duas funcoes nomeadas com semantica clara:
- normalizar_para_busca: para EntityRuler (remove pontuacao, troca hifen)
- normalizar_para_fuzzy: para fuzzy matching (so unicode + lowercase)

Example:
    ```python
    from src.extratores.normalizador import normalizar_para_busca, normalizar_para_fuzzy

    normalizar_para_busca('X-Tudo!')
    'xtudo'
    normalizar_para_fuzzy('Hambúrguer!')
    'hamburguer!'
    ```
"""

from __future__ import annotations

import re
import unicodedata


_PUNCTUATION_RE = re.compile(r'[^\w\s]')
_WHITESPACE_RE = re.compile(r'\s+')


def normalizar_para_busca(texto: str) -> str:
    """Normaliza para busca no EntityRuler.

    Aplica lowercase, normalizacao Unicode (remove acentos),
    remove pontuacao e normaliza espacos. Troca hifen por espaco.

    Args:
        texto: Texto original.

    Returns:
        Texto normalizado em minusculas sem acentos ou pontuacao.

    Example:
        ```python
        normalizar_para_busca('X-Tudo!')
        'xtudo'
        ```
    """
    texto = texto.lower()
    texto = unicodedata.normalize('NFKD', texto)
    texto = texto.encode('ascii', 'ignore').decode('utf-8')
    texto = _PUNCTUATION_RE.sub('', texto)
    texto = texto.replace('-', ' ')
    texto = _WHITESPACE_RE.sub(' ', texto).strip()
    return texto


def normalizar_para_fuzzy(texto: str) -> str:
    """Normaliza para fuzzy matching.

    Aplica lowercase e normalizacao Unicode (remove acentos).
    Preserva pontuacao interna e espacos.

    Args:
        texto: Texto original.

    Returns:
        Texto normalizado em minusculas sem acentos.

    Example:
        ```python
        normalizar_para_fuzzy('Hambúrguer!')
        'hamburguer!'
        ```
    """
    texto = texto.lower()
    texto = unicodedata.normalize('NFKD', texto)
    texto = texto.encode('ascii', 'ignore').decode('utf-8')
    return texto.strip()
