"""Fuzzy matching para fallback do extrator spaCy.

Funcoes puras para correcao de typos em nomes de itens e variantes
do cardapio usando rapidfuzz.

Example:
    ```python
    from src.extratores.fuzzy_extrator import fuzzy_match_item

    aliases = {'hamburguer': 'lanche_001', 'coca': 'bebida_001'}
    fuzzy_match_item('amburguer', aliases)
    ('hamburguer', 94.7, 'lanche_001')
    ```
"""

import re

from rapidfuzz import fuzz, process

from src.extratores.config import get_extrator_config
from src.extratores.normalizador import normalizar_para_fuzzy


# ── Matching de variante numerica ──────────────────────────────────────────


def match_variante_numerica(typo: str, variantes: list[str]) -> str | None:
    """Resolve typos em variantes numericas do tipo NNNml.

    Usa substring matching: se o numero do typo e substring do numero
    da variante, e um match. Ex: '50' em '500' → match.

    Args:
        typo: Texto digitado pelo usuario.
        variantes: Lista de variantes validas do cardapio.

    Returns:
        Variante matchada, ou None se ambiguo ou sem match.

    Example:
        ```python
        match_variante_numerica('50ml', ['300ml', '500ml'])
        '500ml'
        match_variante_numerica('50ml', ['350ml', '500ml'])
        None  # ambiguo: 50 esta em ambos
        ```
    """
    typo_n = normalizar_para_fuzzy(typo)
    match_ml = re.match(r'^(\d+)ml$', typo_n)
    if not match_ml:
        return None
    typo_num = match_ml.group(1)
    candidatos = []
    for var in variantes:
        var_n = normalizar_para_fuzzy(var)
        var_match = re.match(r'^(\d+)ml$', var_n)
        if var_match and typo_num in var_match.group(1):
            candidatos.append(var)
    return candidatos[0] if len(candidatos) == 1 else None


# ── Pre-processamento ───────────────────────────────────────────────────────


def extrair_tokens_significativos(texto: str) -> list[str]:
    """Remove stop words e retorna tokens relevantes.

    Args:
        texto: Texto da mensagem do usuario.

    Returns:
        Lista de tokens significativos.

    Example:
        ```python
        extrair_tokens_significativos('quero um hamburguer sem cebola')
        ['hamburguer', 'sem', 'cebola']
        ```
    """
    texto_n = normalizar_para_fuzzy(texto)
    texto_n = re.sub(r'[^\w\s]', ' ', texto_n)
    tokens = texto_n.split()
    config = get_extrator_config()
    return [t for t in tokens if t not in config.stop_words and len(t) > 1]


# ── Fuzzy match de item ────────────────────────────────────────────────────


def fuzzy_match_item(
    texto: str,
    alias_para_id: dict[str, str],
    cutoff: int | None = None,
) -> tuple[str | None, float, str | None]:
    """Fuzzy match de texto contra aliases do cardapio.

    Args:
        texto: Texto digitado pelo usuario.
        alias_para_id: Mapeamento alias → item_id.
        cutoff: Score minimo (0-100). Usa config se None.

    Returns:
        Tupla (alias_match, score, item_id) ou (None, 0, None).
    """
    config = get_extrator_config()
    cutoff = cutoff if cutoff is not None else config.fuzzy_item_cutoff

    tokens = extrair_tokens_significativos(texto)
    if not tokens:
        return None, 0, None

    candidatos = list(alias_para_id.keys())
    melhor_alias: str | None = None
    melhor_score = 0.0

    for token in [*tokens, normalizar_para_fuzzy(texto)]:
        resultado = process.extractOne(
            token, candidatos, scorer=fuzz.ratio, score_cutoff=cutoff
        )
        if resultado and resultado[1] > melhor_score:
            melhor_alias = resultado[0]
            melhor_score = resultado[1]

    if melhor_alias:
        return melhor_alias, melhor_score, alias_para_id.get(melhor_alias)
    return None, 0, None


# ── Fuzzy match de variante ────────────────────────────────────────────────


def fuzzy_match_variante(
    texto: str,
    variantes: list[str],
    cutoff: int | None = None,
) -> tuple[str | None, float]:
    """Fuzzy match de texto contra variantes validas.

    Usa match_variante_numerica primeiro para variantes do tipo NNNml.
    Depois tenta fuzzy normal com deteccao de ambiguidade.

    Args:
        texto: Texto digitado pelo usuario.
        variantes: Lista de variantes validas do cardapio.
        cutoff: Score minimo (0-100). Usa config se None.

    Returns:
        Tupla (variante_match, score) ou (None, 0).
    """
    if not texto or not texto.strip():
        return None, 0

    config = get_extrator_config()
    cutoff = cutoff if cutoff is not None else config.fuzzy_variante_cutoff

    texto_n = normalizar_para_fuzzy(texto)

    # Tentar matching numerico primeiro
    resultado_num = match_variante_numerica(texto_n, variantes)
    if resultado_num:
        return resultado_num, 95.0

    # Fuzzy normal
    resultado = process.extractOne(
        texto_n, variantes, scorer=fuzz.ratio, score_cutoff=cutoff
    )
    if not resultado:
        return None, 0

    # Verificar ambiguidade: se top-2 estao dentro de AMBIGUIDADE_LIMITE pontos
    todos_matches = process.extract(
        texto_n, variantes, scorer=fuzz.ratio, score_cutoff=cutoff, limit=2
    )
    if len(todos_matches) >= 2:
        _, score1, _ = resultado
        _, score2, _ = todos_matches[1]
        if score1 - score2 < config.ambiguidade_limite:
            return None, 0  # ambiguo, melhor nao arriscar

    return resultado[0], resultado[1]


__all__ = [
    'extrair_tokens_significativos',
    'fuzzy_match_item',
    'fuzzy_match_variante',
    'match_variante_numerica',
    'normalizar',  # compatibilidade — alias para normalizar_para_fuzzy
]

# Compatibilidade com codigo legado que importa normalizar() deste modulo
from src.extratores.normalizador import normalizar_para_fuzzy as normalizar
