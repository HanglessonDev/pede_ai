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

from src.config import get_item_por_id, get_nome_item, get_preco_item, get_tenant_nome, get_variantes
from src.extratores import extrair, extrair_variante
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


def _calcular_preco_item(item: dict, item_data: dict) -> int | None:
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
        variante_obj = next(
            v for v in item_data['variantes'] if v['opcao'] == variante
        )
        return variante_obj['preco'] * quantidade

    return None


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
    fila = state.get('fila_clarificacao', [])
    itens_adicionados = []

    for item in itens_extraidos:
        item_data = get_item_por_id(item['item_id'])
        if item_data is None:
            continue

        preco_total = _calcular_preco_item(item, item_data)

        if preco_total is not None:
            item['preco'] = preco_total
            carrinho.append(item)
            itens_adicionados.append(
                (item_data['nome'], item['quantidade'], item['preco'])
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
    else:
        linhas = [
            f'{qtd}x {nome} — R$ {preco / 100:.2f}'
            for nome, qtd, preco in itens_adicionados
        ]
        resposta = '\n'.join(linhas)

    return {
        'carrinho': carrinho,
        'fila_clarificacao': fila,
        'resposta': resposta,
    }


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
            return _processar_clarificacao(state)
        case _:
            if carrinho:
                total = sum(item.get('preco', 0) for item in carrinho)
                resposta = f"Pedido confirmado! Total: R$ {total/100:.2f}"
                return {'resposta': resposta, 'etapa': 'finalizado'}

            return {'resposta': 'Não tenho nada no carrinho para confirmar.'}


def _processar_clarificacao(state: State) -> dict:
    """Processa a resposta do usuário durante clarificação de variante.

    Tenta extrair uma variante válida da mensagem. Se válida,
    calcula o preço e adiciona ao carrinho. Se inválida, incrementa
    o contador de tentativas e faz re-prompt (até 3 tentativas).

    Args:
        state: Estado atual do grafo de atendimento.

    Returns:
        Dicionário com estado atualizado.
    """
    fila = list(state.get('fila_clarificacao', []))
    carrinho = list(state.get('carrinho', []))
    tentativas = state.get('tentativas_clarificacao', 0)
    mensagem = state.get('mensagem_atual', '')

    if not fila:
        return {'resposta': '', 'etapa': 'inicio'}

    item_fila = fila[0]
    item_id = item_fila['item_id']
    nome = item_fila['nome']
    opcoes = item_fila['opcoes']
    item_dados = item_fila['item']

    variante = extrair_variante(mensagem, item_id)

    if variante is not None:
        # Variante válida: calcula preço e adiciona ao carrinho
        item_data = get_item_por_id(item_id)
        if item_data is None:
            fila.pop(0)
            return {
                'fila_clarificacao': fila,
                'tentativas_clarificacao': 0,
                'resposta': 'Erro ao processar item.',
                'etapa': 'inicio' if not fila else 'clarificando_variante',
            }

        variante_obj = next(
            (v for v in item_data.get('variantes', []) if v['opcao'] == variante),
            None,
        )
        if variante_obj is None:
            fila.pop(0)
            return {
                'fila_clarificacao': fila,
                'tentativas_clarificacao': 0,
                'resposta': 'Erro ao processar variante.',
                'etapa': 'inicio' if not fila else 'clarificando_variante',
            }

        preco_total = variante_obj['preco'] * item_dados['quantidade']
        item_dados['variante'] = variante
        item_dados['preco'] = preco_total
        carrinho.append(item_dados)

        fila.pop(0)
        tentativas = 0

        if fila:
            proxima = fila[0]
            opcoes_str = ', '.join(proxima['opcoes'])
            resposta = f'{proxima["nome"]}: qual opção? {opcoes_str}'
        else:
            linhas = [
                f'{it["quantidade"]}x {get_nome_item(it["item_id"]) or it["item_id"]} — R$ {it["preco"] / 100:.2f}'
                for it in carrinho
            ]
            resposta = '\n'.join(linhas)

        return {
            'carrinho': carrinho,
            'fila_clarificacao': fila,
            'tentativas_clarificacao': tentativas,
            'resposta': resposta,
            'etapa': 'inicio' if not fila else 'clarificando_variante',
        }

    # Variante inválida: incrementa tentativas
    tentativas += 1

    if tentativas >= 3:
        # Desistiu: remove item da fila
        fila.pop(0)
        tentativas = 0
        if fila:
            proxima = fila[0]
            opcoes_str = ', '.join(proxima['opcoes'])
            resposta = f'Não consegui entender. {proxima["nome"]}: qual opção? {opcoes_str}'
            return {
                'fila_clarificacao': fila,
                'tentativas_clarificacao': tentativas,
                'resposta': resposta,
                'etapa': 'clarificando_variante',
            }
        return {
            'fila_clarificacao': fila,
            'tentativas_clarificacao': tentativas,
            'resposta': 'Não consegui entender a opção. Vamos continuar com o pedido.',
            'etapa': 'inicio',
        }

    # Re-prompt
    opcoes_str = ', '.join(opcoes)
    resposta = f'Essa opção não está disponível. {nome}: {opcoes_str}?'
    return {
        'fila_clarificacao': fila,
        'tentativas_clarificacao': tentativas,
        'resposta': resposta,
        'etapa': 'clarificando_variante',
    }


def node_handler_cancelar(state: State) -> dict:
    """Processa cancelamento do pedido.

    Args:
        state: Estado atual do grafo de atendimento.

    Returns:
        Dicionário vazio (a ser implementado).
    """
    ...
