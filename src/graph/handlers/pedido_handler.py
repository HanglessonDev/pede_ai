"""Handler de processamento de pedidos.

Processa itens extraidos da mensagem do usuario, calcula precos,
adiciona ao carrinho e envia itens pendentes para fila de clarificacao.

Example:
    ```python
    from src.graph.handlers.pedido_handler import processar_pedido

    itens = [
        {'item_id': 'lanche_002', 'quantidade': 1, 'variante': None, 'remocoes': []}
    ]
    result = processar_pedido(itens, [])
    len(result.carrinho)
    1
    ```
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.config import get_item_por_id, get_variantes
from src.graph.handlers.carrinho import Carrinho, CarrinhoItem
from src.graph.state import RetornoNode


@dataclass
class ResultadoPedir:
    """Resultado do processamento de pedido.

    Attributes:
        carrinho: Carrinho atualizado.
        fila: Itens pendentes de clarificacao.
        resposta: Texto formatado para o usuario.
    """

    carrinho: list[dict] = field(default_factory=list)
    fila: list[dict] = field(default_factory=list)
    resposta: str = ''

    def to_dict(self) -> RetornoNode:
        """Converte para dicionario compativel com LangGraph State."""
        return {
            'carrinho': self.carrinho,
            'fila_clarificacao': self.fila,
            'resposta': self.resposta,
            'etapa': 'clarificando_variante' if self.fila else 'coletando',
        }


def _calcular_preco_item(item: dict, item_data: dict) -> int | None:
    """Calcula o preco total de um item considerando quantidade e variantes.

    Args:
        item: Dicionario do item extraido com ``quantidade`` e opcional ``variante``.
        item_data: Dados completos do item do cardapio.

    Returns:
        Preco total em centavos ou None se nao foi possivel calcular.
    """
    preco_base = item_data.get('preco')
    variante = item.get('variante')
    quantidade = item['quantidade']

    if preco_base is not None:
        return preco_base * quantidade

    variantes_validas = get_variantes(item['item_id'])
    if variante and variante in variantes_validas:
        variante_obj = next(
            (v for v in item_data.get('variantes', []) if v['opcao'] == variante),
            None,
        )
        if variante_obj:
            return variante_obj['preco'] * quantidade

    return None


def processar_pedido(
    itens_extraidos: list[dict],
    carrinho_existente: list[dict],
) -> ResultadoPedir:
    """Processa itens extraidos e os adiciona ao carrinho.

    Para cada item extraido, verifica se possui preco fixo ou variantes.
    Itens com variantes invalidas ou nao especificadas vao para a fila
    de clarificacao.

    Args:
        itens_extraidos: Lista de itens extraidos da mensagem.
        carrinho_existente: Carrinho atual do estado (para mesclar).

    Returns:
        ResultadoPedir com carrinho, fila e resposta atualizados.
    """
    carrinho = Carrinho.from_state_dicts(carrinho_existente)
    fila: list[dict] = []
    itens_adicionados: list[CarrinhoItem] = []

    for item in itens_extraidos:
        item_data = get_item_por_id(item['item_id'])
        if item_data is None:
            continue

        preco_total = _calcular_preco_item(item, item_data)

        if preco_total is not None:
            carrinho_item = CarrinhoItem(
                item_id=item['item_id'],
                quantidade=item['quantidade'],
                preco_centavos=preco_total,
                variante=item.get('variante'),
            )
            carrinho.adicionar(carrinho_item)
            itens_adicionados.append(carrinho_item)
        else:
            fila.append(
                {
                    'item': item,
                    'item_id': item['item_id'],
                    'nome': item_data['nome'],
                    'campo': 'variante',
                    'opcoes': get_variantes(item['item_id']),
                }
            )

    if fila:
        proxima = fila[0]
        opcoes = ', '.join(proxima['opcoes'])
        resposta = f'{proxima["nome"]}: qual opcao? {opcoes}'
    elif itens_adicionados:
        resposta = carrinho.formatar()
    else:
        resposta = ''

    return ResultadoPedir(
        carrinho=carrinho.to_state_dicts(),
        fila=fila,
        resposta=resposta,
    )
