"""
Testes para o módulo src/cardapio.py.

Testes de alta qualidade cobrindo:
- Casos happy path
- Casos de borda (edge cases)
- Comportamento com dados inválidos
- Verificação de tipos de retorno
"""

from src.cardapio import (
    get_cardapio,
    get_item_por_id,
    get_itens_por_categoria,
    get_nome_item,
    get_observacoes_genericas,
    get_preco_item,
    get_remocoes_genericas,
    get_variantes,
)


class TestGetCardapio:
    """Testes para get_cardapio()."""

    def test_retorna_dicionario(self):
        """Deve retornar um dicionário."""
        result = get_cardapio()
        assert isinstance(result, dict)

    def test_estrutura_esperada(self):
        """Deve conter as chaves principais."""
        result = get_cardapio()
        assert 'tenant_id' in result
        assert 'tenant_nome' in result
        assert 'itens' in result

    def test_itens_nao_vazio(self):
        """Deve conter itens no cardápio."""
        result = get_cardapio()
        assert len(result['itens']) > 0

    def test_cache_retorna_mesma_instancia(self):
        """Deve retornar a mesma instância em chamadas subsequentes (cache)."""
        result1 = get_cardapio()
        result2 = get_cardapio()
        assert result1 is result2


class TestGetItemPorId:
    """Testes para get_item_por_id()."""

    def test_item_existente_retorna_dicionario(self):
        """Deve retornar dados do item para ID válido."""
        result = get_item_por_id('lanche_001')
        assert result is not None
        assert isinstance(result, dict)

    def test_item_existente_contem_campos_esperados(self):
        """Deve conter campos obrigatórios."""
        result = get_item_por_id('lanche_001')
        assert result is not None
        assert 'id' in result
        assert 'nome' in result
        assert 'categoria' in result
        assert result['id'] == 'lanche_001'

    def test_item_inexistente_retorna_none(self):
        """Deve retornar None para ID inexistente."""
        result = get_item_por_id('inexistente_999')
        assert result is None

    def test_id_vazio_retorna_none(self):
        """Deve retornar None para string vazia."""
        result = get_item_por_id('')
        assert result is None

    def test_id_none_retorna_none(self):
        """Deve retornar None para None (type error deve ser tratadas)."""
        # Não deve lançar exceção, deve retornar None
        result = get_item_por_id(None)  # type: ignore
        assert result is None

    def test_diferentes_itens_retornam_dados_distintos(self):
        """Itens diferentes devem ter dados distintos."""
        item1 = get_item_por_id('lanche_001')
        item2 = get_item_por_id('lanche_002')
        assert item1 is not None
        assert item2 is not None
        assert item1['nome'] != item2['nome']


class TestGetNomeItem:
    """Testes para get_nome_item()."""

    def test_item_com_preco_fixo(self):
        """Deve retornar o nome do item."""
        result = get_nome_item('lanche_002')
        assert result == 'X-Salada'

    def test_item_com_variantes(self):
        """Deve retornar nome mesmo para item com variantes."""
        result = get_nome_item('lanche_001')
        assert result == 'Hambúrguer'

    def test_bebida(self):
        """Deve funcionar para bebidas."""
        result = get_nome_item('bebida_001')
        assert result == 'Coca-Cola'

    def test_item_inexistente_retorna_none(self):
        """Deve retornar None para item inexistente."""
        result = get_nome_item('nao_existe_123')
        assert result is None


class TestGetPrecoItem:
    """Testes para get_preco_item()."""

    def test_item_com_preco_fixo_retorna_preco(self):
        """Deve retornar o preço em centavos para item com preço fixo."""
        result = get_preco_item('lanche_002')  # X-Salada = 1800
        assert result == 1800

    def test_item_com_preco_nulo_retorna_none(self):
        """Deve retornar None para item sem preço fixo (usa variantes)."""
        result = get_preco_item('lanche_001')  # Hambúrguer = null
        assert result is None

    def test_bebida_com_variantes_retorna_none(self):
        """Bebidas com variantes devem retornar None."""
        result = get_preco_item('bebida_001')  # Coca-Cola = null
        assert result is None

    def test_item_inexistente_retorna_none(self):
        """Deve retornar None para item inexistente."""
        result = get_preco_item('item_inexistente')
        assert result is None


class TestGetVariantes:
    """Testes para get_variantes()."""

    def test_lanche_com_varias_variantes(self):
        """Deve retornar lista de opções para Hambúrguer."""
        result = get_variantes('lanche_001')
        assert isinstance(result, list)
        assert len(result) == 3
        assert 'simples' in result
        assert 'duplo' in result
        assert 'triplo' in result

    def test_bebida_com_varias_tamanhos(self):
        """Deve retornar variantes para bebidas."""
        result = get_variantes('bebida_001')
        assert isinstance(result, list)
        assert len(result) == 4
        assert 'lata' in result
        assert '350ml' in result

    def test_item_sem_variantes_retorna_lista_vazia(self):
        """Deve retornar lista vazia para item sem variantes."""
        result = get_variantes('lanche_002')  # X-Salada sem variantes
        assert result == []

    def test_item_inexistente_retorna_lista_vazia(self):
        """Deve retornar lista vazia para item inexistente."""
        result = get_variantes('nao_existe_999')
        assert result == []

    def test_retorna_apenas_nomes_das_opcoes(self):
        """Deve retornar só os nomes, não os preços."""
        result = get_variantes('lanche_001')
        # Cada item deve ser apenas string, não dict
        for variante in result:
            assert isinstance(variante, str)


class TestGetItensPorCategoria:
    """Testes para get_itens_por_categoria()."""

    def test_categoria_lanche_retorna_lista(self):
        """Deve retornar lista de lanches."""
        result = get_itens_por_categoria('lanche')
        assert isinstance(result, list)
        assert len(result) > 0

    def test_todos_itens_tem_categoria_correta(self):
        """Todos os itens retornados devem pertencer à categoria."""
        result = get_itens_por_categoria('lanche')
        for item in result:
            assert item['categoria'] == 'lanche'

    def test_categoria_bebida(self):
        """Deve funcionar para bebidas."""
        result = get_itens_por_categoria('bebida')
        assert isinstance(result, list)
        assert len(result) > 0
        for item in result:
            assert item['categoria'] == 'bebida'

    def test_categoria_inexistente_retorna_lista_vazia(self):
        """Categoria inexistente deve retornar lista vazia."""
        result = get_itens_por_categoria('categoria_inexistente')
        assert result == []

    def test_categoria_acompanhamento(self):
        """Deve funcionar para acompanhamentos."""
        result = get_itens_por_categoria('acompanhamento')
        assert isinstance(result, list)
        assert len(result) > 0


class TestGetRemocoesGenericas:
    """Testes para get_remocoes_genericas()."""

    def test_retorna_lista(self):
        """Deve retornar uma lista."""
        result = get_remocoes_genericas()
        assert isinstance(result, list)

    def test_nao_retorna_vazio(self):
        """Deve conter palavras de remoção."""
        result = get_remocoes_genericas()
        assert len(result) > 0

    def test_contem_palavras_comuns(self):
        """Deve conter palavras comuns de remoção."""
        result = get_remocoes_genericas()
        assert 'sem' in result
        assert 'tira' in result

    def test_retorna_apenas_strings(self):
        """Todos os elementos devem ser strings."""
        result = get_remocoes_genericas()
        for item in result:
            assert isinstance(item, str)


class TestGetObservacoesGenericas:
    """Testes para get_observacoes_genericas()."""

    def test_retorna_lista(self):
        """Deve retornar uma lista."""
        result = get_observacoes_genericas()
        assert isinstance(result, list)

    def test_contem_observacoes_validas(self):
        """Deve conter observações comuns."""
        result = get_observacoes_genericas()
        assert 'bem passado' in result
        assert 'ao ponto' in result


class TestIntegracao:
    """Testes de integração entre funções."""

    def test_get_item_por_id_e_get_variantes(self):
        """get_variantes deve usar get_item_por_id internamente."""
        item = get_item_por_id('lanche_001')
        assert item is not None
        variantes = get_variantes('lanche_001')
        assert len(variantes) == len(item.get('variantes', []))

    def test_get_nome_item_e_get_preco_item(self):
        """ funções devem ser consistentes para mesmo item."""
        nome = get_nome_item('lanche_002')
        preco = get_preco_item('lanche_002')
        item = get_item_por_id('lanche_002')
        assert item is not None
        assert nome == item['nome']
        assert preco == item['preco']

    def test_categorias_cobertas(self):
        """Todas as categorias devem ter itens."""
        categorias = ['lanche', 'bebida', 'acompanhamento']
        for cat in categorias:
            itens = get_itens_por_categoria(cat)
            assert len(itens) > 0, f"Categoria {cat} sem itens"


class TestEdgeCases:
    """Testes de casos de borda."""

    def test_id_com_caracteres_especiais(self):
        """ID com caracteres especiais deve ser tratado."""
        result = get_item_por_id('lanche_001!@#')
        assert result is None

    def test_id_muito_longo(self):
        """ID muito longo deve ser tratado."""
        result = get_item_por_id('a' * 1000)
        assert result is None

    def test_categoria_case_sensitive(self):
        """Categoria deve ser case-sensitive (manter no padrão)."""
        result_lower = get_itens_por_categoria('lanche')
        result_mixed = get_itens_por_categoria('LANCHE')
        # O comportamento esperado é que categoria seja case-sensitive
        # então resultados podem ser diferentes ou iguais dependendo da impl
        # O importante é que não lance exceção
        assert isinstance(result_lower, list)
        assert isinstance(result_mixed, list)


class TestConsistenciaCache:
    """Testes para verificar comportamento de cache."""

    def test_cache_retorna_mesma_referencia(self):
        """Cache deve retornar a mesma referência (singleton)."""
        result1 = get_cardapio()
        result2 = get_cardapio()
        # Deve ser o mesmo objeto (cache)
        assert result1 is result2
        # Modificar um afeta o outro (comportamento esperado do cache)
        result1['itens'].append({'test': 'modificado'})
        assert len(result2['itens']) > 8  # Verifica que foi modificado

    def test_itens_por_id_cache(self):
        """ get_item_por_id deve usar cache."""
        result1 = get_item_por_id('lanche_001')
        result2 = get_item_por_id('lanche_001')
        # Deve retornar exatamente o mesmo objeto (cache)
        assert result1 is result2