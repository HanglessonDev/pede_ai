"""Testes para handler de remocao de itens do carrinho."""

import pytest
from unittest.mock import patch

from src.graph.handlers.remocao_handler import processar_remocao, ResultadoRemover


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def carrinho_vazio():
    """Carrinho vazio."""
    return []


@pytest.fixture
def carrinho_um_item():
    """Carrinho com um item."""
    return [
        {
            'item_id': 'lanche_001',
            'quantidade': 1,
            'preco': 1500,
            'variante': 'simples',
        },
    ]


@pytest.fixture
def carrinho_multiplo():
    """Carrinho com multiplos itens."""
    return [
        {
            'item_id': 'lanche_001',
            'quantidade': 1,
            'preco': 1500,
            'variante': 'simples',
        },
        {
            'item_id': 'bebida_001',
            'quantidade': 1,
            'preco': 500,
            'variante': 'lata',
        },
    ]


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE CARRINHO VAZIO
# ══════════════════════════════════════════════════════════════════════════════


class TestCarrinhoVazio:
    """Testes para remocao com carrinho vazio."""

    def test_retorna_erro_carrinho_vazio(self, carrinho_vazio):
        """Carrinho vazio deve retornar mensagem de erro."""
        result = processar_remocao(carrinho_vazio, 'tira a coca')
        assert 'vazio' in result.resposta.lower()
        assert result.etapa == 'inicio'
        assert result.carrinho == []


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE ITEM NÃO ENCONTRADO
# ══════════════════════════════════════════════════════════════════════════════


class TestItemNaoEncontrado:
    """Testes para remocao de item que nao existe no carrinho."""

    def test_item_nao_encontrado(self, carrinho_um_item):
        """Item nao encontrado deve retornar mensagem de erro."""
        with patch(
            'src.graph.handlers.remocao_handler.extrair_item_carrinho', return_value=[]
        ):
            result = processar_remocao(carrinho_um_item, 'tira a pizza')
            assert 'não encontrei' in result.resposta.lower()
            assert result.etapa == 'carrinho'
            assert len(result.carrinho) == 1


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE REMOCAO COM SUCESSO
# ══════════════════════════════════════════════════════════════════════════════


class TestRemocaoSucesso:
    """Testes para remocao bem-sucedida de itens."""

    def test_remove_unico_item_limpa_carrinho(self, carrinho_um_item):
        """Remover o unico item deve limpar o carrinho."""
        with patch(
            'src.graph.handlers.remocao_handler.extrair_item_carrinho',
            return_value=[{'item_id': 'lanche_001', 'indices': [0]}],
        ):
            result = processar_remocao(carrinho_um_item, 'tira o hamburguer')
            assert result.carrinho == []
            assert result.etapa == 'inicio'
            assert 'Todos os itens foram removidos' in result.resposta

    def test_remove_um_de_multiplos(self, carrinho_multiplo):
        """Remover um item de multiplos deve manter os restantes."""
        with patch(
            'src.graph.handlers.remocao_handler.extrair_item_carrinho',
            return_value=[{'item_id': 'bebida_001', 'indices': [1]}],
        ):
            result = processar_remocao(carrinho_multiplo, 'tira a coca')
            assert len(result.carrinho) == 1
            assert result.carrinho[0]['item_id'] == 'lanche_001'
            assert result.etapa == 'carrinho'

    def test_remove_multiplos_itens(self, carrinho_multiplo):
        """Remover multiplos itens deve limpar o carrinho."""
        with patch(
            'src.graph.handlers.remocao_handler.extrair_item_carrinho',
            return_value=[
                {'item_id': 'lanche_001', 'indices': [0]},
                {'item_id': 'bebida_001', 'indices': [1]},
            ],
        ):
            result = processar_remocao(carrinho_multiplo, 'tira tudo')
            assert result.carrinho == []
            assert result.etapa == 'inicio'

    def test_resposta_mostra_carrinho_atualizado(self, carrinho_multiplo):
        """Resposta deve mostrar carrinho atualizado apos remocao."""
        with patch(
            'src.graph.handlers.remocao_handler.extrair_item_carrinho',
            return_value=[{'item_id': 'bebida_001', 'indices': [1]}],
        ):
            result = processar_remocao(carrinho_multiplo, 'tira a coca')
            assert 'Itens removidos!' in result.resposta
            assert 'Seu pedido:' in result.resposta


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE ResultadoRemover
# ══════════════════════════════════════════════════════════════════════════════


class TestResultadoRemover:
    """Testes para o dataclass ResultadoRemover."""

    def test_to_dict_contem_chaves(self):
        """to_dict deve conter todas as chaves esperadas."""
        result = ResultadoRemover(
            carrinho=[{'item_id': 'lanche_001', 'preco': 1500}],
            resposta='Itens removidos!',
            etapa='carrinho',
        )
        d = result.to_dict()
        assert 'carrinho' in d
        assert 'resposta' in d
        assert 'etapa' in d

    def test_to_dict_valores_corretos(self):
        """to_dict deve mapear valores corretamente."""
        carrinho = [{'item_id': 'lanche_001', 'preco': 1500}]
        result = ResultadoRemover(
            carrinho=carrinho,
            resposta='Itens removidos!',
            etapa='carrinho',
        )
        d = result.to_dict()
        assert d['carrinho'] == carrinho
        assert d['resposta'] == 'Itens removidos!'
        assert d['etapa'] == 'carrinho'
