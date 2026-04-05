"""Handler de troca de variantes de itens do carrinho.

Extrai itens e variantes mencionados na mensagem e troca a variante
de itens existentes no carrinho, recalculando o preco.

Example:
    ```python
    from src.graph.handlers.trocar import processar_troca

    carrinho = [
        {
            'item_id': 'lanche_001',
            'quantidade': 1,
            'preco': 1500,
            'variante': 'simples',
        },
    ]
    result = processar_troca(carrinho, 'muda pra duplo')
    result.carrinho[0]['variante']
    'duplo'
    ```
"""

from dataclasses import dataclass, field

from src.config import get_item_por_id, get_nome_item, get_preco_item
from src.extratores import extrair, extrair_itens_troca, normalizar
from src.graph.handlers.utils import formatar_carrinho
from src.graph.state import ETAPAS, RetornoNode


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
    etapa: ETAPAS = 'carrinho'

    def to_dict(self) -> RetornoNode:
        """Converte para dicionario compativel com LangGraph State."""
        return {
            'carrinho': self.carrinho,
            'resposta': self.resposta,
            'etapa': self.etapa,
        }


def _calcular_preco_variante(
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
    preco_base = get_preco_item(item_id)
    if preco_base is not None:
        return preco_base * quantidade

    item_data = get_item_por_id(item_id)
    if not item_data:
        return None

    variante_obj = next(
        (v for v in item_data.get('variantes', []) if v['opcao'] == variante),
        None,
    )
    return variante_obj['preco'] * quantidade if variante_obj else None


def _extrair_primeiro_item_da_mensagem(mensagem: str) -> str:
    """Extrai o texto do primeiro ITEM mencionado na mensagem.

    Usado como fallback quando o extrator nao encontra o item no carrinho
    (caso B com item_original None), para dar feedback mais informativo
    sobre qual item o usuario tentou trocar.

    Args:
        mensagem: Mensagem original do usuario.

    Returns:
        Texto do primeiro ITEM encontrado, ou 'item' como fallback.
    """
    itens = extrair(mensagem)
    if itens:
        return normalizar(itens[0].get('item_id', 'item'))
    return 'item'


def _variante_eh_valida(item_id: str, variante: str) -> bool:
    """Verifica se uma variante existe para um determinado item.

    Args:
        item_id: ID do item no cardapio.
        variante: Nome da variante a verificar.

    Returns:
        True se a variante existe, False caso contrario.
    """
    item_data = get_item_por_id(item_id)
    if not item_data:
        return False
    variantes_validas = [v['opcao'] for v in item_data.get('variantes', [])]
    return variante in variantes_validas


def processar_troca(
    carrinho: list[dict],
    mensagem: str,
) -> ResultadoTrocar:
    """Processa troca de variantes de itens no carrinho.

    Extrai o item original e a nova variante da mensagem, verifica
    compatibilidade, recalcula o preco e substitui no carrinho.

    Args:
        carrinho: Carrinho atual do estado.
        mensagem: Mensagem do usuario com o pedido de troca.

    Returns:
        ResultadoTrocar com carrinho, resposta e etapa atualizados.

    Note:
        MVP (Fase 1):
        - Caso B: 1 ITEM + variante (troca variante de item existente)
        - Caso C: 0 ITEMs + 1 VARIANTE isolada (inferencia pelo carrinho)
        - Caso A: troca item por item diferente -> resposta informativa (Fase 2)
        - Ambiguidade: resposta direta sem estado extra
        TODO (Fase 2):
        - Caso A: troca item por item diferente com validacao de cardapio
        - Clarificacao de trocas com estado (etapa='clarificando_troca')
        - Merge de complementos e remocoes na troca
    """
    if not carrinho:
        return ResultadoTrocar(
            resposta='Não há pedido para trocar.',
            etapa='inicio',
        )

    extracao = extrair_itens_troca(mensagem, carrinho)
    caso = extracao['caso']
    item_original = extracao['item_original']
    variante_nova = extracao['variante_nova']

    # Caso vazio: nenhuma entidade relevante encontrada
    if caso == 'vazio':
        return ResultadoTrocar(
            carrinho=carrinho,
            resposta="Não entendi o que quer trocar. Ex: 'muda pra duplo'",
        )

    # Caso A: 2+ ITEMs (troca item por item) — Fase 2
    if caso == 'A':
        return ResultadoTrocar(
            carrinho=carrinho,
            resposta="Por enquanto só consigo trocar variantes. Ex: 'muda pra duplo'",
        )

    # Caso B: 1 ITEM + variante opcional
    if caso == 'B':
        nome_item_mencionado = None
        if item_original is None:
            nome_item_mencionado = _extrair_primeiro_item_da_mensagem(mensagem)
        return _processar_caso_b(
            carrinho, item_original, variante_nova, nome_item_mencionado
        )

    # Caso C: 0 ITEMs + 1 VARIANTE isolada
    if caso == 'C':
        return _processar_caso_c(carrinho, variante_nova)

    # Fallback defensivo
    return ResultadoTrocar(
        carrinho=carrinho,
        resposta="Não entendi o que quer trocar. Ex: 'muda pra duplo'",
    )


def _processar_caso_b(
    carrinho: list[dict],
    item_original: dict | None,
    variante_nova: str | None,
    nome_item_mencionado: str | None = None,
) -> ResultadoTrocar:
    """Processa troca no caso B: 1 ITEM + variante opcional.

    Args:
        carrinho: Carrinho atual do estado.
        item_original: Dados do item encontrado no carrinho, ou None.
        variante_nova: Nome da nova variante, ou None.
        nome_item_mencionado: Nome do item extraido da mensagem (usado
            quando item_original e None para feedback ao usuario).

    Returns:
        ResultadoTrocar com o resultado do processamento.
    """
    # Item nao encontrado no carrinho
    if item_original is None:
        nome = nome_item_mencionado or 'item'
        return ResultadoTrocar(
            carrinho=carrinho,
            resposta=f"'{nome}' não está no seu carrinho.",
        )

    # Variante não mencionada
    if variante_nova is None:
        nome_item = get_nome_item(item_original['item_id']) or item_original['item_id']
        return ResultadoTrocar(
            carrinho=carrinho,
            resposta=f"Mudar '{nome_item}' pra... o quê? Ex: 'muda pra duplo'",
        )

    # Verificar se a variante é válida para o item
    item_id = item_original['item_id']
    if not _variante_eh_valida(item_id, variante_nova):
        nome_item = get_nome_item(item_id) or item_id
        return ResultadoTrocar(
            carrinho=carrinho,
            resposta=f"'{nome_item}' não tem opção '{variante_nova}'.",
        )

    # Calcular novo preco e substituir itens
    carrinho_atualizado = list(carrinho)
    for indice in item_original['indices']:
        item_antigo = carrinho_atualizado[indice]
        quantidade = item_antigo.get('quantidade', 1)
        novo_preco = _calcular_preco_variante(item_id, variante_nova, quantidade)

        if novo_preco is None:
            # Erro defensivo: não deveria acontecer pois já validamos
            nome_item = get_nome_item(item_id) or item_id
            return ResultadoTrocar(
                carrinho=carrinho,
                resposta=f"Não foi possível calcular o preço para '{nome_item}'.",
            )

        carrinho_atualizado[indice] = {
            **item_antigo,
            'variante': variante_nova,
            'preco': novo_preco,
        }

    resposta = formatar_carrinho(carrinho_atualizado)
    return ResultadoTrocar(
        carrinho=carrinho_atualizado,
        resposta=resposta,
    )


def _processar_caso_c(
    carrinho: list[dict],
    variante_nova: str | None,
) -> ResultadoTrocar:
    """Processa troca no caso C: 0 ITEMs + 1 VARIANTE isolada.

    Args:
        carrinho: Carrinho atual do estado.
        variante_nova: Nome da variante isolada, ou None.

    Returns:
        ResultadoTrocar com o resultado do processamento.
    """
    # Defensivo: variante não deveria ser None no caso C
    if variante_nova is None:
        return ResultadoTrocar(
            carrinho=carrinho,
            resposta="Não entendi. Ex: 'muda pra duplo'",
        )

    # Detectar compatibilidade: itens do carrinho que aceitam essa variante
    compativeis: list[tuple[int, dict]] = []
    for idx, item in enumerate(carrinho):
        item_data = get_item_por_id(item['item_id'])
        if not item_data:
            continue
        variantes_validas = [v['opcao'] for v in item_data.get('variantes', [])]
        if variante_nova in variantes_validas:
            compativeis.append((idx, item))

    # Ambiguidade: 2+ itens compatíveis
    if len(compativeis) >= 2:
        nomes = [
            get_nome_item(item['item_id']) or item['item_id'] for _, item in compativeis
        ]
        nomes_str = ' ou '.join(nomes)
        return ResultadoTrocar(
            carrinho=carrinho,
            resposta=f'Qual item? {nomes_str}?',
        )

    # Troca direta: 1 item compatível
    if len(compativeis) == 1:
        idx, item = compativeis[0]
        return _substituir_item_no_carrinho(carrinho, idx, item, variante_nova)

    # Fallback: 0 compativeis
    return _processar_caso_c_fallback(carrinho, variante_nova)


def _processar_caso_c_fallback(
    carrinho: list[dict],
    variante_nova: str,
) -> ResultadoTrocar:
    """Processa fallback do caso C quando nenhum item eh compativel.

    Se o carrinho tem 1 unico item, tenta aplicar a variante nele.
    Caso contrario, informa que nenhum item aceita a variante.

    Args:
        carrinho: Carrinho atual do estado.
        variante_nova: Nome da variante a aplicar.

    Returns:
        ResultadoTrocar com o resultado do processamento.
    """
    if len(carrinho) == 1:
        idx = 0
        item = carrinho[0]
        if _variante_eh_valida(item['item_id'], variante_nova):
            return _substituir_item_no_carrinho(carrinho, idx, item, variante_nova)
        nome_item = get_nome_item(item['item_id']) or item['item_id']
        return ResultadoTrocar(
            carrinho=carrinho,
            resposta=f"'{nome_item}' não tem opção '{variante_nova}'.",
        )

    return ResultadoTrocar(
        carrinho=carrinho,
        resposta=f"Nenhum item no seu carrinho aceita a variante '{variante_nova}'.",
    )


def _substituir_item_no_carrinho(
    carrinho: list[dict],
    indice: int,
    item: dict,
    variante_nova: str,
) -> ResultadoTrocar:
    """Substitui a variante de um item no carrinho e recalcula o preco.

    Args:
        carrinho: Carrinho atual do estado.
        indice: Posicao do item no carrinho a substituir.
        item: Dados do item a modificar.
        variante_nova: Nome da nova variante.

    Returns:
        ResultadoTrocar com carrinho atualizado e resposta formatada.
    """
    item_id = item['item_id']
    quantidade = item.get('quantidade', 1)
    novo_preco = _calcular_preco_variante(item_id, variante_nova, quantidade)

    if novo_preco is None:
        nome_item = get_nome_item(item_id) or item_id
        return ResultadoTrocar(
            carrinho=carrinho,
            resposta=f"Não foi possível calcular o preço para '{nome_item}'.",
        )

    carrinho_atualizado = list(carrinho)
    carrinho_atualizado[indice] = {
        **item,
        'variante': variante_nova,
        'preco': novo_preco,
    }

    resposta = formatar_carrinho(carrinho_atualizado)
    return ResultadoTrocar(
        carrinho=carrinho_atualizado,
        resposta=resposta,
    )
