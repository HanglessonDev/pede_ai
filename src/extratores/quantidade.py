"""Resolucao unificada de quantidade.

Substitui: _resolver_quantidade, _extrair_qtd_do_doc,
           logica inline do fuzzy fallback, e qtd_regex.py.
"""

from __future__ import annotations

import re

from src.extratores.config import ExtratorConfig


def resolver_quantidade(texto: str, config: ExtratorConfig) -> int | float | None:
    """Resolve 'quatro' -> 4, 'meio' -> 0.5, '2' -> 2, 'xyz' -> None.

    Ordem de tentativa:
    1. Digitos puros (isdigit)
    2. Numeros fracionarios do config (meio, meia, etc.)
    3. Numeros escritos do config (um, dois, tres, etc.)
    4. None (desconhecido)

    Args:
        texto: Palavra isolada que pode ser quantidade.
        config: ExtratorConfig com mapas de numeros.

    Returns:
        Inteiro, float ou None se nao reconhecer.
    """
    texto = texto.strip().lower()

    # 1. Digito puro
    if texto.isdigit():
        return int(texto)

    # 2. Fracionarios
    if texto in config.numeros_fracionarios:
        return config.numeros_fracionarios[texto]

    # 3. Numeros escritos
    if texto in config.numeros_escritos:
        return config.numeros_escritos[texto]

    # 4. Desconhecido
    return None


def extrair_quantidade_do_texto(
    texto: str,
    config: ExtratorConfig,
) -> tuple[int | float | None, str]:
    """Extrai quantidade do inicio do texto via regex.

    Constroi regex dinamicamente a partir do config:
    - Digitos: \\d+
    - Fracionarios: meio, meia, ...
    - Escritos: um, dois, tres, ...
    - Case insensitive

    Args:
        texto: Texto completo (ex: 'quatro sucos').
        config: ExtratorConfig com mapas de numeros.

    Returns:
        Tupla (quantidade, texto_sem_qtd).
        Quantidade e None se nenhum padrao for encontrado.
    """
    # Construir alternativas da regex a partir do config
    alternativas: list[str] = [r'\d+']

    # Fracionarios (ex: meio, meia)
    alternativas.extend(re.escape(k) for k in config.numeros_fracionarios)

    # Numeros escritos (ex: um, dois, tres)
    alternativas.extend(re.escape(k) for k in config.numeros_escritos)

    # Pattern: (alternativas) no inicio seguido de espaco
    pattern = r'^(?:' + '|'.join(alternativas) + r')\s+'
    regex = re.compile(pattern, re.IGNORECASE)

    match = regex.match(texto)
    if not match:
        return None, texto

    qtd_texto = match.group(0).strip()
    resto = texto[match.end() :]

    # Resolver o valor extraido
    qtd = resolver_quantidade(qtd_texto, config)
    return qtd, resto
