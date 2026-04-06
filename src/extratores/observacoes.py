"""Detecao de observacoes e modificadores em itens do cardapio.

Camada 7 do pipeline de extracao. Identificacoes sao anotacoes livres
que o usuario faz sobre como quer o item (ex: "bem gelada", "caprichado",
"bem passado").

Exemplos:
    - "coca bem gelada" -> observacoes=["bem gelada"]
    - "hamburguer caprichado" -> observacoes=["caprichado"]
    - "hamburguer bem passado" -> observacoes=["bem passado"]
    - "coca super gelada" -> observacoes=["super gelada"]
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.config import get_cardapio

if TYPE_CHECKING:
    from spacy.tokens import Doc


def detectar_observacoes(doc: Doc) -> list[str]:
    """Detecta observacoes genericas (lista fixa + modificadores de intensidade).

    Duas estrategias sao usadas:

    1. **Lista fixa**: observacoes predefinidas no cardapio
       (ex: "bem passado", "ao ponto", "caprichado").
    2. **Modificadores de intensidade**: padroes como "bem gelada",
       "muito quente", "super caprichado" — intensificador + ADJ/NOUN/VERB.

    IMPORTANT: Frases que contem triggers de complemento ("com", "extra",
    "adicional") seguidos de intensificadores sao ignoradas — elas pertencem
    ao modulo de complementos, nao observacoes.

    Args:
        doc: Documento spaCy processado.

    Returns:
        Lista de observacoes encontradas.
    """
    observacoes: list[str] = []
    texto = doc.text.lower()

    # Skip entire text if it contains complemento triggers followed by intensifiers
    # e.g. "com bastante X" is a complemento phrase, not an observation
    complemento_triggers = {'com', 'extra', 'adicional'}
    intensificadores = {'bem', 'muito', 'bastante', 'super', 'mega'}

    tokens_lower = [t.lower_ for t in doc]
    has_complemento_phrase = False
    for i, tok in enumerate(tokens_lower):
        if tok in complemento_triggers:
            # Check if next token is an intensifier
            if i + 1 < len(tokens_lower) and tokens_lower[i + 1] in intensificadores:
                has_complemento_phrase = True
                break

    if has_complemento_phrase:
        return observacoes

    # Lista fixa do cardapio
    cardapio = get_cardapio()
    for obs in cardapio.get('observacoes_genericas', []):
        if obs in texto:
            observacoes.append(obs)

    # Modificadores de intensidade
    for token in doc:
        if token.lower_ in intensificadores:
            try:
                alvo = token.nbor(1)
                if alvo.pos_ in ('ADJ', 'NOUN', 'VERB'):
                    obs_texto = f'{token.text} {alvo.text}'
                    if obs_texto not in observacoes:
                        observacoes.append(obs_texto)
            except IndexError:
                pass

    return observacoes


def detectar_modificadores(doc: Doc) -> list[str]:
    """Detecta apenas modificadores de intensidade.

    Funcao auxiliar para uso isolado quando necessario.

    Args:
        doc: Documento spaCy processado.

    Returns:
        Lista de modificadores encontrados (ex: ["bem passado", "super gelada"]).
    """
    modificadores: list[str] = []
    intensificadores = {'bem', 'muito', 'bastante', 'super', 'mega'}

    for token in doc:
        if token.lower_ in intensificadores:
            try:
                alvo = token.nbor(1)
                if alvo.pos_ in ('ADJ', 'NOUN', 'VERB'):
                    mod_texto = f'{token.text} {alvo.text}'
                    if mod_texto not in modificadores:
                        modificadores.append(mod_texto)
            except IndexError:
                pass

    return modificadores
