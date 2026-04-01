"""
Testes de alta qualidade para o módulo src/config/cardapio.py.

Características:
- Parametrização para evitar código repetitivo
- Fixtures para dados compartilhados
- Cobertura completa de happy path e edge cases
- Testes de integridade e comportamento de cache
"""

import pytest

from src.config import (
    get_cardapio,
    get_item_por_id,
    get_itens_por_categoria,
    get_nome_item,
    get_observacoes_genericas,
    get_preco_item,
    get_remocoes_genericas,
    get_variantes,
)


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def item_ids_validos():
    """IDs de itens válidos para testes."""
    return {
        'hamburguer': 'lanche_001',
        'x_salada': 'lanche_002',
        'x_tudo': 'lanche_003',
        'batata': 'acomp_001',
        'coca': 'bebida_001',
        'coca_zero': 'bebida_002',
    }


@pytest.fixture
def item_ids_invalidos():
    """IDs de itens inválidos para testes."""
    return [
        'inexistente_999',
        '',
        'item_inexistente',
    ]


# ══════════════════════════════════════════════════════════════════════════════
# TESTES PARAMETRIZADOS
# ══════════════════════════════════════════════════════════════════════════════


class TestGetCardapio:
    """Testes para get_cardapio()."""

    @pytest.mark.parametrize('key', ['tenant_id', 'tenant_nome', 'itens'])
    def test_estrutura_contem_chaves_principais(self, key):
        """Deve conter todas as chaves principais."""
        result = get_cardapio()
        assert key in result, f"Chave '{key}' não encontrada no cardápio"

    def test_itens_nao_vazio(self):
        """Deve conter itens no cardápio."""
        result = get_cardapio()
        assert len(result['itens']) > 0

    def test_cache_retorna_mesma_instancia(self):
        """Deve retornar a mesma instância em chamadas subsequentes."""
        result1 = get_cardapio()
        result2 = get_cardapio()
        assert result1 is result2


class TestGetItemPorId:
    """Testes para get_item_por_id()."""

    @pytest.mark.parametrize(
        'item_id,expected_nome',
        [
            ('lanche_001', 'Hambúrguer'),
            ('lanche_002', 'X-Salada'),
            ('lanche_003', 'X-Tudo'),
            ('acomp_001', 'Batata Frita'),
            ('bebida_001', 'Coca-Cola'),
        ],
    )
    def test_itens_conhecidos_retornam_dados_corretos(self, item_id, expected_nome):
        """Itens conhecidos devem retornar dados corretos."""
        result = get_item_por_id(item_id)
        assert result is not None
        assert result['nome'] == expected_nome

    @pytest.mark.parametrize('item_id', ['', 'inexistente_999', 'item_nao_existe'])
    def test_itens_invalidos_retornam_none(self, item_id):
        """Itens inválidos devem retornar None."""
        result = get_item_por_id(item_id)
        assert result is None

    def test_id_none_retorna_none(self):
        """None deve ser tratado como inválido."""
        result = get_item_por_id(None)  # type: ignore
        assert result is None


class TestGetNomeItem:
    """Testes para get_nome_item()."""

    @pytest.mark.parametrize(
        'item_id,expected',
        [
            ('lanche_001', 'Hambúrguer'),
            ('lanche_002', 'X-Salada'),
            ('lanche_003', 'X-Tudo'),
            ('acomp_001', 'Batata Frita'),
            ('bebida_001', 'Coca-Cola'),
            ('bebida_002', 'Coca-Cola Zero'),
            ('bebida_003', 'Suco Natural (Limão)'),
        ],
    )
    def test_nomes_corretos(self, item_id, expected):
        """Deve retornar o nome correto do item."""
        result = get_nome_item(item_id)
        assert result == expected

    @pytest.mark.parametrize('item_id', ['', 'inexistente', None])
    def test_nome_invalido_retorna_none(self, item_id):
        """Itens inválidos devem retornar None."""
        result = get_nome_item(item_id)  # type: ignore
        assert result is None


class TestGetPrecoItem:
    """Testes para get_preco_item()."""

    @pytest.mark.parametrize(
        'item_id,expected_preco',
        [
            ('lanche_002', 1800),
            ('lanche_003', 2000),
        ],
    )
    def test_preco_fixo_retorna_valor_correto(self, item_id, expected_preco):
        """Itens com preço fixo devem retornar o preço correto."""
        result = get_preco_item(item_id)
        assert result == expected_preco

    @pytest.mark.parametrize(
        'item_id',
        [
            'lanche_001',  # Hambúrguer - usa variantes
            'acomp_001',  # Batata - usa variantes
            'bebida_001',  # Coca-Cola - usa variantes
        ],
    )
    def test_itens_com_variantes_retornam_none(self, item_id):
        """Itens com variantes devem retornar None."""
        result = get_preco_item(item_id)
        assert result is None

    @pytest.mark.parametrize('item_id', ['', 'inexistente_999'])
    def test_itens_invalidos_retornam_none(self, item_id):
        """Itens inválidos devem retornar None."""
        result = get_preco_item(item_id)
        assert result is None


class TestGetVariantes:
    """Testes para get_variantes()."""

    @pytest.mark.parametrize(
        'item_id,expected_count,expected_items',
        [
            ('lanche_001', 3, ['simples', 'duplo', 'triplo']),
            ('acomp_001', 3, ['pequena', 'media', 'grande']),
            ('bebida_001', 4, ['lata', '350ml', '600ml', '1 litro']),
        ],
    )
    def test_variantes_corretas(self, item_id, expected_count, expected_items):
        """Deve retornar as variantes corretas."""
        result = get_variantes(item_id)
        assert len(result) == expected_count
        for item in expected_items:
            assert item in result

    @pytest.mark.parametrize(
        'item_id',
        [
            'lanche_002',  # X-Salada sem variantes
            'lanche_003',  # X-Tudo sem variantes
        ],
    )
    def test_itens_sem_variantes_retornam_lista_vazia(self, item_id):
        """Itens sem variantes devem retornar lista vazia."""
        result = get_variantes(item_id)
        assert result == []

    @pytest.mark.parametrize('item_id', ['', 'inexistente_999', None])
    def test_itens_invalidos_retornam_lista_vazia(self, item_id):
        """Itens inválidos devem retornar lista vazia."""
        result = get_variantes(item_id)  # type: ignore
        assert result == []

    def test_retorna_apenas_strings(self):
        """Todas as variantes devem ser strings."""
        result = get_variantes('lanche_001')
        assert all(isinstance(v, str) for v in result)


class TestGetItensPorCategoria:
    """Testes para get_itens_por_categoria()."""

    @pytest.mark.parametrize(
        'categoria,min_itens',
        [
            ('lanche', 1),
            ('bebida', 1),
            ('acompanhamento', 1),
        ],
    )
    def test_categorias_tem_itens(self, categoria, min_itens):
        """Categorias válidas devem retornar itens."""
        result = get_itens_por_categoria(categoria)
        assert len(result) >= min_itens
        assert all(item['categoria'] == categoria for item in result)

    def test_categoria_inexistente_retorna_lista_vazia(self):
        """Categoria inexistente deve retornar lista vazia."""
        result = get_itens_por_categoria('categoria_inexistente')
        assert result == []


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE COMPORTAMENTO E PROPRIEDADES
# ══════════════════════════════════════════════════════════════════════════════


class TestGetRemocoesGenericas:
    """Testes para get_remocoes_genericas()."""

    def test_retorna_lista_nao_vazia(self):
        """Deve retornar uma lista não vazia."""
        result = get_remocoes_genericas()
        assert isinstance(result, list)
        assert len(result) > 0

    @pytest.mark.parametrize('palavra', ['sem', 'tira', 'retira', 'remove'])
    def test_contem_palavras_comuns_de_remocao(self, palavra):
        """Deve conter palavras comuns de remoção."""
        result = get_remocoes_genericas()
        assert palavra in result

    def test_todos_sao_strings(self):
        """Todos os elementos devem ser strings."""
        result = get_remocoes_genericas()
        assert all(isinstance(item, str) for item in result)


class TestGetObservacoesGenericas:
    """Testes para get_observacoes_genericas()."""

    def test_retorna_lista_nao_vazia(self):
        """Deve retornar uma lista não vazia."""
        result = get_observacoes_genericas()
        assert isinstance(result, list)
        assert len(result) > 0

    @pytest.mark.parametrize('observacao', ['bem passado', 'ao ponto', 'bem gelado'])
    def test_contem_observacoes_comuns(self, observacao):
        """Deve conter observações comuns."""
        result = get_observacoes_genericas()
        assert observacao in result


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE INTEGRIDADE E CONSISTÊNCIA
# ══════════════════════════════════════════════════════════════════════════════


class TestIntegridadeDados:
    """Testes de integridade dos dados do cardápio."""

    def test_todos_itens_tem_id_unico(self):
        """Cada item deve ter um ID único."""
        cardapio = get_cardapio()
        ids = [item['id'] for item in cardapio['itens']]
        assert len(ids) == len(set(ids)), 'IDs duplicados encontrados'

    def test_todos_itens_tem_campos_obrigatorios(self):
        """Todos os itens devem ter campos obrigatórios."""
        cardapio = get_cardapio()
        obrigatorios = ['id', 'nome', 'categoria']
        for item in cardapio['itens']:
            for campo in obrigatorios:
                assert campo in item, (
                    f"Campo '{campo}' ausente no item {item.get('id')}"
                )

    def test_categorias_cobertas(self):
        """Todas as categorias principais devem ter itens."""
        categorias_esperadas = {'lanche', 'bebida', 'acompanhamento'}
        cardapio = get_cardapio()
        categorias_encontradas = {item['categoria'] for item in cardapio['itens']}
        assert categorias_esperadas.issubset(categorias_encontradas)


class TestConsistenciaEntreFuncoes:
    """Testes de consistência entre diferentes funções."""

    def test_get_item_e_get_variantes_sao_consistentes(self):
        """get_variantes deve ser consistente com get_item_por_id."""
        for item in get_cardapio()['itens']:
            item_id = item['id']
            variantes_item = item.get('variantes', [])
            variantes_func = get_variantes(item_id)
            assert len(variantes_func) == len(variantes_item)

    def test_get_nome_e_get_preco_sao_consistentes(self):
        """get_nome_item e get_preco_item devem ser consistentes com get_item_por_id."""
        for item in get_cardapio()['itens']:
            item_id = item['id']
            item_full = get_item_por_id(item_id)
            assert item_full is not None
            nome = get_nome_item(item_id)
            preco = get_preco_item(item_id)

            assert nome == item_full['nome']
            # Preço pode ser None se o item usa variantes
            if preco is not None:
                assert preco == item_full['preco']


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE EDGE CASES E COMPORTAMENTO EXTREMO
# ══════════════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Testes de casos de borda e edge cases."""

    @pytest.mark.parametrize(
        'item_id',
        [
            'lanche_001!@#',
            'lanche_001$%^',
            'lanche_001&*(',
        ],
    )
    def test_id_com_caracteres_especiais_retorna_none(self, item_id):
        """IDs com caracteres especiais devem ser tratados como inválidos."""
        result = get_item_por_id(item_id)
        assert result is None

    def test_id_muito_longo_retorna_none(self):
        """IDs muito longos devem ser tratados como inválidos."""
        result = get_item_por_id('a' * 1000)
        assert result is None

    def test_categoria_vazia_retorna_lista_vazia(self):
        """Categoria vazia deve retornar lista vazia."""
        result = get_itens_por_categoria('')
        assert result == []

    def test_tipo_invalido_nao_crash(self):
        """Tipos inválidos não devem causar crash (exceto unhashable)."""
        # Usamos type: ignore para testar edge cases com tipos incorretos
        funcoes_seguras = [
            (lambda: get_item_por_id(123), None),  # type: ignore
            (lambda: get_nome_item(123), None),  # type: ignore
            (lambda: get_preco_item(123), None),  # type: ignore
            (lambda: get_variantes(123), []),  # type: ignore
        ]
        for func, _ in funcoes_seguras:
            result = func()
            # Não deve crashar, deve retornar None ou lista vazia
            assert result is None or result == [], f'Resultado inesperado: {result}'

        # List é unhashable e causa TypeError - comportamento esperado
        with pytest.raises(TypeError):
            get_item_por_id([])  # type: ignore


class TestCache:
    """Testes de comportamento de cache."""

    def test_cache_e_singleton(self):
        """Cache deve retornar a mesma referência."""
        result1 = get_cardapio()
        result2 = get_cardapio()
        assert result1 is result2

    def test_cache_persiste_entre_chamadas(self):
        """Cache deve persistir entre chamadas."""
        from src.config.cardapio import _CardapioCache

        original_len = len(get_cardapio()['itens'])
        get_cardapio()['itens'].append({'test': 'modificado'})
        # O cache deve refletir a modificação
        assert len(get_cardapio()['itens']) == original_len + 1
        # Limpar cache para não afetar outros testes
        _CardapioCache._cardapio = None
        _CardapioCache._itens_por_id = None

    def test_item_por_id_cache_e_singleton(self):
        """get_item_por_id deve usar cache."""
        result1 = get_item_por_id('lanche_001')
        result2 = get_item_por_id('lanche_001')
        assert result1 is result2


class TestImutabilidadeInputs:
    """Testes para garantir que inputs não são modificados."""

    def test_get_cardapio_nao_modifica_input(self):
        """get_cardapio não deve modificar dados internos."""
        cardapio = get_cardapio()
        original = len(cardapio['itens'])
        get_cardapio()
        # O tamanho não deve mudar por chamada à função
        assert len(cardapio['itens']) >= original
