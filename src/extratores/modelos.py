"""Value objects imutaveis para extracao de itens do cardapio.

Todos os models sao frozen dataclasses — representam valores, nao entidades.

Example:
    ```python
    from src.extratores.modelos import ItemExtraido

    item = ItemExtraido(
        item_id='lanche_001',
        quantidade=2,
        variante='duplo',
        remocoes=['cebola'],
    )
    item.item_id
    'lanche_001'
    ```
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ItemExtraido:
    """Item extraido da mensagem do usuario.

    Attributes:
        item_id: ID do item no cardapio.
        quantidade: Quantidade solicitada.
        variante: Variante selecionada (ou None).
        remocoes: Lista de ingredientes a remover.
    """

    item_id: str
    quantidade: int
    variante: str | None
    remocoes: list[str]


@dataclass(frozen=True)
class ItemOriginal:
    """Item do carrinho identificado para troca.

    Attributes:
        item_id: ID do item no cardapio.
        nome: Nome legivel do item.
        indices: Indices no carrinho que matcham este item.
    """

    item_id: str
    nome: str
    indices: list[int]


@dataclass(frozen=True)
class ExtracaoTroca:
    """Resultado da extracao de troca.

    Attributes:
        caso: Tipo de troca ('A', 'B', 'C', 'vazio').
        item_original: Item do carrinho a ser trocado (ou None).
        variante_nova: Nova variante desejada (ou None).
    """

    caso: Literal['A', 'B', 'C', 'vazio']
    item_original: ItemOriginal | None
    variante_nova: str | None


@dataclass(frozen=True)
class MatchCarrinho:
    """Match de item mencionado com item do carrinho.

    Attributes:
        item_id: ID do item no cardapio.
        variante: Variante do item no carrinho (ou None).
        indices: Indices no carrinho que matcham.
    """

    item_id: str
    variante: str | None
    indices: list[int]


@dataclass(frozen=True)
class Segmento:
    """Fatia do texto para processamento por camada.

    Attributes:
        texto: Texto completo da mensagem (referencia).
        start: Indice de token inicial (nao caractere).
        end: Indice de token final (exclusive).
    """

    texto: str
    start: int  # indice de TOKEN
    end: int    # indice de TOKEN (exclusive)

    def slice_tokens(self, doc) -> str:
        """Extrai texto do segmento usando indices de token.

        Args:
            doc: Documento spaCy processado.

        Returns:
            Texto fatiado do segmento.
        """
        return doc[self.start:self.end].text


@dataclass(frozen=True)
class ItemMencionado:
    """Item mencionado na mensagem (uso interno).

    Attributes:
        texto: Texto normalizado do item mencionado.
        variante: Variante mencionada junto com o item (ou None).
        ent_id: ID da entidade no spaCy (ent_id_).
    """

    texto: str
    variante: str | None
    ent_id: str
