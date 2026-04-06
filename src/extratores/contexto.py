"""Janela de contexto para associacao de tokens a itens.

Limita o alcance de tokens que podem ser associados a um ITEM
extratado, evitando que tokens distantes sejam incorretamente
vinculados (ex: 'dupla' de 'coca dupla' nao vira variante do
'hamburguer' que aparece antes).
"""

from __future__ import annotations


def extrair_contexto_item(doc, item_ent, janela: int = 3) -> tuple[int, int]:
    """Retorna o range de tokens dentro da janela de contexto de um ITEM.

    Args:
        doc: Documento spaCy processado.
        item_ent: Entidade spaCy do tipo ITEM.
        janela: Numero maximo de tokens antes e depois do ITEM.

    Returns:
        Tupla (start, end) com os indices dos tokens na janela.
    """
    start = max(0, item_ent.start - janela)
    end = min(len(doc), item_ent.end + janela)
    return start, end


def token_esta_na_janela(
    token_pos: int, item_start: int, item_end: int, janela: int = 3
) -> bool:
    """Verifica se um token esta dentro da janela de contexto de um ITEM.

    Args:
        token_pos: Posicao do token no documento.
        item_start: Posicao inicial do ITEM.
        item_end: Posicao final do ITEM.
        janela: Numero maximo de tokens de distancia.

    Returns:
        True se o token esta dentro da janela.
    """
    return (item_start - janela) <= token_pos <= (item_end + janela)
