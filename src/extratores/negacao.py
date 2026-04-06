"""Detecao de negacao/cancelamento em mensagens do usuario.

Usa abordagem de 3 tiers para evitar falsos positivos:

- Tier 1: Expressoes completas (match em qualquer lugar)
- Tier 2: Palavras de cancelamento autonomas (match em qualquer lugar)
- Tier 3: Palavras dependentes de contexto (so' match com verbo de desejo)

Casos especiais:
- "melhor nao/nao" → True (rejeicao suave)
- "sem" NUNCA e' negacao (e' remocao)
"""

from __future__ import annotations

import re

# ── Tier 1: Expressoes completas de negacao (match em qualquer lugar) ───────
# Sao frases ambiguas que sempre indicam negacao.
EXPRESSOES_NEGACAO = [
    'nao quero',
    'não quero',
    'quero nao',
    'quero não',
    'nao quer',
    'não quer',
    'quer nao',
    'quer não',
    'deixa pra la',
    'deixa para lá',
    'deixa pra lá',
    'deixa para la',
    'muda de ideia',
]

# ── Tier 2: Palavras de cancelamento autonomas (match em qualquer lugar) ─────
# Sao comandos claros de cancelamento.
PALAVRAS_CANCELAMENTO = [
    'esquece',
    'esqueça',
    'esqueca',
    'cancela',
    'cancelar',
    'desisto',
]

# ── Tier 3: Palavras dependentes de contexto ─────────────────────────────────
# So' indicam negacao quando proximas de um verbo de desejo.
PALAVRAS_NEGACAO_CONTEXTUAL = ['nao', 'não', 'nem']

# Verbos de desejo que, quando proximos de palavras contextuais, indicam negacao
VERBOS_DESEJO = ['quero', 'quer', 'pedir', 'comprar']

# ── Caso especial: "melhor nao/nao" ──────────────────────────────────────────
PADROES_ESPECIAIS = [
    r'melhor\s+nao\b',
    r'melhor\s+não\b',
]


def _match_expressao(texto: str, expressao: str) -> bool:
    """Verifica se uma expressao aparece no texto (case-insensitive, word-boundary)."""
    texto_lower = texto.lower()
    expressao_lower = expressao.lower()
    # Para expressoes multi-palavra, usa substring simples
    return expressao_lower in texto_lower


def _match_palavra_cancelamento(texto: str, palavra: str) -> bool:
    """Verifica se uma palavra de cancelamento aparece como palavra inteira."""
    texto_lower = texto.lower()
    palavra_lower = palavra.lower()
    # Word boundary: a palavra deve estar isolada
    padrao = rf'\b{re.escape(palavra_lower)}\b'
    return bool(re.search(padrao, texto_lower))


def _match_contextual(texto: str) -> bool:
    """Verifica se ha' palavra contextual proxima de verbo de desejo.

    Procura por padroes como:
    - "nao quero", "nao quer", "nem pedir"
    - "quero nao", "quer nao", "pedir nem"

    Exclui construcoes subordinadas: "quero que nao venha X"
    (aqui "nao" modifica "venha", nao o verbo de desejo).
    """
    texto_lower = texto.lower()
    tokens = re.findall(r'\b\w+\b', texto_lower)

    for i, token in enumerate(tokens):
        if token not in PALAVRAS_NEGACAO_CONTEXTUAL:
            continue

        # Exclui caso "que" aparece entre o verbo de desejo e "nao"
        # ex: "quero que nao venha" — "que" esta' antes de "nao"
        tem_que_antes = 'que' in tokens[max(0, i - 3):i]
        if tem_que_antes:
            continue

        # Olha tokens vizinhos (janela de 3 tokens)
        inicio = max(0, i - 3)
        fim = min(len(tokens), i + 4)
        vizinhos = tokens[inicio:i] + tokens[i + 1:fim]

        # Verifica se algum vizinho e' verbo de desejo
        for vizinho in vizinhos:
            if vizinho in VERBOS_DESEJO:
                return True

    return False


def detectar_negacao(texto: str) -> bool:
    """Detecta se o texto contem negacao/cancelamento de pedido.

    Abordagem de 3 tiers:
    1. Expressoes completas → match direto
    2. Palavras de cancelamento → match direto (word boundary)
    3. Palavras contextuais → so' match com verbo de desejo proximo

    Args:
        texto: Texto da mensagem do usuario.

    Returns:
        True se o texto indica negacao/cancelamento, False caso contrario.
    """
    if not texto or not texto.strip():
        return False

    # Tier 1: Expressoes completas de negacao
    for expressao in EXPRESSOES_NEGACAO:
        if _match_expressao(texto, expressao):
            return True

    # Tier 2: Palavras de cancelamento autonomas
    for palavra in PALAVRAS_CANCELAMENTO:
        if _match_palavra_cancelamento(texto, palavra):
            return True

    # Caso especial: "melhor nao/nao"
    for padrao in PADROES_ESPECIAIS:
        if re.search(padrao, texto.lower()):
            return True

    # Tier 3: Palavras contextuais (nao, não, nem) — precisam de contexto
    if _match_contextual(texto):
        return True

    return False
