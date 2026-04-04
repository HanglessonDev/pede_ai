"""Fuzzy matching para fallback do extrator spaCy.

Funções puras para correção de typos em nomes de itens e variantes
do cardápio usando rapidfuzz.

Example:
    ```python
    from src.extratores.fuzzy_extrator import fuzzy_match_item

    aliases = {'hamburguer': 'lanche_001', 'coca': 'bebida_001'}
    fuzzy_match_item('amburguer', aliases)
    ('hamburguer', 94.7, 'lanche_001')
    ```
"""

import re
import unicodedata

from rapidfuzz import fuzz, process


# ── Constantes ──────────────────────────────────────────────────────────────

STOP_WORDS = {
    'quero',
    'quer',
    'me',
    'da',
    'de',
    'do',
    'um',
    'uma',
    'uns',
    'umas',
    'o',
    'a',
    'os',
    'as',
    'e',
    'ou',
    'pra',
    'para',
    'por',
    'pelo',
    'pela',
    'no',
    'na',
    'nos',
    'nas',
    'muda',
    'mudar',
    'troca',
    'trocar',
    'coloca',
    'bota',
    'veja',
    'ver',
    'mostra',
    'mostrar',
    'pode',
    'favor',
    'por favor',
    'aqui',
    'ali',
    'isso',
    'isto',
    'esse',
    'essa',
}
"""Stop words a remover durante pré-processamento."""

FUZZY_ITEM_CUTOFF = 75
"""Score mínimo para fuzzy match de itens (0-100)."""

FUZZY_VARIANTE_CUTOFF = 75
"""Score mínimo para fuzzy match de variantes (0-100)."""

AMBIGUIDADE_LIMITE = 5
"""Diferença máxima entre top-2 scores para considerar ambíguo."""


# ── Normalização ────────────────────────────────────────────────────────────


def normalizar(texto: str) -> str:
    """Normaliza texto para comparação (lowercase, sem acentos, sem pontuação).

    Args:
        texto: Texto original.

    Returns:
        Texto normalizado.

    Example:
        ```python
        normalizar('Hambúrguer!')
        'hamburguer'
        ```
    """
    texto = texto.lower()
    texto = unicodedata.normalize('NFKD', texto)
    texto = texto.encode('ascii', 'ignore').decode('utf-8')
    return texto.strip()


# ── Pré-processamento ───────────────────────────────────────────────────────


def extrair_tokens_significativos(texto: str) -> list[str]:
    """Remove stop words e retorna tokens relevantes.

    Args:
        texto: Texto da mensagem do usuário.

    Returns:
        Lista de tokens significativos.

    Example:
        ```python
        extrair_tokens_significativos('quero um hamburguer sem cebola')
        ['hamburguer', 'sem', 'cebola']
        ```
    """
    texto_n = normalizar(texto)
    texto_n = re.sub(r'[^\w\s]', ' ', texto_n)
    tokens = texto_n.split()
    return [t for t in tokens if t not in STOP_WORDS and len(t) > 1]


# ── Matching de variante numérica ──────────────────────────────────────────


def match_variante_numerica(typo: str, variantes: list[str]) -> str | None:
    """Resolve typos em variantes numéricas do tipo NNNml.

    Usa substring matching: se o número do typo é substring do número
    da variante, é um match. Ex: '50' em '500' → match.

    Args:
        typo: Texto digitado pelo usuário.
        variantes: Lista de variantes válidas do cardápio.

    Returns:
        Variante matchada, ou None se ambíguo ou sem match.

    Example:
        ```python
        match_variante_numerica('50ml', ['300ml', '500ml'])
        '500ml'
        match_variante_numerica('50ml', ['350ml', '500ml'])
        None  # ambíguo: 50 está em ambos
        ```
    """
    typo_n = normalizar(typo)
    match_ml = re.match(r'^(\d+)ml$', typo_n)
    if not match_ml:
        return None
    typo_num = match_ml.group(1)
    candidatos = []
    for var in variantes:
        var_n = normalizar(var)
        var_match = re.match(r'^(\d+)ml$', var_n)
        if var_match and typo_num in var_match.group(1):
            candidatos.append(var)
    return candidatos[0] if len(candidatos) == 1 else None


# ── Fuzzy match de item ────────────────────────────────────────────────────


def fuzzy_match_item(
    texto: str,
    alias_para_id: dict[str, str],
    cutoff: int = FUZZY_ITEM_CUTOFF,
) -> tuple[str | None, float, str | None]:
    """Fuzzy match de texto contra aliases do cardápio.

    Args:
        texto: Texto digitado pelo usuário.
        alias_para_id: Mapeamento alias → item_id.
        cutoff: Score mínimo (0-100).

    Returns:
        Tupla (alias_match, score, item_id) ou (None, 0, None).
    """
    tokens = extrair_tokens_significativos(texto)
    if not tokens:
        return None, 0, None

    candidatos = list(alias_para_id.keys())
    melhor_alias: str | None = None
    melhor_score = 0.0

    for token in [*tokens, normalizar(texto)]:
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
    cutoff: int = FUZZY_VARIANTE_CUTOFF,
) -> tuple[str | None, float]:
    """Fuzzy match de texto contra variantes válidas.

    Usa match_variante_numerica primeiro para variantes do tipo NNNml.
    Depois tenta fuzzy normal com detecção de ambiguidade.

    Args:
        texto: Texto digitado pelo usuário.
        variantes: Lista de variantes válidas do cardápio.
        cutoff: Score mínimo (0-100).

    Returns:
        Tupla (variante_match, score) ou (None, 0).
    """
    if not texto or not texto.strip():
        return None, 0

    texto_n = normalizar(texto)

    # Tentar matching numérico primeiro
    resultado_num = match_variante_numerica(texto_n, variantes)
    if resultado_num:
        return resultado_num, 95.0

    # Fuzzy normal
    resultado = process.extractOne(
        texto_n, variantes, scorer=fuzz.ratio, score_cutoff=cutoff
    )
    if not resultado:
        return None, 0

    # Verificar ambiguidade: se top-2 estão dentro de AMBIGUIDADE_LIMITE pontos
    todos_matches = process.extract(
        texto_n, variantes, scorer=fuzz.ratio, score_cutoff=cutoff, limit=2
    )
    if len(todos_matches) >= 2:
        _, score1, _ = resultado
        _, score2, _ = todos_matches[1]
        if score1 - score2 < AMBIGUIDADE_LIMITE:
            return None, 0  # ambíguo, melhor não arriscar

    return resultado[0], resultado[1]


__all__ = [
    'extrair_tokens_significativos',
    'fuzzy_match_item',
    'fuzzy_match_variante',
    'match_variante_numerica',
    'normalizar',
]
