"""Helpers para extrair contexto relevante de decisoes.

Funcoes utilitarias para capturar o estado no momento de uma decisao,
usadas pelo DecisorLogger para registrar o contexto completo.

Example:
    ```python
    from src.observabilidade.contexto import extrair_contexto_dispatcher

    contexto = extrair_contexto_dispatcher(state)
    loggers.decisor.registrar(
        componente='dispatcher',
        decisao='adicionar_item',
        contexto=contexto,
    )
    ```
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.graph.state import State


def extrair_contexto_classificacao(
    mensagem: str,
    mensagem_norm: str = '',
    caminho: str = '',
    carrinho_size: int = 0,
) -> dict:
    """Extrai contexto relevante para decisao de classificacao.

    Args:
        mensagem: Mensagem original do usuario.
        mensagem_norm: Mensagem normalizada.
        caminho: Caminho usado (lookup, rag_forte, llm_rag, llm_fixo).
        carrinho_size: Tamanho atual do carrinho.

    Returns:
        Dict com contexto para logging.
    """
    return {
        'mensagem_original': mensagem,
        'mensagem_norm': mensagem_norm,
        'caminho': caminho,
        'carrinho_size': carrinho_size,
    }


def extrair_contexto_dispatcher(state: State) -> dict:
    """Extrai contexto relevante para decisao do dispatcher.

    Args:
        state: Estado atual do grafo.

    Returns:
        Dict com contexto para logging.
    """
    carrinho = state.get('carrinho', [])
    return {
        'mensagem': state.get('mensagem_atual', ''),
        'carrinho_size': len(carrinho),
        'carrinho_itens': [
            {'item_id': i.get('item_id', ''), 'variante': i.get('variante', '')}
            for i in carrinho
        ],
        'intent': state.get('intent', ''),
    }


def extrair_contexto_extracao(mensagem: str, itens: list[dict]) -> dict:
    """Extrai contexto relevante para decisao de extracao.

    Args:
        mensagem: Mensagem original.
        itens: Itens extraidos.

    Returns:
        Dict com contexto para logging.
    """
    return {
        'mensagem': mensagem,
        'itens_encontrados': len(itens),
        'itens_ids': [i.get('item_id', '') for i in itens],
    }


def extrair_contexto_negacao(mensagem: str, tokens_negacao: list[str]) -> dict:
    """Extrai contexto relevante para decisao de negacao.

    Args:
        mensagem: Mensagem original.
        tokens_negacao: Tokens de negacao encontrados.

    Returns:
        Dict com contexto para logging.
    """
    return {
        'mensagem': mensagem,
        'tokens_negacao_encontrados': tokens_negacao,
    }
