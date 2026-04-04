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

from langgraph.config import get_config

from src.config import get_tenant_nome
from src.extratores import extrair
from src.graph.handlers.clarificacao import clarificar
from src.graph.handlers.pedir import processar as processar_pedido
from src.graph.handlers.remover import processar_remocao
from src.graph.handlers.utils import calcular_total_carrinho, formatar_carrinho
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
    thread_id = get_config().get('configurable', {}).get('thread_id', '')

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
    thread_id = get_config().get('configurable', {}).get('thread_id', '')
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
    resposta = 'Seu pedido:\n' + formatar_carrinho(carrinho)
    total = calcular_total_carrinho(carrinho)
    resposta += f'\nTotal: R$ {total / 100:.2f}'
    return {'resposta': resposta, 'etapa': 'carrinho'}


def node_handler_confirmar(state: State) -> RetornoNode:
    """Processa confirmação do pedido pelo usuário.

    Calcula o total do carrinho, gera mensagem de confirmação
    e limpa o carrinho após o pedido ser finalizado.

    Args:
        state: Estado atual do grafo de atendimento.

    Returns:
        Dicionário com ``resposta``, ``etapa`` e ``carrinho`` atualizados.
        Retorna mensagem de erro se o carrinho estiver vazio.

    Example:
        ```python
        state = {
            'mensagem_atual': 'confirmar',
            'intent': 'confirmar',
            'itens_extraidos': [],
            'carrinho': [
                {
                    'item_id': 'lanche_001',
                    'nome': 'Hambúrguer',
                    'quantidade': 1,
                    'preco': 1500,
                    'variante': 'simples',
                },
            ],
            'fila_clarificacao': [],
            'etapa': 'inicio',
            'resposta': '',
        }
        result = node_handler_confirmar(state)
        result['etapa']
        'finalizado'
        ```
    """
    carrinho = state.get('carrinho', [])
    if not carrinho:
        return {'resposta': 'Não há pedido para confirmar.'}
    total = calcular_total_carrinho(carrinho)
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

    total = calcular_total_carrinho(carrinho)
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
    """
    carrinho = state.get('carrinho', [])
    mensagem = state.get('mensagem_atual', '')
    return processar_remocao(carrinho, mensagem).to_dict()
