"""Captura de remocoes de ingredientes.

Funcao pura para capturar itens a remover apos sinais como 'sem', 'tira', etc.

Example:
    ```python
    from src.extratores.remocoes import capturar_remocoes, capturar_remocoes_v2
    from src.extratores.config import get_extrator_config

    config = get_extrator_config()
    remocoes = capturar_remocoes(doc, config)

    # Versao scope-aware (filtra ITEMs do cardapio):
    itens_ids = frozenset({'hamburguer', 'batata', 'coca'})
    remocoes = capturar_remocoes_v2(doc, config, itens_ids)
    ```
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from spacy.tokens import Doc

    from src.extratores.config import ExtratorConfig


def _pular_artigos(tokens: list, indice: int, pos_ignoraveis: frozenset[str]) -> int:
    """Pula artigos e preposicoes a partir do indice."""
    while indice < len(tokens) and tokens[indice].pos_ in pos_ignoraveis:
        indice += 1
    return indice


def _deve_parar_no_conectivo(
    tokens: list,
    indice_conectivo: int,
    palavras_remocao: frozenset[str],
    pos_ignoraveis: frozenset[str],
) -> bool:
    """Decide se deve parar no conectivo 'e'/'ou'."""
    indice = _pular_artigos(tokens, indice_conectivo + 1, pos_ignoraveis)
    if indice >= len(tokens):
        return False
    return (
        tokens[indice].text.lower() in palavras_remocao or tokens[indice].text.isdigit()
    )


def _tokens_a_frente(doc: Doc, token) -> list:
    """Retorna tokens apos o token atual."""
    return list(doc)[token.i + 1 :]


def _tem_nova_remocao_a_frente(doc, token_atual, config: ExtratorConfig) -> bool:
    """Verifica se ha uma nova remocao apos o token atual."""
    for t in _tokens_a_frente(doc, token_atual):
        if t.lower_ in config.palavras_remocao:
            return True
        if t.lower_ in config.palavras_parada:
            return False
    return False


def capturar_remocoes(doc: Doc, config: ExtratorConfig) -> list[tuple[str, int]]:
    """Captura itens a remover apos sinais como 'sem', 'tira', etc.

    Args:
        doc: Documento spaCy processado.
        config: Configuracao com palavras de remocao, conectivos, etc.

    Returns:
        Lista de tuplas (texto, indice_do_token).
    """
    remocoes: list[tuple[str, int]] = []
    tokens = list(doc)
    indice = 0

    while indice < len(tokens):
        token = tokens[indice]

        if token.text.lower() not in config.palavras_remocao:
            indice += 1
            continue

        # Encontrou sinal de remocao, captura itens seguintes
        indice += 1
        while indice < len(tokens):
            token = tokens[indice]

            # Conectivos: decide se para ou continua
            if token.text.lower() in config.conectivos:
                if _deve_parar_no_conectivo(
                    tokens, indice, config.palavras_remocao, config.pos_ignoraveis
                ):
                    break
                indice += 1
                continue

            # Palavras de parada obrigatoria
            if token.text.lower() in config.palavras_parada:
                break

            # Ignora artigos/preposicoes
            if token.pos_ in config.pos_ignoraveis:
                indice += 1
                continue

            # Token relevante: adiciona as remocoes
            remocoes.append((token.text, token.i))
            indice += 1

    return remocoes


def capturar_remocoes_v2(
    doc: Doc,
    config: ExtratorConfig,
    itens_ids: frozenset[str],
) -> list[tuple[str, int]]:
    """Captura remocoes filtrando tokens que sao ITEMs do cardapio.

    Diferenca para capturar_remocoes(): filtra tokens cujo nome normalizado
    esta em itens_ids, evitando que nomes de lanches/bebidas/acompanhamentos
    sejam capturados como ingredientes a remover.

    Args:
        doc: Documento spaCy processado.
        config: Configuracao com palavras de remocao, conectivos, etc.
        itens_ids: Set de nomes + aliases do cardapio (normalizados).

    Returns:
        Lista de tuplas (texto, indice_do_token).
    """
    from src.extratores.normalizador import normalizar_para_busca  # noqa: PLC0415

    remocoes: list[tuple[str, int]] = []
    tokens = list(doc)
    indice = 0

    while indice < len(tokens):
        token = tokens[indice]

        if token.text.lower() not in config.palavras_remocao:
            indice += 1
            continue

        # Encontrou sinal de remocao, captura itens seguintes
        indice += 1
        while indice < len(tokens):
            token = tokens[indice]

            # Conectivos: decide se para ou continua
            if token.text.lower() in config.conectivos:
                if _deve_parar_no_conectivo(
                    tokens, indice, config.palavras_remocao, config.pos_ignoraveis
                ):
                    break
                indice += 1
                continue

            # Palavras de parada obrigatoria
            if token.text.lower() in config.palavras_parada:
                break

            # Ignora artigos/preposicoes
            if token.pos_ in config.pos_ignoraveis:
                indice += 1
                continue

            # FILTRO CRITICO: se e ITEM do cardapio, nao e remocao
            if normalizar_para_busca(token.text) in itens_ids:
                indice += 1
                continue

            # Token relevante: adiciona as remocoes
            remocoes.append((token.text, token.i))
            indice += 1

    return remocoes
