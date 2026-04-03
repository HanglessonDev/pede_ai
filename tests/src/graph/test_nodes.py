"""
Testes de alta qualidade para o módulo src/graph/nodes.py.

Características:
- Mock de dependências externas (LLM, spacy, etc)
- Testes de nodes implementados
- Parametrização para cobrir casos diversos
"""

import pytest
from unittest.mock import patch

from src.graph.nodes import (
    node_router,
    node_extrator,
    node_handler_pedir,
    node_handler_saudacao,
    node_handler_carrinho,
    node_handler_confirmar,
    node_handler_remover,
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

    @patch('src.graph.nodes._classificar_intencao')
    def test_retorna_intent(self, mock_classificar):
        """Deve retornar a intent classificada."""
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

    @patch('src.graph.nodes._classificar_intencao')
    def test_chama_classificar_com_mensagem(self, mock_classificar):
        """Deve chamar classificar com a mensagem."""
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

    @patch('src.graph.nodes._classificar_intencao')
    def test_mensagem_vazia(self, mock_classificar):
        """Deve tratar mensagem vazia."""
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

    @patch('src.graph.nodes.get_tenant_nome')
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
        assert 'carrinho está vazio' in result['resposta'].lower()

    @patch('src.graph.nodes.get_nome_item')
    def test_carrinho_com_itens_retorna_lista(self, mock_nome, state_com_carrinho):
        """Carrinho com itens deve retornar lista formatada."""
        mock_nome.side_effect = lambda id: (
            'Hamburguer' if id == 'lanche_001' else 'Coca-Cola'
        )
        result = node_handler_carrinho(state_com_carrinho)  # type: ignore
        assert 'Hamburguer' in result['resposta']
        assert 'Total' in result['resposta']

    @patch('src.graph.nodes.get_nome_item')
    def test_total_calculado_corretamente(self, mock_nome, state_com_carrinho):
        """Total deve ser calculado corretamente."""
        mock_nome.side_effect = lambda id: 'Item'
        result = node_handler_carrinho(state_com_carrinho)  # type: ignore
        assert '35.00' in result['resposta']


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE NODE_HANDLER_PEDIR
# ══════════════════════════════════════════════════════════════════════════════


class TestNodeHandlerPedir:
    """Testes para node_handler_pedir."""

    @patch('src.graph.nodes.processar_pedido')
    def test_delega_para_handler_pedir(self, mock_processar):
        """Deve delegar processamento para o handler."""
        from src.graph.handlers.pedir import ResultadoPedir

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

    def test_itens_extraidos_vazio(self):
        """Itens extraidos vazio deve retornar listas vazias."""
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
        }  # pyright: ignore[reportAssignmentType]
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
        }  # pyright: ignore[reportAssignmentType]
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
        }  # pyright: ignore[reportAssignmentType]
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
        }  # pyright: ignore[reportAssignmentType]
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
        }  # pyright: ignore[reportAssignmentType]
        result = node_handler_remover(state)
        assert not result['carrinho']
        assert (
            'todos os itens' in result['resposta'].lower()
            or 'removido' in result['resposta'].lower()
        )


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
