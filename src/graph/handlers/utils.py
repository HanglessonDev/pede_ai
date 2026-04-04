"""Utilitários compartilhados entre handlers do grafo."""

from src.config import get_nome_item


def calcular_total_carrinho(carrinho: list[dict]) -> int:
    """Calcula o total do carrinho em centavos.

    Args:
        carrinho: Lista de itens no carrinho.

    Returns:
        Total em centavos.

    Example:
        ```python
        carrinho = [
            {'item_id': 'lanche_001', 'quantidade': 1, 'preco': 1500},
            {'item_id': 'bebida_001', 'quantidade': 2, 'preco': 500},
        ]
        calcular_total_carrinho(carrinho)
        2500
        ```
    """
    return sum(item.get('preco', 0) for item in carrinho)


def formatar_carrinho(carrinho: list[dict]) -> str:
    """Formata o carrinho como string legível.

    Args:
        carrinho: Lista de itens no carrinho.

    Returns:
        String formatada com quantidade, nome e preço de cada item.

    Example:
        ```python
        carrinho = [
            {'item_id': 'lanche_001', 'quantidade': 1, 'preco': 1500},
        ]
        formatar_carrinho(carrinho)
        '1x Hambúrguer — R$ 15.00'
        ```
    """
    linhas = [
        f'{it["quantidade"]}x {get_nome_item(it["item_id"]) or it["item_id"]} — R$ {it["preco"] / 100:.2f}'
        for it in carrinho
    ]
    return '\n'.join(linhas)
