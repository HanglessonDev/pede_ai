"""Modelos de carrinho de pedidos.

Classes OO para representar o carrinho e seus itens,
substituindo o uso de dicts soltos.

Example:
    ```python
    from src.graph.handlers.carrinho import Carrinho, CarrinhoItem

    carrinho = Carrinho()
    carrinho.adicionar(CarrinhoItem('lanche_001', 2, 3000, 'duplo'))
    carrinho.total_reais()  # 60.0
    ```
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.config import get_nome_item


@dataclass(frozen=True)
class CarrinhoItem:
    """Item individual no carrinho.

    Attributes:
        item_id: ID do item no cardapio.
        quantidade: Quantidade deste item.
        preco_centavos: Preco unitario em centavos.
        variante: Variante selecionada (ou None).
    """

    item_id: str
    quantidade: int
    preco_centavos: int
    variante: str | None = None

    def preco_reais(self) -> float:
        """Retorna preco unitario em reais."""
        return self.preco_centavos / 100

    def subtotal(self) -> int:
        """Retorna subtotal (preco * quantidade) em centavos."""
        return self.preco_centavos * self.quantidade

    def subtotal_reais(self) -> float:
        """Retorna subtotal em reais."""
        return self.subtotal() / 100

    def to_dict(self) -> dict:
        """Converte para dict compativel com State."""
        return {
            'item_id': self.item_id,
            'quantidade': self.quantidade,
            'preco': self.preco_centavos,
            'variante': self.variante,
        }

    @classmethod
    def from_dict(cls, data: dict) -> CarrinhoItem:
        """Cria CarrinhoItem a partir de dict do State."""
        return cls(
            item_id=data['item_id'],
            quantidade=data.get('quantidade', 1),
            preco_centavos=data['preco'],
            variante=data.get('variante'),
        )


@dataclass
class Carrinho:
    """Carrinho de pedidos com metodos de negocio.

    Attributes:
        itens: Lista de itens no carrinho.
    """

    itens: list[CarrinhoItem] = field(default_factory=list)

    def adicionar(self, item: CarrinhoItem) -> None:
        """Adiciona um item ao carrinho."""
        self.itens.append(item)

    def remover_indices(self, indices: set[int]) -> None:
        """Remove itens nos indices especificados."""
        self.itens = [i for idx, i in enumerate(self.itens) if idx not in indices]

    def limpar(self) -> None:
        """Limpa todos os itens do carrinho."""
        self.itens.clear()

    def total_centavos(self) -> int:
        """Retorna total do carrinho em centavos."""
        return sum(item.subtotal() for item in self.itens)

    def total_reais(self) -> float:
        """Retorna total do carrinho em reais."""
        return self.total_centavos() / 100

    def vazio(self) -> bool:
        """Retorna True se o carrinho esta vazio."""
        return not self.itens

    def tamanho(self) -> int:
        """Retorna numero de itens no carrinho."""
        return len(self.itens)

    def formatar(self) -> str:
        """Formata o carrinho como texto legivel.

        Returns:
            String com um item por linha.
        """
        if self.vazio():
            return 'Seu carrinho esta vazio.'

        linhas = []
        for item in self.itens:
            nome = get_nome_item(item.item_id) or item.item_id
            if item.variante:
                nome = f'{nome} ({item.variante})'
            linhas.append(f'{item.quantidade}x {nome} — R$ {item.subtotal_reais():.2f}')

        linhas.append(f'\nTotal: R$ {self.total_reais():.2f}')
        return '\n'.join(linhas)

    def to_state_dicts(self) -> list[dict]:
        """Converte para lista de dicts compativel com State."""
        return [item.to_dict() for item in self.itens]

    @classmethod
    def from_state_dicts(cls, dados: list[dict]) -> Carrinho:
        """Cria Carrinho a partir de lista de dicts do State."""
        return cls(itens=[CarrinhoItem.from_dict(d) for d in dados])
