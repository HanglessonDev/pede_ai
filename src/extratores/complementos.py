"""Detecao de complementos adicionados a itens do cardapio.

Camada 6 do pipeline de extracao. Identifica ingredientes/opcoes
adicionais que o usuario quer incluir em um item especifico.

Exemplos:
    - "hamburguer com bacon" -> complementos=["bacon"]
    - "hamburguer com o queijo" -> complementos=["queijo"]
    - "hamburguer bacon extra" -> complementos=["bacon"]

Os complementos validos sao obtidos do cardapio, especificamente
do campo ``complementos`` de cada item.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from spacy.tokens import Doc

    from src.extratores.config import ExtratorConfig


def _get_item_por_id(cardapio: dict, item_id: str) -> dict:
    """Busca item do cardapio por ID."""
    for item in cardapio.get('itens', []):
        if item['id'] == item_id:
            return item
    return {}


def _tokens_a_frente(doc: 'Doc', token, max_tokens: int = 5):
    """Yield tokens apos ``token`` (excluindo o proprio token)."""
    for t in doc[token.i + 1 :]:
        if t.pos_ in ('PUNCT', 'SPACE'):
            continue
        yield t
        max_tokens -= 1
        if max_tokens <= 0:
            break


def _tokens_a_frente_complemento(
    doc: 'Doc',
    token,
    max_tokens: int = 5,
    skip_words: frozenset[str] | None = None,
):
    """Scan forward from ``token``, skipping prepositions/articles.

    Unlike ``_tokens_a_frente``, this does NOT stop at stop words —
    it skips prepositions (de, do, da) and articles (um, uma, o, a)
    and keeps looking for valid complemento names up to max_tokens.

    Args:
        doc: Documento spaCy.
        token: Token de partida (ex: trigger "com", "adicional").
        max_tokens: Numero maximo de tokens significativos a examinar.
        skip_words: Palavras a pular silenciosamente (default: preposicoes + artigos).

    Yields:
        Tokens que nao sao de pulo, ate max_tokens.
    """
    if skip_words is None:
        skip_words = frozenset({'de', 'do', 'da', 'um', 'uma', 'o', 'a', 'os', 'as', 'e', 'ou'})
    for t in doc[token.i + 1 :]:
        if t.pos_ in ('PUNCT', 'SPACE'):
            continue
        if t.lower_ in skip_words:
            continue  # skip but don't count against max_tokens for matches
        yield t
        max_tokens -= 1
        if max_tokens <= 0:
            break


def _token_anterior(doc: 'Doc', token):
    """Retorna o token significativo anterior a ``token``."""
    for t in reversed(doc[: token.i]):
        if t.pos_ not in ('PUNCT', 'SPACE', 'DET', 'ADP'):
            return t
    return None


def detectar_complementos(
    doc: 'Doc', item_id: str, cardapio: dict, config: 'ExtratorConfig'
) -> list[str]:
    """Detecta complementos adicionados ao item.

    Duas estrategias sao usadas:

    1. **Padrao direto**: "com bacon" — palavra-chave + nome do complemento
       nos tokens seguintes.
    2. **Padrao inverso**: "bacon extra" — nome do complemento seguido de
       ADJ como "extra" ou "adicional".

    Args:
        doc: Documento spaCy processado.
        item_id: ID do item no cardapio (para buscar complementos validos).
        cardapio: Dados completos do cardapio.
        config: Configuracao do extrator.

    Returns:
        Lista de nomes de complementos encontrados.
    """
    item_info = _get_item_por_id(cardapio, item_id)
    complementos_validos = {
        c['nome'].lower() for c in item_info.get('complementos', [])
    }

    if not complementos_validos:
        return []

    complementos: list[str] = []
    texto_lower = doc.text.lower()

    # Strategy 1: "com <complemento>" and "adicional de <complemento>"
    # Use _tokens_a_frente_complemento which skips prepositions/articles
    # and does NOT stop at connectives (they're only stopping points for remocoes).
    for token in doc:
        if token.lower_ in config.palavras_complemento:
            for next_t in _tokens_a_frente_complemento(doc, token):
                if next_t.lower_ in complementos_validos:
                    if next_t.text not in complementos:
                        complementos.append(next_t.text)

        # Strategy 2: Padrao inverso — "bacon extra" → NOUN + ADJ
        if token.lower_ in ('extra', 'adicional') and token.pos_ == 'ADJ':
            prev_t = _token_anterior(doc, token)
            if prev_t and prev_t.text.lower() in complementos_validos:
                if prev_t.text not in complementos:
                    complementos.append(prev_t.text)

        # Strategy 2b: "adicional" as trigger word (not ADJ) — "adicional de queijo"
        if token.lower_ == 'adicional' and token.lower_ in config.palavras_complemento:
            for next_t in _tokens_a_frente_complemento(doc, token):
                if next_t.lower_ in complementos_validos:
                    if next_t.text not in complementos:
                        complementos.append(next_t.text)

    # Strategy 3: Also check for complemento names appearing after "com" anywhere in text
    # This handles cases where spaCy might tokenize differently
    for palavra in config.palavras_complemento:
        if palavra in ('com',) and palavra in texto_lower:
            # Find position of "com" in text and look for complemento names after it
            pos_com = texto_lower.find(palavra)
            texto_depois = texto_lower[pos_com + len(palavra) :]
            for comp_nome in complementos_validos:
                if comp_nome in texto_depois:
                    # Find the actual token text (preserve original case)
                    for token in doc:
                        if token.lower_ == comp_nome and token.text not in complementos:
                            complementos.append(token.text)

    return complementos
