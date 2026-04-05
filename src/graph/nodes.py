"""Nos de processamento do grafo de atendimento.

Cada funcao representa um no no grafo LangGraph, recebendo e
retornando atualizacoes parciais do estado.

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

import time

from langgraph.config import get_config

from src.extratores import extrair
from src.graph.handlers.cancelar_handler import processar_cancelamento
from src.graph.handlers.carrinho_handler import processar_carrinho
from src.graph.handlers.clarificacao import clarificar
from src.graph.handlers.confirmar_handler import processar_confirmacao
from src.graph.handlers.pedido_handler import processar_pedido
from src.graph.handlers.remocao_handler import processar_remocao
from src.graph.handlers.saudacao_handler import processar_saudacao
from src.graph.handlers.troca_handler import processar_troca
from src.graph.state import RetornoNode, State
from src.observabilidade.registry import (
    get_extracao_logger,
    get_funil_logger,
    get_handler_logger,
    get_obs_logger,
)


# ── Helpers ─────────────────────────────────────────────────────────────────


def _get_thread_id() -> str:
    """Extrai thread_id do contexto LangGraph."""
    return get_config().get('configurable', {}).get('thread_id', '')


def _log_node_event(
    handler_name: str,
    mensagem: str,
    intent: str,
    input_dados: dict,
    output_dados: dict,
    tempo_ms: float,
) -> None:
    """Registra evento de observabilidade para um node.

    Args:
        handler_name: Nome do handler (ex: 'node_router').
        mensagem: Mensagem original do usuario.
        intent: Intencao classificada.
        input_dados: Dados de entrada do handler.
        output_dados: Dados de saida do handler.
        tempo_ms: Tempo de execucao em milissegundos.
    """
    thread_id = _get_thread_id()

    obs_logger = get_obs_logger()
    if obs_logger:
        obs_logger.registrar(
            thread_id=thread_id,
            mensagem=mensagem,
            mensagem_norm='',
            intent=intent,
            confidence=0.0,
            caminho='',
            top1_texto='',
            top1_intencao='',
        )

    funil_logger = get_funil_logger()
    if funil_logger:
        funil_logger.registrar(
            thread_id=thread_id,
            etapa_anterior='',
            etapa_atual=handler_name,
            intent=intent,
            carrinho_size=0,
        )

    handler_logger = get_handler_logger()
    if handler_logger:
        handler_logger.registrar(
            thread_id=thread_id,
            handler=handler_name,
            intent=intent,
            input_dados=input_dados,
            output_dados=output_dados,
            tempo_ms=tempo_ms,
        )


# ── Router ──────────────────────────────────────────────────────────────────


def _criar_node_router(classificador):
    """Factory para node_router com classificador injetado.

    Args:
        classificador: Instancia de ClassificadorIntencoes.

    Returns:
        Funcao node_router com classificador injetado.
    """

    def node_router(state: State) -> RetornoNode:
        """Classifica a intencao da mensagem e atualiza o estado."""
        mensagem = state.get('mensagem_atual', '')
        thread_id = _get_thread_id()
        inicio = time.monotonic()
        etapa_anterior = state.get('etapa', 'inicio')

        resultado = classificador.classificar(mensagem)
        meta = resultado.metadados

        # Registra evento de observabilidade
        obs_logger = get_obs_logger()
        obs_logger.registrar(
            thread_id=thread_id,
            mensagem=mensagem,
            mensagem_norm=resultado.mensagem_norm,
            intent=resultado.intent,
            confidence=resultado.confidence,
            caminho=resultado.caminho,
            top1_texto=resultado.top1_texto,
            top1_intencao=resultado.top1_intencao,
            lookup=meta.get('lookup', '') or '',
            rag_top1=meta.get('rag_top1', '') or '',
            rag_sim=str(meta.get('rag_sim', '')),
            rag_intent=meta.get('rag_intent', '') or '',
            llm_raw=meta.get('llm_raw', '') or '',
            llm_intent=meta.get('llm_intent', '') or '',
        )

        # Log de funil
        funil_logger = get_funil_logger()
        if funil_logger:
            funil_logger.registrar(
                thread_id=thread_id,
                etapa_anterior=etapa_anterior,
                etapa_atual='roteado',
                intent=resultado.intent,
                carrinho_size=len(state.get('carrinho', [])),
            )

        tempo_ms = (time.monotonic() - inicio) * 1000

        # Log de handler
        handler_logger = get_handler_logger()
        if handler_logger:
            handler_logger.registrar(
                thread_id=thread_id,
                handler='node_router',
                intent=resultado.intent,
                input_dados={'mensagem': mensagem},
                output_dados={
                    'intent': resultado.intent,
                    'confidence': resultado.confidence,
                    'caminho': resultado.caminho,
                    'top1_texto': resultado.top1_texto,
                    'top1_intencao': resultado.top1_intencao,
                },
                tempo_ms=tempo_ms,
            )

        return {
            'intent': resultado.intent,
            'confidence': resultado.confidence,
        }

    return node_router


# ── Compatibilidade com testes ──────────────────────────────────────────────

# Variavel global que testes podem mockar para injetar classificador
_classificador_padrao = None


def _classificar_intencao(mensagem: str, thread_id: str = '') -> dict:
    """Wrapper compativel com a API antiga para testes.

    Usa o classificador injetado se disponivel, senao retorna dict vazio.
    """
    if _classificador_padrao is not None:
        resultado = _classificador_padrao.classificar(mensagem)
        return {
            'intent': resultado.intent,
            'confidence': resultado.confidence,
            'caminho': resultado.caminho,
            'top1_texto': resultado.top1_texto,
            'top1_intencao': resultado.top1_intencao,
            'mensagem_norm': resultado.mensagem_norm,
        }
    return {
        'intent': 'desconhecido',
        'confidence': 0.0,
        'caminho': 'llm_fixo',
        'top1_texto': '',
        'top1_intencao': '',
        'mensagem_norm': mensagem,
    }


def node_router(state: State) -> RetornoNode:
    """Classifica a intencao da mensagem e atualiza o estado.

    Versao standalone para testes — usa _classificar_intencao
    que pode ser mockado.
    """
    mensagem = state.get('mensagem_atual', '')
    thread_id = _get_thread_id()
    inicio = time.monotonic()
    etapa_anterior = state.get('etapa', 'inicio')

    resultado = _classificar_intencao(mensagem, thread_id=thread_id)

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

    funil_logger = get_funil_logger()
    if funil_logger:
        funil_logger.registrar(
            thread_id=thread_id,
            etapa_anterior=etapa_anterior,
            etapa_atual='roteado',
            intent=resultado['intent'],
            carrinho_size=len(state.get('carrinho', [])),
        )

    tempo_ms = (time.monotonic() - inicio) * 1000

    handler_logger = get_handler_logger()
    if handler_logger:
        handler_logger.registrar(
            thread_id=thread_id,
            handler='node_router',
            intent=resultado['intent'],
            input_dados={'mensagem': mensagem},
            output_dados=resultado,
            tempo_ms=tempo_ms,
        )

    return {
        'intent': resultado['intent'],
        'confidence': resultado['confidence'],
    }


# ── Nodes ───────────────────────────────────────────────────────────────────


def node_verificar_etapa(state: State) -> RetornoNode:
    """No de verificacao de etapa do fluxo.

    Apenas passa adiante sem modificar o estado. A decisao
    de qual caminho seguir e feita pela edge condicional
    ``_decidir_entrada`` no builder.
    """
    return {}


def node_clarificacao(state: State) -> RetornoNode:
    """Processa resposta do usuario durante clarificacao de variante."""
    thread_id = _get_thread_id()
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
    """Extrai itens do cardapio da mensagem do usuario."""
    if state.get('intent') == 'pedir':
        mensagem = state.get('mensagem_atual', '')
        inicio = time.monotonic()
        itens = extrair(mensagem)
        tempo_ms = (time.monotonic() - inicio) * 1000

        ext_logger = get_extracao_logger()
        if ext_logger:
            ext_logger.registrar(
                thread_id=_get_thread_id(),
                mensagem=mensagem,
                itens_extraidos=itens,
                tempo_ms=tempo_ms,
            )
        return {'itens_extraidos': itens}
    return {'itens_extraidos': []}


def node_handler_pedir(state: State) -> RetornoNode:
    """Processa itens extraidos e os adiciona ao carrinho."""
    itens_extraidos = state.get('itens_extraidos') or []
    carrinho = state.get('carrinho', [])
    resultado = processar_pedido(itens_extraidos, carrinho)
    return resultado.to_dict()


def node_handler_saudacao(state: State) -> RetornoNode:
    """Gera resposta de saudacao com o nome do restaurante."""
    return processar_saudacao()


def node_handler_carrinho(state: State) -> RetornoNode:
    """Gera resposta com o conteudo atual do carrinho."""
    carrinho = state.get('carrinho', [])
    return processar_carrinho(carrinho)


def node_handler_confirmar(state: State) -> RetornoNode:
    """Processa confirmacao do pedido pelo usuario."""
    carrinho = state.get('carrinho', [])
    return processar_confirmacao(carrinho)


def node_handler_cancelar(state: State) -> RetornoNode:
    """Processa cancelamento do pedido."""
    carrinho = state.get('carrinho', [])
    return processar_cancelamento(carrinho)


def node_handler_remover(state: State) -> RetornoNode:
    """Processa remocao de itens do pedido."""
    carrinho = state.get('carrinho', [])
    mensagem = state.get('mensagem_atual', '')
    return processar_remocao(carrinho, mensagem).to_dict()


def node_handler_trocar(state: State) -> RetornoNode:
    """Processa troca de variante de item no pedido."""
    carrinho = state.get('carrinho', [])
    mensagem = state.get('mensagem_atual', '')
    return processar_troca(carrinho, mensagem).to_dict()
