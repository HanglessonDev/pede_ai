"""Handler de troca de variantes de itens do carrinho.

Extrai itens e variantes mencionados na mensagem e troca a variante
de itens existentes no carrinho, recalculando o preco.

Example:
    ```python
    from src.graph.handlers.troca_handler import processar_troca

    carrinho_dicts = [
        {
            'item_id': 'lanche_001',
            'quantidade': 1,
            'preco': 1500,
            'variante': 'simples',
        },
    ]
    result = processar_troca(carrinho_dicts, 'muda pra duplo')
    result.carrinho[0]['variante']
    'duplo'
    ```
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.config import get_item_por_id, get_nome_item
from src.extratores import extrair, extrair_itens_troca, normalizar
from src.graph.handlers.carrinho import Carrinho, CarrinhoItem
from src.graph.state import MODOS, RetornoNode


@dataclass
class ResultadoTrocar:
    """Resultado do processamento de troca.

    Attributes:
        carrinho: Carrinho atualizado apos troca.
        resposta: Texto formatado para o usuario.
        etapa: Proxima etapa do fluxo.
    """

    carrinho: list[dict] = field(default_factory=list)
    resposta: str = ''
    modo: MODOS = 'coletando'

    def to_dict(self) -> RetornoNode:
        """Converte para dicionario compativel com LangGraph State."""
        return {
            'carrinho': self.carrinho,
            'resposta': self.resposta,
            'modo': self.modo,
        }


def _calcular_preco_item(
    item_id: str,
    variante: str | None,
    quantidade: int,
) -> int | None:
    """Calcula o preco total de um item considerando variante e quantidade.

    Args:
        item_id: ID do item no cardapio.
        variante: Nome da variante (ou None para preco fixo).
        quantidade: Quantidade do item.

    Returns:
        Preco total em centavos, ou None se nao foi possivel calcular.
    """
    item_data = get_item_por_id(item_id)
    if not item_data:
        return None

    preco_base = item_data.get('preco')
    if preco_base is not None:
        return preco_base * quantidade

    variante_obj = next(
        (v for v in item_data.get('variantes', []) if v['opcao'] == variante),
        None,
    )
    return variante_obj['preco'] * quantidade if variante_obj else None


def _extrair_primeiro_item_da_mensagem(mensagem: str) -> str:
    """Extrai o texto do primeiro ITEM mencionado na mensagem."""
    itens = extrair(mensagem)
    if itens:
        return normalizar(itens[0].get('item_id', 'item'))
    return 'item'


def processar_troca(
    carrinho_dicts: list[dict],
    mensagem: str,
) -> ResultadoTrocar:
    """Processa troca de variantes de itens no carrinho."""
    if not carrinho_dicts:
        return ResultadoTrocar(
            resposta='Não há pedido para trocar.',
            modo='ocioso',
        )

    extracao = extrair_itens_troca(mensagem, carrinho_dicts)
    caso = extracao['caso']
    item_original = extracao['item_original']
    variante_nova = extracao['variante_nova']

    if caso == 'vazio':
        return ResultadoTrocar(
            carrinho=carrinho_dicts,
            resposta="Não entendi o que quer trocar. Ex: 'muda pra duplo'",
        )

    if caso == 'A':
        return ResultadoTrocar(
            carrinho=carrinho_dicts,
            resposta="Por enquanto só consigo trocar variantes. Ex: 'muda pra duplo'",
        )

    if caso == 'B':
        nome_item_mencionado = None
        if item_original is None:
            nome_item_mencionado = _extrair_primeiro_item_da_mensagem(mensagem)
        return _processar_caso_b(
            carrinho_dicts, item_original, variante_nova, nome_item_mencionado
        )

    if caso == 'C':
        return _processar_caso_c(carrinho_dicts, variante_nova)

    return ResultadoTrocar(
        carrinho=carrinho_dicts,
        resposta="Não entendi o que quer trocar. Ex: 'muda pra duplo'",
    )


def _processar_caso_b(
    carrinho_dicts: list[dict],
    item_original: dict | None,
    variante_nova: str | None,
    nome_item_mencionado: str | None = None,
) -> ResultadoTrocar:
    """Processa troca no caso B: 1 ITEM + variante opcional."""
    if item_original is None:
        nome = nome_item_mencionado or 'item'
        return ResultadoTrocar(
            carrinho=carrinho_dicts,
            resposta=f"'{nome}' não está no seu carrinho.",
        )

    if variante_nova is None:
        nome_item = get_nome_item(item_original['item_id']) or item_original['item_id']
        return ResultadoTrocar(
            carrinho=carrinho_dicts,
            resposta=f"Mudar '{nome_item}' pra... o quê? Ex: 'muda pra duplo'",
        )

    item_id = item_original['item_id']
    item_data = get_item_por_id(item_id)
    if not item_data:
        return ResultadoTrocar(
            carrinho=carrinho_dicts,
            resposta=f"'{item_id}' não encontrado no cardápio.",
        )

    variantes_validas = [v['opcao'] for v in item_data.get('variantes', [])]
    if variante_nova not in variantes_validas:
        nome_item = get_nome_item(item_id) or item_id
        return ResultadoTrocar(
            carrinho=carrinho_dicts,
            resposta=f"'{nome_item}' não tem opção '{variante_nova}'.",
        )

    carrinho = Carrinho.from_state_dicts(carrinho_dicts)
    for indice in item_original['indices']:
        if indice >= len(carrinho.itens):
            continue
        item_antigo = carrinho.itens[indice]
        novo_preco = _calcular_preco_item(
            item_id, variante_nova, item_antigo.quantidade
        )
        if novo_preco is None:
            nome_item = get_nome_item(item_id) or item_id
            return ResultadoTrocar(
                carrinho=carrinho_dicts,
                resposta=f"Não foi possível calcular o preço para '{nome_item}'.",
            )
        carrinho.itens[indice] = CarrinhoItem(
            item_id=item_antigo.item_id,
            quantidade=item_antigo.quantidade,
            preco_centavos=novo_preco,
            variante=variante_nova,
        )

    return ResultadoTrocar(
        carrinho=carrinho.to_state_dicts(),
        resposta=carrinho.formatar(),
    )


def _processar_caso_c(
    carrinho_dicts: list[dict],
    variante_nova: str | None,
) -> ResultadoTrocar:
    """Processa troca no caso C: 0 ITEMs + 1 VARIANTE isolada."""
    if variante_nova is None:
        return ResultadoTrocar(
            carrinho=carrinho_dicts,
            resposta="Não entendi. Ex: 'muda pra duplo'",
        )

    compativeis: list[tuple[int, dict]] = []
    for idx, item_dict in enumerate(carrinho_dicts):
        item_data = get_item_por_id(item_dict['item_id'])
        if not item_data:
            continue
        variantes_validas = [v['opcao'] for v in item_data.get('variantes', [])]
        if variante_nova in variantes_validas:
            compativeis.append((idx, item_dict))

    if len(compativeis) >= 2:
        nomes = [
            get_nome_item(item['item_id']) or item['item_id'] for _, item in compativeis
        ]
        return ResultadoTrocar(
            carrinho=carrinho_dicts,
            resposta=f'Qual item? {" ou ".join(nomes)}?',
        )

    if len(compativeis) == 1:
        idx, item_dict = compativeis[0]
        return _substituir_no_carrinho(carrinho_dicts, idx, item_dict, variante_nova)

    # Fallback: 0 compativeis
    if len(carrinho_dicts) == 1:
        item_dict = carrinho_dicts[0]
        if _variante_valida(item_dict['item_id'], variante_nova):
            return _substituir_no_carrinho(carrinho_dicts, 0, item_dict, variante_nova)
        nome_item = get_nome_item(item_dict['item_id']) or item_dict['item_id']
        return ResultadoTrocar(
            carrinho=carrinho_dicts,
            resposta=f"'{nome_item}' não tem opção '{variante_nova}'.",
        )

    return ResultadoTrocar(
        carrinho=carrinho_dicts,
        resposta=f"Nenhum item no seu carrinho aceita a variante '{variante_nova}'.",
    )


def _substituir_no_carrinho(
    carrinho_dicts: list[dict],
    indice: int,
    item_dict: dict,
    variante_nova: str,
) -> ResultadoTrocar:
    """Substitui a variante de um item no carrinho e recalcula o preco."""
    item_id = item_dict['item_id']
    quantidade = item_dict.get('quantidade', 1)
    novo_preco = _calcular_preco_item(item_id, variante_nova, quantidade)

    if novo_preco is None:
        nome_item = get_nome_item(item_id) or item_id
        return ResultadoTrocar(
            carrinho=carrinho_dicts,
            resposta=f"Não foi possível calcular o preço para '{nome_item}'.",
        )

    carrinho = Carrinho.from_state_dicts(carrinho_dicts)
    carrinho.itens[indice] = CarrinhoItem(
        item_id=item_dict['item_id'],
        quantidade=quantidade,
        preco_centavos=novo_preco,
        variante=variante_nova,
    )

    return ResultadoTrocar(
        carrinho=carrinho.to_state_dicts(),
        resposta=carrinho.formatar(),
    )


def _variante_valida(item_id: str, variante: str) -> bool:
    """Verifica se uma variante existe para um determinado item."""
    item_data = get_item_por_id(item_id)
    if not item_data:
        return False
    variantes_validas = [v['opcao'] for v in item_data.get('variantes', [])]
    return variante in variantes_validas
