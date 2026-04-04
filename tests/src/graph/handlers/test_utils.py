"""Testes para utilitários compartilhados entre handlers."""

from unittest.mock import patch

from src.graph.handlers.utils import formatar_carrinho


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE formatar_carrinho
# ══════════════════════════════════════════════════════════════════════════════


class TestFormatarCarrinho:
    """Testes para formatar_carrinho."""

    def test_carrinho_vazio_retorna_string_vazia(self):
        """Carrinho vazio deve retornar string vazia."""
        result = formatar_carrinho([])
        assert result == ''

    def test_um_item_formatado_corretamente(self):
        """Um item deve ser formatado com quantidade, nome e preço."""
        with patch('src.graph.handlers.utils.get_nome_item', return_value='Hambúrguer'):
            carrinho = [
                {'item_id': 'lanche_001', 'quantidade': 1, 'preco': 1500},
            ]
            result = formatar_carrinho(carrinho)
            assert result == '1x Hambúrguer — R$ 15.00'

    def test_multiplos_itens_um_por_linha(self):
        """Múltiplos itens devem ter uma linha por item."""
        with patch('src.graph.handlers.utils.get_nome_item') as mock_nome:
            mock_nome.side_effect = lambda x: (
                'Hambúrguer' if x == 'lanche_001' else 'Coca-Cola'
            )
            carrinho = [
                {'item_id': 'lanche_001', 'quantidade': 1, 'preco': 1500},
                {'item_id': 'bebida_001', 'quantidade': 2, 'preco': 500},
            ]
            result = formatar_carrinho(carrinho)
            linhas = result.split('\n')
            assert len(linhas) == 2
            assert '1x Hambúrguer' in linhas[0]
            assert '2x Coca-Cola' in linhas[1]

    def test_usa_item_id_quando_nome_none(self):
        """Quando get_nome_item retorna None, usa item_id."""
        with patch('src.graph.handlers.utils.get_nome_item', return_value=None):
            carrinho = [
                {'item_id': 'item_999', 'quantidade': 1, 'preco': 1000},
            ]
            result = formatar_carrinho(carrinho)
            assert 'item_999' in result

    def test_preco_formatado_com_duas_casas_decimais(self):
        """Preço deve ser formatado com duas casas decimais."""
        with patch('src.graph.handlers.utils.get_nome_item', return_value='Suco'):
            carrinho = [
                {'item_id': 'bebida_003', 'quantidade': 1, 'preco': 500},
            ]
            result = formatar_carrinho(carrinho)
            assert '5.00' in result

    def test_preco_valores_decimais_corretos(self):
        """Preços com valores não redondos devem formatar corretamente."""
        with patch('src.graph.handlers.utils.get_nome_item', return_value='Coca Zero'):
            carrinho = [
                {'item_id': 'bebida_002', 'quantidade': 1, 'preco': 350},
            ]
            result = formatar_carrinho(carrinho)
            assert '3.50' in result
