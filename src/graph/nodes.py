"""Nós de processamento do grafo de atendimento.

Cada função representa um nó no grafo LangGraph, recebendo e
retornando atualizações parciais do estado.

Example:
    ```python
    from src.graph.nodes import node_handler_saudacao

    state = {
        'mensagem_atual': 'oi',
        'intent': 'saudacao',
        'itens_extraidos': [],
        'carrinho': [],
        'fila_clarificacao': [],
        'etapa': 'inicio',
        'resposta': '',
    }
    result = node_handler_saudacao(state)
    'resposta' in result
    True
    ```
"""

from src.config import get_nome_item, get_tenant_nome
from src.extratores import extrair, extrair_item_carrinho
from src.graph.handlers.clarificacao import clarificar
from src.graph.handlers.pedir import processar as processar_pedido
from src.graph.state import RetornoNode, State
from src.observabilidade.registry import get_obs_logger
from src.roteador.classificador_intencoes import _classificar_intencao


def node_verificar_etapa(state: State) -> RetornoNode:
    """Nó de verificação de etapa do fluxo.

    Apenas passa adiante sem modificar o estado. A decisão
    de qual caminho seguir é feita pela edge condicional
    ``_decidir_entrada`` no builder.

    Args:
        state: Estado atual do grafo de atendimento.

    Returns:
        Dicionário vazio - apenas passa adiante sem modificar o estado.
    """
    return {}  # não faz nada, só passa adiante


def node_router(state: State) -> RetornoNode:
    """Classifica a intenção da mensagem e atualiza o estado.

    Nó de roteamento que envia a mensagem atual para o classificador
    de intenções e armazena o resultado no estado.

    Args:
        state: Estado atual do grafo de atendimento.

    Returns:
        Dicionário com ``intent`` e ``confidence`` atualizados.

    Example:
        ```python
        state = {
            'mensagem_atual': 'oi',
            'intent': '',
            'itens_extraidos': [],
            'carrinho': [],
            'fila_clarificacao': [],
            'etapa': 'inicio',
            'resposta': '',
        }
        result = node_router(state)
        'intent' in result
        True
        ```
    """
    mensagem = state.get('mensagem_atual', '')
    thread_id = state.get('config', {}).get('configurable', {}).get('thread_id', '')

    resultado = _classificar_intencao(mensagem, thread_id=thread_id)

    # Registra evento de observabilidade
    obs_logger = get_obs_logger()
    obs_logger.registrar(
        thread_id=thread_id,
        mensagem=mensagem,
        mensagem_norm=resultado['mensagem_norm'],
        intent=resultado['intent'],
        confidence=resultado['confidence'],
        caminho=resultado['caminho'],
        top1_texto=resultado['top1_texto'],
        top1_intencao=resultado['top1_intencao'],
    )

    return {
        'intent': resultado['intent'],
        'confidence': resultado['confidence'],
    }


def node_clarificacao(state: State) -> RetornoNode:
    thread_id = state.get('config', {}).get('configurable', {}).get('thread_id', '')
    resultado = clarificar(
        fila=state.get('fila_clarificacao', []),
        mensagem=state.get('mensagem_atual', ''),
        tentativas=state.get('tentativas_clarificacao', 0),
        thread_id=thread_id,
    )
    carrinho_atualizado = state.get('carrinho', []) + resultado.carrinho
    return {
        'carrinho': carrinho_atualizado,
        'fila_clarificacao': resultado.fila,
        'resposta': resultado.resposta,
        'etapa': resultado.etapa,
    }


def node_extrator(state: State) -> RetornoNode:
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


def node_handler_pedir(state: State) -> RetornoNode:
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


def node_handler_saudacao(state: State) -> RetornoNode:
    """Gera resposta de saudação com o nome do restaurante.

    Args:
        state: Estado atual do grafo de atendimento.

    Returns:
        Dicionário com ``resposta`` e ``etapa`` atualizados.
    """
    nome_restaurante = get_tenant_nome()
    resposta = f'Ola! Seja bem-vindo(a) a {nome_restaurante}!\nComo posso ajudar?'
    return {'resposta': resposta, 'etapa': 'saudacao'}


def node_handler_carrinho(state: State) -> RetornoNode:
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


def node_handler_confirmar(state: State) -> RetornoNode:
    carrinho = state.get('carrinho', [])
    if not carrinho:
        return {'resposta': 'Não há pedido para confirmar.'}
    total = sum(item.get('preco', 0) for item in carrinho)
    return {
        'resposta': f'Pedido confirmado! Total: R$ {total / 100:.2f}',
        'etapa': 'finalizado',
        'carrinho': [],  # limpa carrinho após confirmar
    }


def node_handler_cancelar(state: State) -> RetornoNode:
    """Processa cancelamento do pedido.

    Args:
        state: Estado atual do grafo de atendimento.

    Returns:
        Dicionário com ``resposta``, ``etapa`` e ``carrinho`` atualizados.
        Retorna mensagem de carrinho vazio se não houver itens.
    """
    carrinho = state.get('carrinho', [])
    if not carrinho:
        return {'resposta': 'Não há pedido para cancelar.', 'etapa': 'inicio'}

    total = sum(item.get('preco', 0) for item in carrinho)
    return {
        'resposta': f'Pedido cancelado. Total descartado: R$ {total / 100:.2f}',
        'etapa': 'inicio',
        'carrinho': [],
        'fila_clarificacao': [],
        'tentativas_clarificacao': 0,
    }


def node_handler_remover(state: State) -> RetornoNode:
    """Processa remoção de itens do pedido.

    Extrai os itens mencionados na mensagem e remove do carrinho.
    Suporta remoção por nome do item e por variante específica.

    Args:
        state: Estado atual do grafo de atendimento.

    Returns:
        Dicionário com ``resposta``, ``etapa`` e ``carrinho`` atualizados.
        Retorna mensagem de erro se não encontrar itens para remover.

    Note:
        MVP (Fase 1):
        - Remove TODOS os matches (ignora quantidade)
        - Match parcial por nome
        - "tira tudo" limpa carrinho
        TODO (Fase 2):
        - Suportar quantidade ("tira UMA coca")
        - Clarificação quando ambíguo
    """
    carrinho = state.get('carrinho', [])
    mensagem = state.get('mensagem_atual', '')

    if not carrinho:
        return {
            'resposta': 'Seu carrinho está vazio! Não há nada para remover.',
            'etapa': 'inicio',
        }

    # Extrair itens para remover
    itens_para_remover = extrair_item_carrinho(mensagem, carrinho)

    if not itens_para_remover:
        return {
            'resposta': 'Não encontrei esse item no seu carrinho.',
            'etapa': 'carrinho',
        }

    # Remover itens do carrinho (de trás para frente para preservar índices)
    carrinho_atualizado = carrinho.copy()
    indices_para_remover = set()
    for item in itens_para_remover:
        indices_para_remover.update(item['indices'])

    # Remove em ordem decrescente para não corromper índices
    for indice in sorted(indices_para_remover, reverse=True):
        carrinho_atualizado.pop(indice)

    if not carrinho_atualizado:
        return {
            'resposta': 'Todos os itens foram removidos do seu pedido.',
            'etapa': 'inicio',
            'carrinho': carrinho_atualizado,
        }

    # Calcular novo total
    total = sum(item.get('preco', 0) for item in carrinho_atualizado)
    linhas = []
    for item in carrinho_atualizado:
        nome = get_nome_item(item['item_id']) or item['item_id']
        linhas.append(f'{item["quantidade"]}x {nome} - R$ {item["preco"] / 100:.2f}')

    return {
        'resposta': 'Itens removidos!\nSeu pedido:\n'
        + '\n'.join(linhas)
        + f'\nTotal: R$ {total / 100:.2f}',
        'etapa': 'carrinho',
        'carrinho': carrinho_atualizado,
    }
