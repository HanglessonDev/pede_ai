"""Testes para handler de remoção de itens do carrinho."""

import pytest
from unittest.mock import patch

from src.graph.handlers.remover import processar_remocao, ResultadoRemover


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def carrinho_vazio():
    """Carrinho vazio."""
    return []


@pytest.fixture
def carrinho_com_um_item():
    """Carrinho com um item."""
    return [
        {
            'item_id': 'lanche_001',
            'nome': 'Hambúrguer',
            'quantidade': 1,
            'preco': 1500,
            'variante': 'simples',
        },
    ]


@pytest.fixture
def carrinho_multiplo():
    """Carrinho com múltiplos itens."""
    return [
        {
            'item_id': 'lanche_001',
            'nome': 'Hambúrguer',
            'quantidade': 1,
            'preco': 1500,
            'variante': 'simples',
        },
        {
            'item_id': 'bebida_001',
            'nome': 'Coca-Cola',
            'quantidade': 1,
            'preco': 500,
            'variante': 'lata',
        },
    ]


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE CARRINHO VAZIO
# ══════════════════════════════════════════════════════════════════════════════


class TestCarrinhoVazio:
    """Testes para remoção com carrinho vazio."""

    def test_retorna_erro_carrinho_vazio(self, carrinho_vazio):
        """Carrinho vazio deve retornar mensagem de erro."""
        result = processar_remocao(carrinho_vazio, 'tira a coca')
        assert result.resposta == 'Seu carrinho está vazio! Não há nada para remover.'
        assert result.etapa == 'inicio'
        assert result.carrinho == []


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE ITEM NÃO ENCONTRADO
# ══════════════════════════════════════════════════════════════════════════════


class TestItemNaoEncontrado:
    """Testes para remoção de item que não existe no carrinho."""

    def test_item_nao_encontrado(self, carrinho_com_um_item):
        """Item não encontrado deve retornar mensagem de erro."""
        with patch('src.graph.handlers.remover.extrair_item_carrinho', return_value=[]):
            result = processar_remocao(carrinho_com_um_item, 'tira a pizza')
            assert result.resposta == 'Não encontrei esse item no seu carrinho.'
            assert result.etapa == 'carrinho'
            assert len(result.carrinho) == 1


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE REMOÇÃO COM SUCESSO
# ══════════════════════════════════════════════════════════════════════════════


class TestRemocaoSucesso:
    """Testes para remoção bem-sucedida de itens."""

    def test_remove_unico_item_limpa_carrinho(self, carrinho_com_um_item):
        """Remover o único item deve limpar o carrinho."""
        with patch(
            'src.graph.handlers.remover.extrair_item_carrinho',
            return_value=[{'item_id': 'lanche_001', 'indices': [0]}],
        ):
            result = processar_remocao(carrinho_com_um_item, 'tira o hambúrguer')
            assert result.carrinho == []
            assert result.etapa == 'inicio'
            assert 'Todos os itens foram removidos' in result.resposta

    def test_remove_um_de_multiplos(self, carrinho_multiplo):
        """Remover um item de múltiplos deve manter os restantes."""
        with patch(
            'src.graph.handlers.remover.extrair_item_carrinho',
            return_value=[{'item_id': 'bebida_001', 'indices': [1]}],
        ):
            result = processar_remocao(carrinho_multiplo, 'tira a coca')
            assert len(result.carrinho) == 1
            assert result.carrinho[0]['item_id'] == 'lanche_001'
            assert result.etapa == 'carrinho'

    def test_remove_multiplos_itens(self, carrinho_multiplo):
        """Remover múltiplos itens deve limpar o carrinho."""
        with patch(
            'src.graph.handlers.remover.extrair_item_carrinho',
            return_value=[
                {'item_id': 'lanche_001', 'indices': [0]},
                {'item_id': 'bebida_001', 'indices': [1]},
            ],
        ):
            result = processar_remocao(carrinho_multiplo, 'tira tudo')
            assert result.carrinho == []
            assert result.etapa == 'inicio'

    def test_resposta_mostra_carrinho_atualizado(self, carrinho_multiplo):
        """Resposta deve mostrar carrinho atualizado após remoção."""
        with patch(
            'src.graph.handlers.remover.extrair_item_carrinho',
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
