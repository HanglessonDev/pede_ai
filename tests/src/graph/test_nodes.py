"""
Testes de alta qualidade para o módulo src/graph/nodes.py.

Características:
- Mock de dependências externas (LLM, spacy, etc)
- Testes de nodes implementados
- Parametrização para cobrir casos diversos
"""

import pytest
from unittest.mock import MagicMock, patch

from src.graph.nodes import (
    node_router,
    node_extrator,
    node_handler_pedir,
    node_handler_saudacao,
    node_handler_carrinho,
    node_handler_confirmar,
    node_handler_remover,
    node_verificar_etapa,
    node_clarificacao,
    node_handler_cancelar,
    node_handler_trocar,
)
from src.graph.state import State


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def state_carrinho_vazio():
    """State com carrinho vazio."""
    return {
        'mensagem_atual': '',
        'carrinho': [],
        'fila_clarificacao': [],
    }


@pytest.fixture
def state_com_carrinho():
    """State com itens no carrinho."""
    return {
        'mensagem_atual': '',
        'carrinho': [
            {'item_id': 'lanche_001', 'quantidade': 2, 'preco': 3000},
            {'item_id': 'bebida_001', 'quantidade': 1, 'preco': 500},
        ],
        'fila_clarificacao': [],
    }


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE NODE_ROUTER
# ══════════════════════════════════════════════════════════════════════════════


class TestNodeRouter:
    """Testes para node_router."""

    @patch('src.graph.nodes.get_config')
    @patch('src.graph.nodes.get_obs_logger')
    @patch('src.graph.nodes._classificar_intencao')
    def test_retorna_intent(self, mock_classificar, mock_get_logger, mock_get_config):
        """Deve retornar a intent classificada."""
        mock_get_config.return_value = {'configurable': {'thread_id': ''}}
        mock_classificar.return_value = {
            'intent': 'pedir',
            'confidence': 0.85,
            'caminho': 'llm_rag',
            'top1_texto': '',
            'top1_intencao': '',
            'mensagem_norm': '',
        }
        result = node_router({'mensagem_atual': 'quero xbacon'})  # type: ignore
        assert result['intent'] == 'pedir'
        assert result['confidence'] == 0.85

    @patch('src.graph.nodes.get_config')
    @patch('src.graph.nodes.get_obs_logger')
    @patch('src.graph.nodes._classificar_intencao')
    def test_chama_classificar_com_mensagem(
        self, mock_classificar, mock_get_logger, mock_get_config
    ):
        """Deve chamar classificar com a mensagem."""
        mock_get_config.return_value = {'configurable': {'thread_id': ''}}
        mock_classificar.return_value = {
            'intent': 'saudacao',
            'confidence': 0.9,
            'caminho': 'lookup',
            'top1_texto': 'oi',
            'top1_intencao': 'saudacao',
            'mensagem_norm': 'oi',
        }
        node_router({'mensagem_atual': 'oi'})  # type: ignore
        mock_classificar.assert_called_with('oi', thread_id='')

    @patch('src.graph.nodes.get_config')
    @patch('src.graph.nodes.get_obs_logger')
    @patch('src.graph.nodes._classificar_intencao')
    def test_mensagem_vazia(self, mock_classificar, mock_get_logger, mock_get_config):
        """Deve tratar mensagem vazia."""
        mock_get_config.return_value = {'configurable': {'thread_id': ''}}
        mock_classificar.return_value = {
            'intent': 'saudacao',
            'confidence': 0.9,
            'caminho': 'lookup',
            'top1_texto': '',
            'top1_intencao': '',
            'mensagem_norm': '',
        }
        result = node_router({'mensagem_atual': ''})  # type: ignore
        assert result['intent'] == 'saudacao'


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE NODE_EXTRATOR
# ══════════════════════════════════════════════════════════════════════════════


class TestNodeExtrator:
    """Testes para node_extrator."""

    @patch('src.graph.nodes.extrair')
    def test_intent_pedir_chama_extrair(self, mock_extrair):
        """Quando intent e 'pedir', deve chamar extrair."""
        mock_extrair.return_value = [{'item_id': 'lanche_001', 'quantidade': 1}]
        node_extrator({'intent': 'pedir', 'mensagem_atual': 'xbacon'})  # type: ignore
        mock_extrair.assert_called_once_with('xbacon')

    @patch('src.graph.nodes.extrair')
    def test_outra_intent_nao_chama_extrair(self, mock_extrair):
        """Quando intent nao e 'pedir', nao deve chamar extrair."""
        result = node_extrator({'intent': 'saudacao', 'mensagem_atual': 'oi'})  # type: ignore
        mock_extrair.assert_not_called()
        assert result['itens_extraidos'] == []


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE NODE_HANDLER_SAUDACAO
# ══════════════════════════════════════════════════════════════════════════════


class TestNodeHandlerSaudacao:
    """Testes para node_handler_saudacao."""

    @patch('src.graph.handlers.saudacao_handler.get_tenant_nome')
    def test_retorna_saudacao_com_nome(self, mock_get_nome):
        """Deve retornar saudacao com nome do tenant."""
        mock_get_nome.return_value = 'Lanchonete do Ze'
        result = node_handler_saudacao({})  # type: ignore
        assert 'Lanchonete do Ze' in result['resposta']
        assert result['etapa'] == 'saudacao'


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE NODE_HANDLER_CARRINHO
# ══════════════════════════════════════════════════════════════════════════════


class TestNodeHandlerCarrinho:
    """Testes para node_handler_carrinho."""

    def test_carrinho_vazio_retorna_mensagem(self, state_carrinho_vazio):
        """Carrinho vazio deve retornar mensagem."""
        result = node_handler_carrinho(state_carrinho_vazio)  # type: ignore
        assert 'carrinho' in result['resposta'].lower()
        assert 'vazio' in result['resposta'].lower()

    @patch('src.graph.handlers.carrinho.get_nome_item')
    def test_carrinho_com_itens_retorna_lista(self, mock_nome, state_com_carrinho):
        """Carrinho com itens deve retornar lista formatada."""
        mock_nome.side_effect = lambda id: (
            'Hamburguer' if id == 'lanche_001' else 'Coca-Cola'
        )
        result = node_handler_carrinho(state_com_carrinho)  # type: ignore
        assert 'Hamburguer' in result['resposta']
        assert 'Total' in result['resposta']

    @patch('src.graph.handlers.carrinho.get_nome_item')
    def test_total_calculado_corretamente(self, mock_nome, state_com_carrinho):
        """Total deve ser calculado corretamente."""
        mock_nome.side_effect = lambda id: 'Item'
        result = node_handler_carrinho(state_com_carrinho)  # type: ignore
        assert '65.00' in result['resposta']


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE NODE_HANDLER_PEDIR
# ══════════════════════════════════════════════════════════════════════════════


class TestNodeHandlerPedir:
    """Testes para node_handler_pedir."""

    @patch('src.graph.nodes.get_config')
    @patch('src.graph.nodes.processar_pedido')
    def test_delega_para_handler_pedir(self, mock_processar, mock_config):
        """Deve delegar processamento para o handler."""
        from src.graph.handlers.pedido_handler import ResultadoPedir

        mock_config.return_value = {'configurable': {'thread_id': 'teste'}}
        mock_processar.return_value = ResultadoPedir(
            carrinho=[{'item_id': 'lanche_001', 'preco': 1500}],
            fila=[],
            resposta='1x Hambúrguer — R$ 15.00',
        )
        state = {
            'itens_extraidos': [{'item_id': 'lanche_001', 'quantidade': 1}],
            'carrinho': [],
            'fila_clarificacao': [],
        }
        result = node_handler_pedir(state)  # type: ignore
        assert mock_processar.called
        assert len(result['carrinho']) == 1

    @patch('src.graph.nodes.get_config')
    def test_itens_extraidos_vazio(self, mock_config):
        """Itens extraidos vazio deve retornar listas vazias."""
        mock_config.return_value = {'configurable': {'thread_id': 'teste'}}
        state = {'itens_extraidos': [], 'carrinho': [], 'fila_clarificacao': []}
        result = node_handler_pedir(state)  # type: ignore
        assert result['carrinho'] == []


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE NODE_HANDLER_CONFIRMAR
# ══════════════════════════════════════════════════════════════════════════════


class TestNodeHandlerConfirmar:
    """Testes para node_handler_confirmar."""

    def test_carrinho_vazio_retorna_mensagem(self):
        """Carrinho vazio deve retornar mensagem adequada."""
        result = node_handler_confirmar({'carrinho': [], 'etapa': ''})  # type: ignore
        assert (
            'nada' in result['resposta'].lower()
            or 'vazio' in result['resposta'].lower()
            or 'não há' in result['resposta'].lower()
        )

    def test_confirmar_generico_com_carrinho_retorna_total(self):
        """Confirmacao generica com carrinho deve retornar total."""
        state: State = {
            'mensagem_atual': '',
            'intent': '',
            'itens_extraidos': [],
            'carrinho': [{'item_id': 'lanche_001', 'preco': 1500}],
            'fila_clarificacao': [],
            'etapa': 'pedindo',
            'resposta': '',
            'tentativas_clarificacao': 0,
        }
        result = node_handler_confirmar(state)
        assert 'confirmado' in result['resposta'].lower()
        assert '15.00' in result['resposta']


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE NODE_HANDLER_REMOVER
# ══════════════════════════════════════════════════════════════════════════════


class TestNodeHandlerRemover:
    """Testes para node_handler_remover()."""

    def test_remover_carrinho_vazio(self):
        """Remover com carrinho vazio deve retornar mensagem de erro."""
        state: State = {
            'mensagem_atual': 'tira a coca',
            'intent': 'remover',
            'itens_extraidos': [],
            'carrinho': [],
            'fila_clarificacao': [],
            'etapa': 'carrinho',
            'resposta': '',
            'tentativas_clarificacao': 0,
            'confidence': 0.0,
        }
        result = node_handler_remover(state)
        assert 'vazio' in result['resposta'].lower()
        assert result['etapa'] == 'inicio'

    def test_remover_item_inexistente(self):
        """Remover item que não existe deve retornar mensagem de erro."""
        state: State = {
            'mensagem_atual': 'tira pizza',
            'intent': 'remover',
            'itens_extraidos': [],
            'carrinho': [
                {
                    'item_id': 'lanche_001',
                    'quantidade': 2,
                    'preco': 3000,
                    'variante': None,
                },
            ],
            'fila_clarificacao': [],
            'etapa': 'carrinho',
            'resposta': '',
            'tentativas_clarificacao': 0,
            'confidence': 0.0,
        }
        result = node_handler_remover(state)
        assert 'não encontrei' in result['resposta'].lower()
        assert result['etapa'] == 'carrinho'

    def test_remover_item_simples(self):
        """Remover item simples deve funcionar."""
        state: State = {
            'mensagem_atual': 'tira a coca',
            'intent': 'remover',
            'itens_extraidos': [],
            'carrinho': [
                {
                    'item_id': 'lanche_002',
                    'quantidade': 2,
                    'preco': 1800,
                    'variante': None,
                },
                {
                    'item_id': 'bebida_001',
                    'quantidade': 1,
                    'preco': 500,
                    'variante': 'lata',
                },
            ],
            'fila_clarificacao': [],
            'etapa': 'carrinho',
            'resposta': '',
            'tentativas_clarificacao': 0,
            'confidence': 0.0,
        }
        result = node_handler_remover(state)
        assert (
            'removido' in result['resposta'].lower()
            or 'Itens removidos' in result['resposta']
        )
        assert len(result['carrinho']) == 1
        assert result['carrinho'][0]['item_id'] == 'lanche_002'

    def test_remover_tudo(self):
        """'tira tudo' deve remover todos os itens."""
        state: State = {
            'mensagem_atual': 'tira tudo',
            'intent': 'remover',
            'itens_extraidos': [],
            'carrinho': [
                {
                    'item_id': 'lanche_002',
                    'quantidade': 2,
                    'preco': 1800,
                    'variante': None,
                },
                {
                    'item_id': 'bebida_001',
                    'quantidade': 1,
                    'preco': 500,
                    'variante': 'lata',
                },
            ],
            'fila_clarificacao': [],
            'etapa': 'carrinho',
            'resposta': '',
            'tentativas_clarificacao': 0,
            'confidence': 0.0,
        }
        result = node_handler_remover(state)
        assert not result['carrinho']
        assert (
            'todos os itens' in result['resposta'].lower()
            or 'removido' in result['resposta'].lower()
        )


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE NODE_VERIFICAR_ETAPA
# ══════════════════════════════════════════════════════════════════════════════


class TestNodeVerificarEtapa:
    """Testes para node_verificar_etapa."""

    def test_retorna_dict_vazio(self):
        """Deve retornar dict vazio passando adiante."""
        state = {'etapa': 'pedindo', 'carrinho': []}
        result = node_verificar_etapa(state)  # type: ignore[arg-type]
        assert result == {}


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE NODE_CLARIFICACAO
# ══════════════════════════════════════════════════════════════════════════════


class TestNodeClarificacao:
    """Testes para node_clarificacao."""

    @patch('src.graph.nodes._get_thread_id')
    @patch('src.graph.nodes.clarificar')
    def test_processa_resposta_clarificacao(self, mock_clarificar, mock_thread):
        """Deve processar resposta de clarificação."""
        mock_thread.return_value = 'thread_1'
        mock_clarificar.return_value = MagicMock(
            carrinho=[{'item_id': 'lanche_001', 'quantidade': 1}],
            fila=[],
            resposta='Item adicionado',
            etapa='carrinho',
        )
        state = {
            'mensagem_atual': 'duplo',
            'carrinho': [],
            'fila_clarificacao': [
                {
                    'item': {'item_id': 'lanche_001', 'variante': None},
                    'item_id': 'lanche_001',
                    'nome': 'Hambúrguer',
                    'campo': 'variante',
                    'opcoes': ['simples', 'duplo'],
                }
            ],
            'tentativas_clarificacao': 0,
        }
        result = node_clarificacao(state)  # type: ignore[arg-type]
        assert len(result['carrinho']) == 1
        assert result['fila_clarificacao'] == []

    @patch('src.graph.nodes._get_thread_id')
    @patch('src.graph.nodes.clarificar')
    def test_atualiza_carrinho_corretamente(self, mock_clarificar, mock_thread):
        """Deve combinar carrinho existente com itens da clarificação."""
        mock_thread.return_value = 'thread_1'
        mock_clarificar.return_value = MagicMock(
            carrinho=[{'item_id': 'lanche_002', 'quantidade': 1}],
            fila=[],
            resposta='Ok',
            etapa='carrinho',
        )
        state = {
            'mensagem_atual': 'lata',
            'carrinho': [{'item_id': 'lanche_001', 'quantidade': 2, 'preco': 3000}],
            'fila_clarificacao': [
                {
                    'item': {'item_id': 'bebida_001', 'variante': None},
                    'item_id': 'bebida_001',
                    'nome': 'Coca-Cola',
                    'campo': 'variante',
                    'opcoes': ['lata', 'garrafa'],
                }
            ],
            'tentativas_clarificacao': 1,
        }
        result = node_clarificacao(state)  # type: ignore[arg-type]
        assert len(result['carrinho']) == 2
        assert result['carrinho'][0]['item_id'] == 'lanche_001'


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE NODE_HANDLER_CANCELAR
# ══════════════════════════════════════════════════════════════════════════════


class TestNodeHandlerCancelar:
    """Testes para node_handler_cancelar."""

    def test_cancela_com_carrinho_vazio(self):
        """Cancelar com carrinho vazio retorna mensagem adequada."""
        state = {'carrinho': []}
        result = node_handler_cancelar(state)  # type: ignore[arg-type]
        assert 'cancelar' in result['resposta'].lower()
        assert result['etapa'] == 'inicio'

    def test_cancela_carrinho_com_itens(self):
        """Cancelar com itens deve limpar o carrinho."""
        state = {
            'carrinho': [
                {'item_id': 'lanche_001', 'quantidade': 2, 'preco': 3000},
                {'item_id': 'bebida_001', 'quantidade': 1, 'preco': 500},
            ]
        }
        result = node_handler_cancelar(state)  # type: ignore[arg-type]
        assert result['carrinho'] == []
        assert result['fila_clarificacao'] == []
        assert 'cancelado' in result['resposta'].lower()


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE NODE_HANDLER_TROCAR
# ══════════════════════════════════════════════════════════════════════════════


class TestNodeHandlerTrocar:
    """Testes para node_handler_trocar."""

    @patch('src.graph.nodes.processar_troca')
    def test_processa_troca_variante(self, mock_trocar):
        """Deve processar troca de variante."""
        from src.graph.handlers.troca_handler import ResultadoTrocar

        mock_trocar.return_value = ResultadoTrocar(
            carrinho=[{'item_id': 'lanche_001', 'variante': 'duplo', 'preco': 1800}],
            resposta='Variante alterada para duplo',
            etapa='carrinho',
        )
        state = {
            'mensagem_atual': 'muda pra duplo',
            'carrinho': [{'item_id': 'lanche_001', 'variante': 'simples', 'preco': 1500}],
        }
        result = node_handler_trocar(state)  # type: ignore[arg-type]
        assert mock_trocar.called
        assert len(result['carrinho']) == 1


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE _LOG_NODE_EVENT
# ══════════════════════════════════════════════════════════════════════════════


class TestLogNodeEvent:
    """Testes para _log_node_event."""

    @patch('src.graph.nodes.get_obs_logger')
    @patch('src.graph.nodes.get_funil_logger')
    @patch('src.graph.nodes.get_handler_logger')
    @patch('src.graph.nodes._get_thread_id')
    def test_com_todos_loggers(
        self, mock_thread, mock_handler, mock_funil, mock_obs
    ):
        """Deve registrar em todos os loggers quando disponiveis."""
        from src.graph.nodes import _log_node_event

        mock_thread.return_value = 'thread_1'
        mock_obs.return_value = MagicMock()
        mock_funil.return_value = MagicMock()
        mock_handler.return_value = MagicMock()

        _log_node_event(
            handler_name='node_router',
            mensagem='oi',
            intent='saudacao',
            input_dados={'mensagem': 'oi'},
            output_dados={'intent': 'saudacao'},
            tempo_ms=10.5,
        )

        mock_obs.return_value.registrar.assert_called_once()
        mock_funil.return_value.registrar.assert_called_once()
        mock_handler.return_value.registrar.assert_called_once()

    @patch('src.graph.nodes.get_obs_logger')
    @patch('src.graph.nodes.get_funil_logger')
    @patch('src.graph.nodes.get_handler_logger')
    @patch('src.graph.nodes._get_thread_id')
    def test_com_loggers_none_nao_quebra(
        self, mock_thread, mock_handler, mock_funil, mock_obs
    ):
        """Loggers None nao devem quebrar a funcao."""
        from src.graph.nodes import _log_node_event

        mock_thread.return_value = 'thread_1'
        mock_obs.return_value = None
        mock_funil.return_value = None
        mock_handler.return_value = None

        _log_node_event(
            handler_name='node_router',
            mensagem='oi',
            intent='saudacao',
            input_dados={},
            output_dados={},
            tempo_ms=5.0,
        )


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE _CRIAR_NODE_ROUTER
# ══════════════════════════════════════════════════════════════════════════════


class TestCriarNodeRouter:
    """Testes para _criar_node_router (factory)."""

    @patch('src.graph.nodes.get_obs_logger')
    @patch('src.graph.nodes.get_funil_logger')
    @patch('src.graph.nodes.get_handler_logger')
    @patch('src.graph.nodes.get_config')
    def test_factory_retorna_funcao(self, mock_config, mock_handler, mock_funil, mock_obs):
        """Factory deve retornar funcao callavel."""
        from src.graph.nodes import _criar_node_router
        from src.roteador.modelos import ResultadoClassificacao

        mock_config.return_value = {'configurable': {'thread_id': 't1'}}
        mock_obs.return_value = MagicMock()
        mock_funil.return_value = None
        mock_handler.return_value = None

        class MockClassificador:
            def classificar(self, msg):
                return ResultadoClassificacao(
                    intent='pedir',
                    confidence=0.9,
                    caminho='llm',
                    top1_texto='',
                    top1_intencao='',
                    mensagem_norm=msg,
                )

        node = _criar_node_router(MockClassificador())
        assert callable(node)

    @patch('src.graph.nodes.get_obs_logger')
    @patch('src.graph.nodes.get_funil_logger')
    @patch('src.graph.nodes.get_handler_logger')
    @patch('src.graph.nodes.get_config')
    def test_factory_classifica_corretamente(
        self, mock_config, mock_handler, mock_funil, mock_obs
    ):
        """Funcao retornada deve classificar corretamente."""
        from src.graph.nodes import _criar_node_router
        from src.roteador.modelos import ResultadoClassificacao

        mock_config.return_value = {'configurable': {'thread_id': 't1'}}
        mock_obs.return_value = MagicMock()
        mock_funil.return_value = None
        mock_handler.return_value = None

        class MockClassificador:
            def classificar(self, msg):
                return ResultadoClassificacao(
                    intent='saudacao',
                    confidence=0.95,
                    caminho='lookup',
                    top1_texto='oi',
                    top1_intencao='saudacao',
                    mensagem_norm=msg,
                )

        node = _criar_node_router(MockClassificador())
        result = node({'mensagem_atual': 'oi', 'carrinho': [], 'etapa': 'inicio'})  # type: ignore[arg-type]
        assert result['intent'] == 'saudacao'
        assert result['confidence'] == 0.95


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE _CLASSIFICAR_INTENCAO
# ══════════════════════════════════════════════════════════════════════════════


class TestClassificarIntencao:
    """Testes para _classificar_intencao."""

    def test_sem_classificador_retorna_fallback(self):
        """Sem classificador injetado deve retornar dict vazio."""
        from src.graph import nodes
        nodes._classificador_padrao = None

        result = nodes._classificar_intencao('quero um hamburguer')
        assert result['intent'] == 'desconhecido'
        assert result['confidence'] == 0.0
        assert result['caminho'] == 'llm_fixo'

    def test_com_classificador_retorna_resultado(self):
        """Com classificador injetado deve retornar resultado."""
        from src.graph import nodes
        from src.roteador.modelos import ResultadoClassificacao

        class MockClassificador:
            def classificar(self, msg):
                return ResultadoClassificacao(
                    intent='pedir',
                    confidence=0.88,
                    caminho='rag',
                    top1_texto='hamburguer',
                    top1_intencao='pedir',
                    mensagem_norm=msg,
                )

        nodes._classificador_padrao = MockClassificador()
        result = nodes._classificar_intencao('quero hamburguer')
        assert result['intent'] == 'pedir'
        assert result['confidence'] == 0.88
        assert result['caminho'] == 'rag'
        nodes._classificador_padrao = None


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE INTEGRIDADE
# ══════════════════════════════════════════════════════════════════════════════


class TestIntegridade:
    """Testes de integridade dos nodes."""

    def test_nodes_retornam_dict(self):
        """Todos os nodes devem ser callable."""
        assert callable(node_router)
        assert callable(node_extrator)
        assert callable(node_handler_saudacao)
        assert callable(node_handler_carrinho)
        assert callable(node_handler_pedir)
        assert callable(node_handler_confirmar)
        assert callable(node_handler_remover)


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE OBSERVABILIDADE NOS NODES
# ══════════════════════════════════════════════════════════════════════════════


class TestNodesObservabilidade:
    """Testes de instrumentacao de observabilidade nos nodes."""

    @patch('src.graph.nodes.get_config')
    @patch('src.graph.nodes.get_funil_logger')
    @patch('src.graph.nodes.get_handler_logger')
    @patch('src.graph.nodes.get_obs_logger')
    @patch('src.graph.nodes._classificar_intencao')
    def test_node_router_registra_funil(
        self,
        mock_classificar,
        mock_get_obs,
        mock_get_handler,
        mock_get_funil,
        mock_get_config,
    ):
        """Node router deve registrar logs de funil e handler."""
        mock_get_config.return_value = {'configurable': {'thread_id': 't1'}}
        mock_funil = MagicMock()
        mock_handler = MagicMock()
        mock_obs = MagicMock()
        mock_get_funil.return_value = mock_funil
        mock_get_handler.return_value = mock_handler
        mock_get_obs.return_value = mock_obs
        mock_classificar.return_value = {
            'intent': 'pedir',
            'confidence': 0.85,
            'caminho': 'llm_rag',
            'top1_texto': '',
            'top1_intencao': '',
            'mensagem_norm': '',
        }

        state = {'mensagem_atual': 'oi', 'etapa': 'inicio', 'carrinho': []}
        node_router(state)  # type: ignore[arg-type]

        assert mock_funil.registrar.called
        assert mock_handler.registrar.called

    @patch('src.graph.nodes.get_config')
    @patch('src.graph.nodes.get_funil_logger')
    @patch('src.graph.nodes.get_handler_logger')
    @patch('src.graph.nodes.get_obs_logger')
    @patch('src.graph.nodes._classificar_intencao')
    def test_node_router_loggers_nulos_nao_quebram(
        self,
        mock_classificar,
        mock_get_obs,
        mock_get_handler,
        mock_get_funil,
        mock_get_config,
    ):
        """Loggers nulos nao devem causar erro."""
        mock_get_config.return_value = {'configurable': {'thread_id': 't1'}}
        mock_get_funil.return_value = None
        mock_get_handler.return_value = None
        mock_get_obs.return_value = MagicMock()
        mock_classificar.return_value = {
            'intent': 'saudacao',
            'confidence': 0.9,
            'caminho': 'lookup',
            'top1_texto': 'oi',
            'top1_intencao': 'saudacao',
            'mensagem_norm': 'oi',
        }

        state = {'mensagem_atual': 'oi', 'etapa': 'inicio', 'carrinho': []}
        result = node_router(state)  # type: ignore[arg-type]

        assert result['intent'] == 'saudacao'

    @patch('src.graph.nodes.get_config')
    @patch('src.graph.nodes.get_extracao_logger')
    @patch('src.graph.nodes.extrair')
    def test_node_extrator_registra_extracao(
        self, mock_extrair, mock_get_ext, mock_get_config
    ):
        """Node extrator deve registrar log de extracao quando intent e pedir."""
        mock_get_config.return_value = {'configurable': {'thread_id': 't1'}}
        mock_ext = MagicMock()
        mock_get_ext.return_value = mock_ext
        mock_extrair.return_value = [{'item_id': 'lanche_001', 'quantidade': 1}]

        state = {
            'mensagem_atual': 'quero um x-salada',
            'intent': 'pedir',
        }
        node_extrator(state)  # type: ignore[arg-type]

        assert mock_ext.registrar.called

    @patch('src.graph.nodes.get_config')
    @patch('src.graph.nodes.get_extracao_logger')
    @patch('src.graph.nodes.extrair')
    def test_node_extrator_logger_nulo_nao_quebra(
        self, mock_extrair, mock_get_ext, mock_get_config
    ):
        """Logger nulo nao deve causar erro no extrator."""
        mock_get_config.return_value = {'configurable': {'thread_id': 't1'}}
        mock_get_ext.return_value = None
        mock_extrair.return_value = []

        state = {
            'mensagem_atual': 'quero um x-salada',
            'intent': 'pedir',
        }
        result = node_extrator(state)  # type: ignore[arg-type]

        assert result['itens_extraidos'] == []
