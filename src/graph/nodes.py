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
        'modo': 'ocioso',
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
from src.observabilidade.contexto import extrair_contexto_dispatcher
from src.observabilidade.loggers import ObservabilidadeLoggers
from src.observabilidade.registry import (
    get_debug_session_logger,
    get_dispatcher_logger,
    get_exception_logger,
    get_extracao_logger,
    get_funil_logger,
    get_handler_logger,
    get_negocio_logger,
    get_obs_logger,
    get_pedido_logger,
)


# ── Helpers ─────────────────────────────────────────────────────────────────


def _get_thread_id() -> str:
    """Extrai thread_id do contexto LangGraph."""
    return get_config().get('configurable', {}).get('thread_id', '')


def _get_turn_id(state: State) -> str:
    """Extrai turn_id do estado, ou string vazia se ausente."""
    return state.get('turn_id', '')


def _log_negocio(state: State, evento: str, resultado: RetornoNode) -> None:
    """Helper para logar eventos de negocio."""
    negocio_logger = get_negocio_logger()
    if not negocio_logger:
        return

    carrinho = state.get('carrinho', [])
    carrinho_size = len(resultado.get('carrinho', carrinho))
    preco_total = 0
    for item in resultado.get('carrinho', carrinho):
        preco_total += item.get('preco_centavos', item.get('preco', 0))

    negocio_logger.registrar(
        thread_id=_get_thread_id(),
        turn_id=_get_turn_id(state),
        evento=evento,
        carrinho_size=carrinho_size,
        preco_total_centavos=preco_total,
        intent=state.get('intent', ''),
        resposta=resultado.get('resposta', ''),
        tentativas_clarificacao=state.get('tentativas_clarificacao', 0),
    )


def _log_debug(
    state: State, node: str, fase: str, dados_brutos: dict | None = None
) -> None:
    """Helper para debug mode — logga estado completo no JSONL da sessão."""
    debug_logger = get_debug_session_logger()
    if debug_logger:
        debug_logger.registrar(
            thread_id=_get_thread_id(),
            turn_id=_get_turn_id(state),
            node=node,
            fase=fase,
            estado={
                k: v for k, v in state.items() if k != 'carrinho'
            },  # carrinho pode ser grande
            dados_brutos=dados_brutos,
        )


def _log_dispatcher(
    state: State,
    acao_final: str,
    passos: dict,
    tempo_ms: float,
) -> None:
    """Helper para logar decisao do dispatcher."""
    dispatcher_logger = get_dispatcher_logger()
    if dispatcher_logger:
        dispatcher_logger.registrar(
            thread_id=_get_thread_id(),
            turn_id=_get_turn_id(state),
            acao_final=acao_final,
            passos=passos,
            tempo_ms=tempo_ms,
        )


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
            modo_anterior='',
            modo_atual=handler_name,
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
        modo_anterior = state.get('modo', 'ocioso')

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
                modo_anterior=modo_anterior,
                modo_atual='roteado',
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
    modo_anterior = state.get('modo', 'ocioso')

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
            modo_anterior=modo_anterior,
            modo_atual='roteado',
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


def node_verificar_modo(state: State) -> RetornoNode:
    """No de verificacao de modo do fluxo.

    Apenas passa adiante sem modificar o estado. A decisao
    de qual caminho seguir e feita pela edge condicional
    ``_decidir_entrada`` no builder.
    """
    return {}


def node_clarificacao(state: State) -> RetornoNode:
    """Processa resposta do usuario durante clarificacao de variante."""
    try:
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
            'modo': resultado.modo,
        }
    except Exception as e:
        exc_logger = get_exception_logger()
        if exc_logger:
            exc_logger.registrar(
                thread_id=_get_thread_id(),
                turn_id=_get_turn_id(state),
                componente='node_clarificacao',
                exception=e,
                estado={
                    'mensagem_atual': state.get('mensagem_atual', ''),
                    'fila_size': len(state.get('fila_clarificacao', [])),
                    'tentativas': state.get('tentativas_clarificacao', 0),
                },
            )
        return {
            'resposta': 'Erro ao processar resposta. Tente novamente.',
            'modo': 'ocioso',
        }


def node_extrator(state: State) -> RetornoNode:
    """Extrai itens do cardapio da mensagem do usuario."""
    try:
        if state.get('intent') == 'pedir':
            mensagem = state.get('mensagem_atual', '')
            inicio = time.monotonic()
            loggers: ObservabilidadeLoggers | None = state.get('loggers')  # type: ignore[assignment]
            try:
                thread_id = _get_thread_id()
            except RuntimeError:
                thread_id = ''
            turn_id = _get_turn_id(state)
            itens = extrair(mensagem, loggers=loggers, thread_id=thread_id, turn_id=turn_id)
            tempo_ms = (time.monotonic() - inicio) * 1000

            ext_logger = get_extracao_logger()
            if ext_logger:
                ext_logger.registrar(
                    thread_id=thread_id,
                    mensagem=mensagem,
                    itens_extraidos=itens,
                    tempo_ms=tempo_ms,
                )
            return {'itens_extraidos': itens}
        return {'itens_extraidos': []}
    except Exception as e:
        exc_logger = get_exception_logger()
        if exc_logger:
            exc_logger.registrar(
                thread_id=_get_thread_id(),
                turn_id=_get_turn_id(state),
                componente='node_extrator',
                exception=e,
                estado={
                    'mensagem_atual': state.get('mensagem_atual', ''),
                    'intent': state.get('intent', ''),
                },
            )
        return {'itens_extraidos': []}


def node_handler_pedir(state: State) -> RetornoNode:
    """Processa itens extraidos e os adiciona ao carrinho."""
    try:
        itens_extraidos = state.get('itens_extraidos') or []
        carrinho = state.get('carrinho', [])
        resultado = processar_pedido(itens_extraidos, carrinho)

        pedido_logger = get_pedido_logger()
        if pedido_logger:
            itens_adicionados_dicts = resultado.carrinho
            preco_total = sum(i.get('preco_centavos', 0) for i in resultado.carrinho)
            pedido_logger.registrar(
                thread_id=_get_thread_id(),
                turn_id=_get_turn_id(state),
                itens_adicionados=itens_adicionados_dicts,
                itens_fila=resultado.fila,
                total_itens=len(resultado.carrinho),
                preco_total_centavos=preco_total,
                modo_saida=resultado.to_dict().get('modo', 'coletando'),
                resposta=resultado.resposta,
            )

        return resultado.to_dict()
    except Exception as e:
        exc_logger = get_exception_logger()
        if exc_logger:
            exc_logger.registrar(
                thread_id=_get_thread_id(),
                turn_id=_get_turn_id(state),
                componente='node_handler_pedir',
                exception=e,
                estado={
                    'mensagem_atual': state.get('mensagem_atual', ''),
                    'intent': state.get('intent', ''),
                    'itens_extraidos_count': len(state.get('itens_extraidos') or []),
                    'carrinho_size': len(state.get('carrinho', [])),
                },
            )
        return {
            'resposta': 'Erro ao processar pedido. Tente novamente.',
            'modo': 'ocioso',
        }


def _handler_fallback(componente: str, state: State) -> RetornoNode:
    """Retorno padrao para handlers com excecao."""
    exc_logger = get_exception_logger()
    if exc_logger:
        exc_logger.registrar(
            thread_id=_get_thread_id(),
            turn_id=_get_turn_id(state),
            componente=componente,
            exception=None,  # type: ignore[arg-type]
            estado={
                'mensagem_atual': state.get('mensagem_atual', ''),
                'intent': state.get('intent', ''),
            },
        )
    return {'resposta': 'Erro interno. Tente novamente.', 'modo': 'ocioso'}  # type: ignore[return-value]


def node_handler_saudacao(state: State) -> RetornoNode:
    """Gera resposta de saudacao com o nome do restaurante."""
    try:
        resultado = processar_saudacao()
        _log_negocio(state, 'saudacao', resultado)
        return resultado
    except Exception:
        return _handler_fallback('node_handler_saudacao', state)


def node_handler_carrinho(state: State) -> RetornoNode:
    """Gera resposta com o conteudo atual do carrinho."""
    try:
        carrinho = state.get('carrinho', [])
        resultado = processar_carrinho(carrinho)
        _log_negocio(state, 'carrinho', resultado)
        return resultado
    except Exception:
        return _handler_fallback('node_handler_carrinho', state)


def node_handler_confirmar(state: State) -> RetornoNode:
    """Processa confirmacao do pedido pelo usuario."""
    try:
        carrinho = state.get('carrinho', [])
        resultado = processar_confirmacao(carrinho)
        _log_negocio(state, 'confirmar', resultado)
        return resultado
    except Exception:
        return _handler_fallback('node_handler_confirmar', state)


def node_handler_cancelar(state: State) -> RetornoNode:
    """Processa cancelamento do pedido."""
    try:
        carrinho = state.get('carrinho', [])
        resultado = processar_cancelamento(carrinho)
        _log_negocio(state, 'cancelar', resultado)
        return resultado
    except Exception:
        return _handler_fallback('node_handler_cancelar', state)


def node_handler_remover(state: State) -> RetornoNode:
    """Processa remocao de itens do pedido."""
    try:
        carrinho = state.get('carrinho', [])
        mensagem = state.get('mensagem_atual', '')
        resultado = processar_remocao(carrinho, mensagem)
        _log_negocio(state, 'remover', resultado.to_dict())
        return resultado.to_dict()
    except Exception:
        return _handler_fallback('node_handler_remover', state)


def node_handler_trocar(state: State) -> RetornoNode:
    """Processa troca de variante de item no pedido."""
    try:
        carrinho = state.get('carrinho', [])
        mensagem = state.get('mensagem_atual', '')
        resultado = processar_troca(carrinho, mensagem)
        _log_negocio(state, 'trocar', resultado.to_dict())
        return resultado.to_dict()
    except Exception:
        return _handler_fallback('node_handler_trocar', state)


# Alias para compatibilidade com o dispatcher
node_handler_adicionar = node_handler_pedir


# ── Dispatcher de modificação ──────────────────────────────────────────────

from src.extratores import extrair_item_carrinho, extrair_itens_troca


_VERBOS_REMOCAO_ITEM: frozenset[str] = frozenset(
    {
        'tira',
        'tirar',
        'remove',
        'remover',
        'retira',
        'retirar',
        'tira fora',
        'tira esse',
        'some',
        'apaga',
        'deleta',
        'exclui',
        'não quero mais',
    }
)


def _parece_remocao(mensagem: str) -> bool:
    """Verifica se a mensagem usa verbo de remoção de item do carrinho."""
    msg = mensagem.lower()
    return any(verbo in msg for verbo in _VERBOS_REMOCAO_ITEM)


def node_dispatcher_modificar(state: State) -> RetornoNode:
    """Decide qual ação executar para intent modificar_pedido."""
    try:
        loggers: ObservabilidadeLoggers | None = state.get('loggers')  # type: ignore[assignment]
        try:
            thread_id = _get_thread_id()
        except RuntimeError:
            thread_id = ''
        turn_id = _get_turn_id(state)
        return _dispatcher_interno(
            state, loggers=loggers, thread_id=thread_id, turn_id=turn_id
        )
    except Exception as e:
        exc_logger = get_exception_logger()
        if exc_logger:
            try:
                exc_thread_id = _get_thread_id()
            except RuntimeError:
                exc_thread_id = ''
            exc_logger.registrar(
                thread_id=exc_thread_id,
                turn_id=_get_turn_id(state),
                componente='node_dispatcher_modificar',
                exception=e,
                estado={
                    'mensagem_atual': state.get('mensagem_atual', ''),
                    'carrinho_size': len(state.get('carrinho', [])),
                },
            )
        return {
            'acao': 'sem_entidade',
            'dados_extracao': {},
        }


def _dispatcher_interno(  # noqa: PLR0911,PLR0915
    state: State,
    loggers: ObservabilidadeLoggers | None = None,
    thread_id: str = '',
    turn_id: str = '',
) -> RetornoNode:
    """Logica interna do dispatcher — separada para exception handling."""
    inicio = time.monotonic()
    mensagem = state['mensagem_atual']
    carrinho = state.get('carrinho', [])

    # ── Passo 1: TrocaExtrator ──────────────────────────────────────────────
    trocas = extrair_itens_troca(
        mensagem, carrinho, loggers=loggers, thread_id=thread_id, turn_id=turn_id
    )
    caso = trocas['caso']
    item_original = trocas['item_original']
    variante_nova = trocas['variante_nova']

    passos: dict = {
        'troca_extrator': {
            'caso': caso,
            'item_original_id': item_original['item_id'] if item_original else None,
            'variante_nova': variante_nova,
        },
    }

    contexto = extrair_contexto_dispatcher(state)
    decisao_logger = loggers.decisor if loggers else None

    def _log_decisao(componente: str, decisao: str, alternativas: list[str], criterio: str, threshold: str = '', resultado: str = '') -> None:
        if decisao_logger:
            decisao_logger.registrar(
                thread_id=thread_id,
                turn_id=turn_id,
                componente=componente,
                decisao=decisao,
                alternativas=alternativas,
                criterio=criterio,
                threshold=threshold,
                resultado=resultado or decisao,
                contexto=contexto,
            )

    # Caso A: 2+ ITEMs mencionados
    if caso == 'A':
        _log_decisao(
            componente='dispatcher_passo1_troca',
            decisao=f'caso_{caso}',
            alternativas=['caso_A', 'caso_B', 'caso_C', 'caso_vazio'],
            criterio=f"num_items>={2}",
            threshold='caso_A=2+items, caso_B=1item, caso_C=1variante',
            resultado='tentar_extrair_itens',
        )
        itens = extrair(mensagem, loggers=loggers, thread_id=thread_id, turn_id=turn_id)
        if itens:
            passos['acao_final'] = 'adicionar_item'
            passos['extrair'] = {'itens_count': len(itens)}
            _log_decisao(
                componente='dispatcher_passo1_casoA',
                decisao='adicionar_item',
                alternativas=['adicionar_item', 'sem_entidade'],
                criterio=f'extrair retornou {len(itens)} itens',
                threshold='itens_count>0',
            )
            tempo_ms = (time.monotonic() - inicio) * 1000
            _log_dispatcher(state, 'adicionar_item', passos, tempo_ms)
            return {'acao': 'adicionar_item', 'itens_extraidos': itens}
        _log_decisao(
            componente='dispatcher_passo1_casoA',
            decisao='sem_entidade',
            alternativas=['adicionar_item', 'sem_entidade'],
            criterio='extrair retornou lista vazia no caso A',
            threshold='itens_count==0',
        )
        passos['acao_final'] = 'sem_entidade'
        tempo_ms = (time.monotonic() - inicio) * 1000
        _log_dispatcher(state, 'sem_entidade', passos, tempo_ms)
        return {'acao': 'sem_entidade', 'dados_extracao': trocas}

    # Caso B: 1 ITEM mencionado
    elif caso == 'B':
        _log_decisao(
            componente='dispatcher_passo1_troca',
            decisao=f'caso_{caso}',
            alternativas=['caso_A', 'caso_B', 'caso_C', 'caso_vazio'],
            criterio=f"num_items==1, item_original={'sim' if item_original else 'nao'}, variante_nova={'sim' if variante_nova else 'nao'}",
            threshold='caso_A=2+items, caso_B=1item, caso_C=1variante',
            resultado='avaliar_subcasos_B',
        )
        if item_original is not None and variante_nova is not None:
            _log_decisao(
                componente='dispatcher_passo1_casoB',
                decisao='trocar_variante',
                alternativas=['trocar_variante', 'remover_item', 'sem_entidade'],
                criterio='item_original e variante_nova ambos presentes',
                threshold='item_original!=None and variante_nova!=None',
            )
            passos['acao_final'] = 'trocar_variante'
            tempo_ms = (time.monotonic() - inicio) * 1000
            _log_dispatcher(state, 'trocar_variante', passos, tempo_ms)
            return {'acao': 'trocar_variante', 'dados_extracao': trocas}

        if item_original is not None and variante_nova is None:
            if _parece_remocao(mensagem):
                _log_decisao(
                    componente='dispatcher_passo1_casoB',
                    decisao='remover_item',
                    alternativas=['trocar_variante', 'remover_item', 'sem_entidade'],
                    criterio='item_original presente, sem variante, verbo de remocao detectado',
                    threshold='_parece_remocao==True',
                )
                passos['acao_final'] = 'remover_item'
                tempo_ms = (time.monotonic() - inicio) * 1000
                _log_dispatcher(state, 'remover_item', passos, tempo_ms)
                return {'acao': 'remover_item', 'dados_extracao': trocas}
            else:
                _log_decisao(
                    componente='dispatcher_passo1_casoB',
                    decisao='sem_entidade',
                    alternativas=['trocar_variante', 'remover_item', 'sem_entidade'],
                    criterio='item_original presente, sem variante, sem verbo de remocao',
                    threshold='_parece_remocao==False',
                )
                passos['acao_final'] = 'sem_entidade'
                tempo_ms = (time.monotonic() - inicio) * 1000
                _log_dispatcher(state, 'sem_entidade', passos, tempo_ms)
                return {'acao': 'sem_entidade', 'dados_extracao': trocas}

    # Caso C: 0 ITEMs + 1 VARIANTE isolada
    elif caso == 'C' and carrinho:
        _log_decisao(
            componente='dispatcher_passo1_troca',
            decisao=f'caso_C_com_carrinho',
            alternativas=['caso_A', 'caso_B', 'caso_C', 'caso_vazio'],
            criterio='num_items==0, 1 variante isolada, carrinho nao vazio',
            threshold='caso_C and len(carrinho)>0',
            resultado='trocar_variante',
        )
        passos['acao_final'] = 'trocar_variante'
        tempo_ms = (time.monotonic() - inicio) * 1000
        _log_dispatcher(state, 'trocar_variante', passos, tempo_ms)
        return {'acao': 'trocar_variante', 'dados_extracao': trocas}

    # Log caso C sem carrinho
    if caso == 'C':
        _log_decisao(
            componente='dispatcher_passo1_troca',
            decisao='caso_C_sem_carrinho',
            alternativas=['caso_A', 'caso_B', 'caso_C', 'caso_vazio'],
            criterio='num_items==0, 1 variante isolada, carrinho vazio — prosseguir para passo 2',
            threshold='caso_C and len(carrinho)==0',
            resultado='prosseguir_passo2',
        )

    # ── Passo 2: Remoção de item do carrinho ────────────────────────────────
    if carrinho and _parece_remocao(mensagem):
        _log_decisao(
            componente='dispatcher_passo2_remocao',
            decisao='tentar_remocao',
            alternativas=['remover_item', 'prosseguir_passo3'],
            criterio='carrinho nao vazio e verbo de remocao detectado',
            threshold='len(carrinho)>0 and _parece_remocao==True',
            resultado='tentar_extrair_item_carrinho',
        )
        remocoes = extrair_item_carrinho(mensagem, carrinho)
        if remocoes:
            _log_decisao(
                componente='dispatcher_passo2_remocao',
                decisao='remover_item',
                alternativas=['remover_item', 'prosseguir_passo3'],
                criterio=f'extrair_item_carrinho retornou {len(remocoes)} matches',
                threshold='matches_count>0',
            )
            passos['remocao'] = {'matches_count': len(remocoes)}
            passos['acao_final'] = 'remover_item'
            tempo_ms = (time.monotonic() - inicio) * 1000
            _log_dispatcher(state, 'remover_item', passos, tempo_ms)
            return {
                'acao': 'remover_item',
                'dados_extracao': {'matches': remocoes},
            }
        _log_decisao(
            componente='dispatcher_passo2_remocao',
            decisao='sem_match_remocao',
            alternativas=['remover_item', 'prosseguir_passo3'],
            criterio='extrair_item_carrinho retornou lista vazia',
            threshold='matches_count==0',
            resultado='prosseguir_passo3',
        )

    # ── Passo 3: Adição de item novo ────────────────────────────────────────
    itens = extrair(mensagem, loggers=loggers, thread_id=thread_id, turn_id=turn_id)
    if itens:
        _log_decisao(
            componente='dispatcher_passo3_adicao',
            decisao='adicionar_item',
            alternativas=['adicionar_item', 'sem_entidade'],
            criterio=f'extrair retornou {len(itens)} itens',
            threshold='itens_count>0',
        )
        passos['extrair'] = {'itens_count': len(itens)}
        passos['acao_final'] = 'adicionar_item'
        tempo_ms = (time.monotonic() - inicio) * 1000
        _log_dispatcher(state, 'adicionar_item', passos, tempo_ms)
        return {'acao': 'adicionar_item', 'itens_extraidos': itens}

    # ── Passo 4: Nada encontrado ────────────────────────────────────────────
    _log_decisao(
        componente='dispatcher_passo4_fallback',
        decisao='sem_entidade',
        alternativas=['adicionar_item', 'sem_entidade'],
        criterio='nenhum extrator encontrou itens relevantes',
        threshold='itens_count==0',
    )
    passos['acao_final'] = 'sem_entidade'
    tempo_ms = (time.monotonic() - inicio) * 1000
    _log_dispatcher(state, 'sem_entidade', passos, tempo_ms)
    return {'acao': 'sem_entidade', 'dados_extracao': trocas}
