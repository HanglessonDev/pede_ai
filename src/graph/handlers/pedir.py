"""Handler de processamento de pedidos.

Processa itens extraídos da mensagem do usuário, calcula preços,
adiciona ao carrinho e envia itens pendentes para fila de clarificação.

Example:
    ```python
    from src.graph.handlers.pedir import processar

    itens = [
        {'item_id': 'lanche_002', 'quantidade': 1, 'variante': None, 'remocoes': []}
    ]
    result = processar(itens, [])
    len(result.carrinho)
    1
    ```
"""

from dataclasses import dataclass, field

from src.config import get_item_por_id, get_preco_item, get_variantes
from src.graph.handlers.utils import formatar_carrinho
from src.graph.state import RetornoNode


@dataclass
class ResultadoPedir:
    """Resultado do processamento de pedido.

    Attributes:
        carrinho: Itens adicionados ao carrinho.
        fila: Itens pendentes de clarificação.
        resposta: Texto formatado para o usuário.
    """

    carrinho: list = field(default_factory=list)
    fila: list = field(default_factory=list)
    resposta: str = ''

    def to_dict(self) -> RetornoNode:
        """Converte para dicionário compatível com LangGraph State."""
        return {
            'carrinho': self.carrinho,
            'fila_clarificacao': self.fila,
            'resposta': self.resposta,
            'etapa': 'clarificando_variante'
            if self.fila
            else 'coletando',  # ← adiciona
        }


def _calcular_preco(item: dict, item_data: dict) -> int | None:
    """Calcula o preço total de um item considerando quantidade e variantes.

    Args:
        item: Dicionário do item extraído com ``quantidade`` e opcional ``variante``.
        item_data: Dados completos do item do cardápio.

    Returns:
        Preço total em centavos ou None se não foi possível calcular.
    """
    preco_base = get_preco_item(item['item_id'])
    variante = item.get('variante')
    quantidade = item['quantidade']

    if preco_base is not None:
        return preco_base * quantidade

    variantes_validas = get_variantes(item['item_id'])
    if variante and variante in variantes_validas:
        variante_obj = next(v for v in item_data['variantes'] if v['opcao'] == variante)
        return variante_obj['preco'] * quantidade

    return None


def processar(
    itens_extraidos: list[dict],
    carrinho_existente: list[dict],
) -> ResultadoPedir:
    """Processa itens extraídos e os adiciona ao carrinho.

    Para cada item extraído, verifica se possui preço fixo ou variantes.
    Itens com variantes inválidas ou não especificadas vão para a fila
    de clarificação.

    Args:
        itens_extraidos: Lista de itens extraídos da mensagem.
        carrinho_existente: Carrinho atual do estado (para mesclar).

    Returns:
        ResultadoPedir com carrinho, fila e resposta atualizados.
    """
    carrinho = list(carrinho_existente)
    fila: list[dict] = []
    itens_adicionados: list[tuple[str, int, int]] = []

    for item in itens_extraidos:
        item_data = get_item_por_id(item['item_id'])
        if item_data is None:
            continue

        preco_total = _calcular_preco(item, item_data)

        if preco_total is not None:
            item_formatado = dict(item)
            item_formatado['preco'] = preco_total
            carrinho.append(item_formatado)
            itens_adicionados.append(
                (
                    item_data['nome'],
                    item_formatado['quantidade'],
                    item_formatado['preco'],
                )
            )
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
        resposta = f'{proxima["nome"]}: qual opção? {opcoes}'
    elif itens_adicionados:
        resposta = formatar_carrinho(carrinho)
    else:
        resposta = ''

    return ResultadoPedir(
        carrinho=carrinho,
        fila=fila,
        resposta=resposta,
    )
