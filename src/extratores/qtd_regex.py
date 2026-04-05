"""Regex posicional para extracao de quantidade."""

from __future__ import annotations

import re

QTD_PATTERN = re.compile(
    r'^(\d+|um|uma|dois|duas|tr[eê]s|quatro|cinco|meio|meia)\s+',
    re.IGNORECASE,
)

_MAPA_NUMEROS: dict[str, float] = {
    'um': 1,
    'uma': 1,
    'dois': 2,
    'duas': 2,
    'tres': 3,
    'três': 3,
    'quatro': 4,
    'cinco': 5,
    'meio': 0.5,
    'meia': 0.5,
}


def extrair_qtd_regex(segmento: str) -> tuple[int | float | None, str]:
    """Extrai quantidade do inicio do segmento via regex.

    Args:
        segmento: Texto do segmento a processar.

    Returns:
        Tupla (quantidade, texto_sem_qtd).
        Quantidade é None se nenhum padrao for encontrado.
    """
    match = QTD_PATTERN.match(segmento)
    if not match:
        return None, segmento

    qtd_texto = match.group(1)
    resto = segmento[match.end() :]

    if qtd_texto.isdigit():
        return int(qtd_texto), resto

    return _MAPA_NUMEROS.get(qtd_texto.lower()), resto
