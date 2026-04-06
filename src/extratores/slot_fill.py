"""Slot Fill — validacao cruzada entre extrator e cardapio.

Usado para confirmar que itens extraidos pelo pipeline realmente
existem no cardapio, reduzindo confianca quando ha divergencia.
"""

from __future__ import annotations

from src.extratores.normalizador import normalizar_para_busca


def slot_fill_menu_first(mensagem: str, cardapio: dict) -> list[str]:
    """Validacao cruzada: encontra itens do cardapio na mensagem.

    Percorre todos os itens e seus aliases, normaliza e busca
    substrings na mensagem normalizada.

    Args:
        mensagem: Texto original do usuario.
        cardapio: Dicionario do cardapio com chave 'itens'.

    Returns:
        Lista de item_ids encontrados na mensagem.
    """
    msg_norm = normalizar_para_busca(mensagem)
    encontrados: list[str] = []
    for item in cardapio.get('itens', []):
        todos_nomes = [item['nome'], *item.get('aliases', [])]
        for nome in todos_nomes:
            if normalizar_para_busca(nome) in msg_norm:
                encontrados.append(item['id'])
                break
    return encontrados
