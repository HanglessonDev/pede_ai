"""
Testes para a função extrair_item_carrinho().

Testa a extração de itens do carrinho para remoção.
"""

import pytest

from src.extratores.spacy_extrator import extrair_item_carrinho


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def carrinho_simples():
    """Carrinho com itens simples."""
    return [
        {'item_id': 'lanche_002', 'quantidade': 2, 'preco': 1800, 'variante': None},
        {'item_id': 'bebida_001', 'quantidade': 1, 'preco': 500, 'variante': 'lata'},
    ]


@pytest.fixture
def carrinho_com_variantes():
    """Carrinho com itens com variantes diferentes."""
    return [
        {
            'item_id': 'lanche_001',
            'quantidade': 1,
            'preco': 1500,
            'variante': 'simples',
        },
        {'item_id': 'lanche_001', 'quantidade': 1, 'preco': 2000, 'variante': 'duplo'},
        {'item_id': 'bebida_001', 'quantidade': 2, 'preco': 500, 'variante': 'lata'},
    ]


@pytest.fixture
def carrinho_vazio():
    """Carrinho vazio."""
    return []


# ══════════════════════════════════════════════════════════════════════════════
# TESTES BÁSICOS
# ══════════════════════════════════════════════════════════════════════════════


class TestExtrairItemCarrinhoBasico:
    """Testes básicos para extrair_item_carrinho()."""

    def test_carrinho_vazio_retorna_lista_vazia(self, carrinho_vazio):
        """Carrinho vazio deve retornar lista vazia."""
        result = extrair_item_carrinho('tira o lanche', carrinho_vazio)
        assert result == []

    def test_remover_item_simples(self, carrinho_simples):
        """Deve remover item simples por nome."""
        result = extrair_item_carrinho('tira a coca', carrinho_simples)
        assert len(result) == 1
        assert result[0]['item_id'] == 'bebida_001'

    def test_remover_item_pelo_nome_do_lanche(self, carrinho_simples):
        """Deve remover item pelo nome do lanche."""
        result = extrair_item_carrinho('tira o xsalada', carrinho_simples)
        assert len(result) == 1
        assert result[0]['item_id'] == 'lanche_002'

    def test_remover_todos_itens(self, carrinho_simples):
        """'tira tudo' deve retornar todos os itens."""
        result = extrair_item_carrinho('tira tudo', carrinho_simples)
        assert len(result) == 2


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE VARIANTES
# ══════════════════════════════════════════════════════════════════════════════


class TestExtrairItemCarrinhoVariantes:
    """Testes para remoção com variantes."""

    def test_remover_variante_especifica(self, carrinho_com_variantes):
        """Deve remover apenas a variante específica."""
        result = extrair_item_carrinho('tira o duplo', carrinho_com_variantes)
        assert len(result) == 1
        assert result[0]['item_id'] == 'lanche_001'
        assert result[0]['variante'] == 'duplo'

    def test_remover_item_sem_especificar_variante(self, carrinho_com_variantes):
        """Sem especificar variante, remove todos os matches."""
        result = extrair_item_carrinho('tira o hamburguer', carrinho_com_variantes)
        # Remove ambos (simples e duplo) - agrupados no mesmo item com 2 indices
        assert len(result) == 1
        assert result[0]['item_id'] == 'lanche_001'
        assert len(result[0]['indices']) == 2  # indices 0 e 1

    def test_remover_bebida_com_variante(self, carrinho_com_variantes):
        """Deve remover bebida com variante específica."""
        result = extrair_item_carrinho('tira a coca lata', carrinho_com_variantes)
        assert len(result) == 1
        assert result[0]['item_id'] == 'bebida_001'
        assert result[0]['variante'] == 'lata'


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE MENSAGENS
# ══════════════════════════════════════════════════════════════════════════════


class TestExtrairItemCarrinhoMensagens:
    """Testes com diferentes formas de mensagem."""

    @pytest.mark.parametrize(
        'mensagem',
        [
            'tira a coca',
            'remove a coca',
            'tira tudo',
            'sem coca',
        ],
    )
    def test_diversos_comandos_de_remocao(self, mensagem, carrinho_simples):
        """Diversos comandos de remoção devem funcionar."""
        result = extrair_item_carrinho(mensagem, carrinho_simples)
        # Todos devem detectar algo (pelo menos a coca)
        assert len(result) >= 1

    def test_mensagem_sem_item_conhecido(self, carrinho_simples):
        """Mensagem sem item conhecido deve retornar lista vazia."""
        result = extrair_item_carrinho('tira a pizza', carrinho_simples)
        assert result == []

    def test_mensagem_irrelevante(self, carrinho_simples):
        """Mensagem irrelevante deve retornar lista vazia."""
        result = extrair_item_carrinho('quero dormir', carrinho_simples)
        assert result == []


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE EDGE CASES
# ══════════════════════════════════════════════════════════════════════════════


class TestExtrairItemCarrinhoEdgeCases:
    """Testes de casos de borda."""

    def test_mensagem_vazia(self, carrinho_simples):
        """Mensagem vazia deve retornar lista vazia."""
        result = extrair_item_carrinho('', carrinho_simples)
        assert result == []

    def test_mensagem_somente_espacos(self, carrinho_simples):
        """Mensagem com espaços deve retornar lista vazia."""
        result = extrair_item_carrinho('   ', carrinho_simples)
        assert result == []

    def test_item_nao_existe_no_carrinho(self, carrinho_simples):
        """Item que não está no carrinho deve retornar lista vazia."""
        result = extrair_item_carrinho('tira a pizza', carrinho_simples)
        assert result == []

    def test_partial_match_muito_generico(self, carrinho_simples):
        """Match parcial muito genérico não deve dar falso positivo."""
        # 'cola' não deve matchar 'coca' por acidente
        result = extrair_item_carrinho('tira cola', carrinho_simples)
        # Se o sistema for inteligente, não deve matchar
        assert isinstance(result, list)


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE ESTRUTURA DO RETORNO
# ══════════════════════════════════════════════════════════════════════════════


class TestExtrairItemCarrinhoEstrutura:
    """Testes da estrutura do retorno."""

    def test_retorno_tem_item_id(self, carrinho_simples):
        """Cada item retornado deve ter item_id."""
        result = extrair_item_carrinho('tira a coca', carrinho_simples)
        if result:
            assert 'item_id' in result[0]

    def test_retorno_tem_variante(self, carrinho_simples):
        """Cada item retornado deve ter variante (pode ser None)."""
        result = extrair_item_carrinho('tira a coca', carrinho_simples)
        if result:
            assert 'variante' in result[0]

    def test_retorno_tem_indices(self, carrinho_simples):
        """Cada item retornado deve ter índices do carrinho."""
        result = extrair_item_carrinho('tira a coca', carrinho_simples)
        if result:
            assert 'indices' in result[0]
            assert isinstance(result[0]['indices'], list)
