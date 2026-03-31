"""Nós de processamento do grafo de atendimento.

Cada função representa um nó no grafo LangGraph, recebendo e
retornando atualizações parciais do estado.

Example:
    >>> from src.graph.nodes import node_handler_saudacao
    >>> state = {'mensagem_atual': 'oi', 'intent': 'saudacao', 'itens_extraidos': [], 'carrinho': [], 'fila_clarificacao': [], 'etapa': 'inicio', 'resposta': ''}
    >>> result = node_handler_saudacao(state)
    >>> 'resposta' in result
    True
"""

from src.config import get_item_por_id, get_nome_item, get_tenant_nome
from src.extratores import extrair
from src.graph.handlers.clarificacao import clarificar
from src.graph.handlers.pedir import processar as processar_pedido
from src.graph.state import State
from src.roteador import classificar_intencao


def node_router(state: State) -> dict:
    """Classifica a intenção da mensagem e atualiza o estado.

    Nó de roteamento que envia a mensagem atual para o classificador
    de intenções e armazena o resultado no estado.

    Args:
        state: Estado atual do grafo de atendimento.

    Returns:
        Dicionário com a chave ``intent`` atualizada.

    Example:
        >>> state = {'mensagem_atual': 'oi', 'intent': '', 'itens_extraidos': [], 'carrinho': [], 'fila_clarificacao': [], 'etapa': 'inicio', 'resposta': ''}
        >>> result = node_router(state)
        >>> 'intent' in result
        True
    """
    intent = classificar_intencao(state.get('mensagem_atual', ''))
    return {'intent': intent}


def node_extrator(state: State) -> dict:
    """Extrai itens do cardápio da mensagem do usuário.

    Nó de extração que processa a mensagem com o extrator spaCy
    apenas quando a intenção é ``pedir``.

    Args:
        state: Estado atual do grafo de atendimento.

    Returns:
        Dicionário com a chave ``itens_extraidos`` atualizada.
        Lista vazia se a intenção não for ``pedir``.
    """
    if state.get('intent') == 'pedir':
        return {'itens_extraidos': extrair(state.get('mensagem_atual', ''))}
    return {'itens_extraidos': []}


def node_handler_pedir(state: State) -> dict:
    """Processa itens extraídos e os adiciona ao carrinho.

    Para cada item extraído, verifica se possui preço fixo ou variantes.
    Itens com variantes inválidas vão para a fila de clarificação.

    Args:
        state: Estado atual do grafo de atendimento.

    Returns:
        Dicionário com ``carrinho``, ``fila_clarificacao`` e ``resposta``
        atualizados.
    """
    itens_extraidos = state.get('itens_extraidos') or []
    carrinho = state.get('carrinho', [])
    resultado = processar_pedido(itens_extraidos, carrinho)
    return resultado.to_dict()


def node_handler_saudacao(state: State) -> dict:
    """Gera resposta de saudação com o nome do restaurante.

    Args:
        state: Estado atual do grafo de atendimento.

    Returns:
        Dicionário com ``resposta`` e ``etapa`` atualizados.
    """
    nome_restaurante = get_tenant_nome()
    resposta = f'Ola! Seja bem-vindo(a) a {nome_restaurante}!\nComo posso ajudar?'
    return {'resposta': resposta, 'etapa': 'saudacao'}


def node_handler_carrinho(state: State) -> dict:
    """Gera resposta com o conteúdo atual do carrinho.

    Lista todos os itens no carrinho com quantidades e preços,
    além do total.

    Args:
        state: Estado atual do grafo de atendimento.

    Returns:
        Dicionário com ``resposta`` e ``etapa`` atualizados.
        Retorna mensagem de carrinho vazio se não houver itens.
    """
    carrinho = state.get('carrinho', [])
    if not carrinho:
        return {'resposta': 'Seu carrinho está vazio!', 'etapa': 'carrinho'}
    linhas = []
    total = 0
    for item in carrinho:
        nome = get_nome_item(item['item_id']) or item['item_id']
        preco = item['preco']
        linhas.append(f'{item["quantidade"]}x {nome} - R$ {preco / 100:.2f}')
        total += preco
    resposta = 'Seu pedido:\n' + '\n'.join(linhas) + f'\nTotal: R$ {total / 100:.2f}'
    return {'resposta': resposta, 'etapa': 'carrinho'}


def node_handler_confirmar(state: State) -> dict:
    """Processa confirmação do usuário.

    Dependendo da etapa atual, confirma uma variante,
    finaliza o pedido com o total ou lida com tentativas
    de clarificação inválidas.

    Args:
        state: Estado atual do grafo de atendimento.

    Returns:
        Dicionário com ``resposta`` e opcionalmente ``etapa``,
        ``carrinho``, ``fila_clarificacao`` e ``tentativas_clarificacao``
        atualizados.
    """
    etapa = state.get('etapa', '')
    carrinho = state.get('carrinho', [])

    match etapa:
        case 'clarificando_variante':
            resultado = clarificar(
                fila=state.get('fila_clarificacao', []),
                mensagem=state.get('mensagem_atual', ''),
                tentativas=state.get('tentativas_clarificacao', 0),
            )
            # Mesclar carrinho existente com novo carrinho do handler
            carrinho_atualizado = carrinho + resultado.carrinho
            return {**resultado.to_dict(), 'carrinho': carrinho_atualizado}
        case _:
            if carrinho:
                total = sum(item.get('preco', 0) for item in carrinho)
                resposta = f"Pedido confirmado! Total: R$ {total/100:.2f}"
                return {'resposta': resposta, 'etapa': 'finalizado'}

            return {'resposta': 'Não tenho nada no carrinho para confirmar.'}


def node_handler_cancelar(state: State) -> dict:
    """Processa cancelamento do pedido.

    Args:
        state: Estado atual do grafo de atendimento.

    Returns:
        Dicionário vazio (a ser implementado).
    """
    ...
