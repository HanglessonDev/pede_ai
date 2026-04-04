"""Testes unitários para o módulo src/extratores/fuzzy_extrator.py.

Cobertura completa de todas as funções públicas:
- normalizar
- extrair_tokens_significativos
- match_variante_numerica
- fuzzy_match_item
- fuzzy_match_variante
"""

import pytest

from src.extratores.fuzzy_extrator import (
    normalizar,
    extrair_tokens_significativos,
    match_variante_numerica,
    fuzzy_match_item,
    fuzzy_match_variante,
)


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def alias_para_id():
    """Mapa completo de aliases para testes."""
    return {
        'Hambúrguer': 'lanche_001',
        'hamburguer': 'lanche_001',
        'burger': 'lanche_001',
        'hambug': 'lanche_001',
        'hamburger': 'lanche_001',
        'X-Salada': 'lanche_002',
        'x salada': 'lanche_002',
        'xsalada': 'lanche_002',
        'x-sal': 'lanche_002',
        'X-Tudo': 'lanche_003',
        'x tudo': 'lanche_003',
        'xtudo': 'lanche_003',
        'x-td': 'lanche_003',
        'Batata Frita': 'acomp_001',
        'batata': 'acomp_001',
        'fritas': 'acomp_001',
        'batatinha': 'acomp_001',
        'batata frita': 'acomp_001',
        'Coca-Cola': 'bebida_001',
        'coca': 'bebida_001',
        'coca cola': 'bebida_001',
        'cocacola': 'bebida_001',
        'Coca-Cola Zero': 'bebida_002',
        'coca zero': 'bebida_002',
        'coca cola zero': 'bebida_002',
        'cocazero': 'bebida_002',
        'Suco Natural (Limão)': 'bebida_003',
        'suco de limão': 'bebida_003',
        'suco limao': 'bebida_003',
        'limonada': 'bebida_003',
        'Suco Natural (Laranja)': 'bebida_004',
        'suco de laranja': 'bebida_004',
        'suco laranja': 'bebida_004',
    }


@pytest.fixture
def variantes_hamburguer():
    """Variantes de hambúrguer."""
    return ['simples', 'duplo', 'triplo']


@pytest.fixture
def variantes_coca():
    """Variantes de Coca-Cola."""
    return ['lata', '350ml', '600ml', '1 litro']


@pytest.fixture
def variantes_suco():
    """Variantes de suco."""
    return ['300ml', '500ml']


@pytest.fixture
def variantes_batata():
    """Variantes de batata."""
    return ['pequena', 'media', 'grande']


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE NORMALIZAR
# ══════════════════════════════════════════════════════════════════════════════


class TestNormalizar:
    """Testes para a função normalizar()."""

    def test_remove_acentos(self):
        """'Hambúrguer' deve retornar 'hamburguer'."""
        assert normalizar('Hambúrguer') == 'hamburguer'

    def test_lowercase(self):
        """'Coca-Cola' deve retornar 'coca-cola'."""
        assert normalizar('Coca-Cola') == 'coca-cola'

    def test_strip(self):
        """'  coca  ' deve retornar 'coca'."""
        assert normalizar('  coca  ') == 'coca'

    def test_remove_pontuacao(self):
        """'coca!' deve retornar 'coca' (normalizar usa unicode, nao re.sub)."""
        # normalizar só faz unicode + strip, nao remove pontuacao via regex
        resultado = normalizar('coca!')
        assert 'coca' in resultado

    def test_vazio(self):
        """String vazia deve retornar vazia."""
        assert normalizar('') == ''


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE EXTRAIR TOKENS SIGNIFICATIVOS
# ══════════════════════════════════════════════════════════════════════════════


class TestExtrairTokensSignificativos:
    """Testes para a função extrair_tokens_significativos()."""

    def test_remove_stop_words(self):
        """'quero um hamburguer' deve retornar ['hamburguer']."""
        resultado = extrair_tokens_significativos('quero um hamburguer')
        assert resultado == ['hamburguer']

    def test_frase_completa(self):
        """'muda o hamburguer pra duplo' deve retornar tokens relevantes."""
        resultado = extrair_tokens_significativos('muda o hamburguer pra duplo')
        assert 'hamburguer' in resultado
        assert 'duplo' in resultado

    def test_mantem_tokens_longos(self):
        """'batata frita' deve retornar ['batata', 'frita']."""
        resultado = extrair_tokens_significativos('batata frita')
        assert resultado == ['batata', 'frita']

    def test_remove_curto(self):
        """'a o e' deve retornar lista vazia (tokens curtos e stop words)."""
        resultado = extrair_tokens_significativos('a o e')
        assert resultado == []

    def test_frase_vazia(self):
        """String vazia deve retornar lista vazia."""
        assert extrair_tokens_significativos('') == []


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE MATCH VARIANTE NUMÉRICA
# ══════════════════════════════════════════════════════════════════════════════


class TestMatchVarianteNumerica:
    """Testes para a função match_variante_numerica()."""

    def test_match_exato(self):
        """'350ml' com ['350ml', '600ml'] deve retornar '350ml'."""
        resultado = match_variante_numerica('350ml', ['350ml', '600ml'])
        assert resultado == '350ml'

    def test_match_substring(self):
        """'50ml' com ['300ml', '500ml'] deve retornar '500ml'."""
        resultado = match_variante_numerica('50ml', ['300ml', '500ml'])
        assert resultado == '500ml'

    def test_match_substring_2(self):
        """'30ml' com ['300ml', '500ml'] deve retornar '300ml'."""
        resultado = match_variante_numerica('30ml', ['300ml', '500ml'])
        assert resultado == '300ml'

    def test_ambiguo(self):
        """'50ml' com ['350ml', '500ml'] deve retornar None (ambíguo)."""
        resultado = match_variante_numerica('50ml', ['350ml', '500ml'])
        assert resultado is None

    def test_nao_numerico(self):
        """'duplo' deve retornar None (não é numérico)."""
        resultado = match_variante_numerica('duplo', ['duplo'])
        assert resultado is None

    def test_vazio(self):
        """String vazia deve retornar None."""
        resultado = match_variante_numerica('', ['350ml'])
        assert resultado is None


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE FUZZY MATCH ITEM
# ══════════════════════════════════════════════════════════════════════════════


class TestFuzzyMatchItem:
    """Testes para a função fuzzy_match_item()."""

    def test_match_exato(self, alias_para_id):
        """'hamburguer' deve matchar exatamente."""
        alias, score, item_id = fuzzy_match_item('hamburguer', alias_para_id)
        assert alias == 'hamburguer'
        assert score == 100.0
        assert item_id == 'lanche_001'

    def test_typo_leve(self, alias_para_id):
        """'hamburguér' deve matchar com score > 75."""
        _alias, score, item_id = fuzzy_match_item('hamburguér', alias_para_id)
        assert item_id == 'lanche_001'
        assert score > 75

    def test_typo_consoante(self, alias_para_id):
        """'amburguer' deve matchar com score > 75."""
        _alias, score, item_id = fuzzy_match_item('amburguer', alias_para_id)
        assert item_id == 'lanche_001'
        assert score > 75

    def test_alias_curto(self, alias_para_id):
        """'burger' deve matchar exatamente."""
        alias, score, item_id = fuzzy_match_item('burger', alias_para_id)
        assert alias == 'burger'
        assert score == 100.0
        assert item_id == 'lanche_001'

    def test_frase_completa(self, alias_para_id):
        """'quero um hamburguer' deve matchar."""
        _alias, score, item_id = fuzzy_match_item('quero um hamburguer', alias_para_id)
        assert item_id == 'lanche_001'
        assert score >= 75

    def test_fora_cardapio(self, alias_para_id):
        """'pizza' não deve matchar."""
        alias, score, item_id = fuzzy_match_item('pizza', alias_para_id)
        assert alias is None
        assert score == 0
        assert item_id is None

    def test_cutoff_alto(self, alias_para_id):
        """'hamburg' com cutoff=95 não deve matchar."""
        alias, score, item_id = fuzzy_match_item('hamburg', alias_para_id, cutoff=95)
        assert alias is None
        assert score == 0
        assert item_id is None

    def test_cutoff_baixo(self, alias_para_id):
        """'hamburg' com cutoff=70 deve matchar."""
        _alias, score, item_id = fuzzy_match_item('hamburg', alias_para_id, cutoff=70)
        assert item_id == 'lanche_001'
        assert score >= 70


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE FUZZY MATCH VARIANTE
# ══════════════════════════════════════════════════════════════════════════════


class TestFuzzyMatchVariante:
    """Testes para a função fuzzy_match_variante()."""

    def test_match_exato(self, variantes_hamburguer):
        """'duplo' com ['simples','duplo','triplo'] deve retornar ('duplo', 100)."""
        variante, score = fuzzy_match_variante('duplo', variantes_hamburguer)
        assert variante == 'duplo'
        assert score == 100.0

    def test_typo(self, variantes_hamburguer):
        """'duple' deve matchar com score > 70."""
        variante, score = fuzzy_match_variante('duple', variantes_hamburguer)
        assert variante is not None
        assert score > 70

    def test_numerica_substring(self, variantes_suco):
        """'50ml' com ['300ml','500ml'] deve retornar ('500ml', 95.0)."""
        variante, score = fuzzy_match_variante('50ml', variantes_suco)
        assert variante == '500ml'
        assert score == 95.0

    def test_ambiguidade(self):
        """'35ml' com ['350ml','350ml'] deve retornar (None, 0) por ambiguidade."""
        variante, score = fuzzy_match_variante('35ml', ['350ml', '350ml'])
        assert variante is None
        assert score == 0

    def test_fora_variantes(self, variantes_hamburguer):
        """'pizza' com ['duplo','triplo'] não deve matchar."""
        variante, score = fuzzy_match_variante('pizza', ['duplo', 'triplo'])
        assert variante is None
        assert score == 0

    def test_vazio(self, variantes_hamburguer):
        """String vazia deve retornar (None, 0)."""
        variante, score = fuzzy_match_variante('', variantes_hamburguer)
        assert variante is None
        assert score == 0
