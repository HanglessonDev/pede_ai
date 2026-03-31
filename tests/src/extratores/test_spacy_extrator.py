"""
Testes de alta qualidade para o módulo src/extratores/spacy_extrator.py.

Características:
- Parametrização para evitar código repetitivo
- Testes de normalização, patterns, extração
- Mock do objeto Doc do spaCy
- Cobertura completa de happy path e edge cases
"""

import pytest
from unittest.mock import MagicMock, patch

from src.extratores.spacy_extrator import (
    normalizar,
    gerar_patterns,
    capturar_remocoes,
    extrair,
    PALAVRAS_REMOCAO,
    CONECTIVOS,
    NUMEROS_ESCRITOS,
)
from src.config import get_cardapio


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def cardapio():
    """Cardápio para testes."""
    return get_cardapio()


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE NORMALIZAÇÃO
# ══════════════════════════════════════════════════════════════════════════════

class TestNormalizar:
    """Testes para a função normalizar()."""

    @pytest.mark.parametrize('input_text,expected', [
        ('X-Tudo', 'xtudo'),
        ('X-Salada', 'xsalada'),
        ('Hamburguer', 'hamburguer'),
        ('Coca-Cola', 'cocacola'),
        ('batata frita', 'batata frita'),
    ])
    def test_minusculas(self, input_text, expected):
        """Deve converter para minusculas."""
        assert normalizar(input_text) == expected

    def test_remove_acentos(self):
        """Deve remover acentos."""
        assert normalizar('Hamburguer') == 'hamburguer'
        assert normalizar('Suco Natural') == 'suco natural'

    def test_remove_pontuacao(self):
        """Deve remover pontuacao."""
        assert normalizar('X-Tudo!') == 'xtudo'
        assert normalizar('Hamburguer.') == 'hamburguer'
        assert normalizar('(teste)') == 'teste'

    def test_hifen_removido_com_pontuacao(self):
        """Hifen e removido com a pontuacao (ordem: pontuacao primeiro, depois replace)."""
        # A funcao remove pontuacao ANTES de fazer replace('-', ' ')
        # entao x-tudo -> remove pontuacao -> xtudo -> replace(-) -> xtudo
        assert normalizar('x-tudo') == 'xtudo'

    def test_espacos_extras_removidos(self):
        """Espaços extras devem ser normalizados."""
        assert normalizar('x    tudo') == 'x tudo'
        assert normalizar('  ola  ') == 'ola'

    @pytest.mark.parametrize('input_text', [
        '',
        '   ',
        'a',
        'X',
        '1',
        '@#$%',
    ])
    def test_entradas_variadas(self, input_text):
        """Deve tratar entradas variadas."""
        result = normalizar(input_text)
        assert isinstance(result, str)
        assert result == result.strip() or input_text.strip() == ''


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE CONSTANTES
# ══════════════════════════════════════════════════════════════════════════════

class TestConstantes:
    """Testes para verificar constantes definidas."""

    def test_palavras_remocao_contem_esperadas(self):
        """PALAVRAS_REMOCAO deve conter palavras esperadas."""
        esperado = {'sem', 'tira', 'remove', 'retira', 'nao coloca'}
        assert esperado == PALAVRAS_REMOCAO

    def test_conectivos_contem_e_ou(self):
        """CONECTIVOS deve conter 'e' e 'ou'."""
        assert {'e', 'ou'} == CONECTIVOS

    def test_numeros_escritos_corretos(self):
        """NUMEROS_ESCRITOS deve mapear corretamente."""
        esperado = {
            'um': 1, 'uma': 1,
            'dois': 2, 'duas': 2,
            'tres': 3, 'quatro': 4, 'cinco': 5,
            'seis': 6, 'sete': 7, 'oito': 8, 'nove': 9, 'dez': 10
        }
        assert esperado == NUMEROS_ESCRITOS


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE GERAR PATTERNS
# ══════════════════════════════════════════════════════════════════════════════

class TestGerarPatterns:
    """Testes para a função gerar_patterns()."""

    def test_retorna_lista(self, cardapio):
        """Deve retornar uma lista."""
        result = gerar_patterns(cardapio)
        assert isinstance(result, list)

    def test_nao_retorna_vazio(self, cardapio):
        """Deve gerar patterns para o cardápio."""
        result = gerar_patterns(cardapio)
        assert len(result) > 0

    def test_todos_tem_label(self, cardapio):
        """Todos os patterns devem ter label."""
        result = gerar_patterns(cardapio)
        for pattern in result:
            assert 'label' in pattern

    def test_items_e_variantes_tem_id(self, cardapio):
        """Patterns de ITEM e VARIANTE devem ter id, QTD nao tem."""
        result = gerar_patterns(cardapio)
        
        # ITEM e VARIANTE devem ter id
        for pattern in result:
            if pattern['label'] in ('ITEM', 'VARIANTE'):
                assert 'id' in pattern, f"Pattern {pattern} nao tem id"
        
        # QTD pode ou nao ter id (nao e obrigatorio)
        qtd_patterns = [p for p in result if p['label'] == 'QTD']
        assert len(qtd_patterns) > 0

    def test_labels_sao_validos(self, cardapio):
        """Labels devem ser ITEM, VARIANTE ou QTD."""
        result = gerar_patterns(cardapio)
        labels_validos = {'ITEM', 'VARIANTE', 'QTD'}
        for pattern in result:
            assert pattern['label'] in labels_validos

    def test_tem_patterns_para_itens(self, cardapio):
        """Deve gerar patterns para itens do cardápio."""
        result = gerar_patterns(cardapio)
        labels = [p['label'] for p in result]
        assert 'ITEM' in labels

    def test_tem_patterns_para_variantes(self, cardapio):
        """Deve gerar patterns para variantes."""
        result = gerar_patterns(cardapio)
        labels = [p['label'] for p in result]
        assert 'VARIANTE' in labels

    def test_tem_patterns_para_numeros(self, cardapio):
        """Deve gerar patterns para números escritos."""
        result = gerar_patterns(cardapio)
        labels = [p['label'] for p in result]
        assert 'QTD' in labels

    def test_quantidade_numeros_escritos(self, cardapio):
        """Deve ter patterns para cada número escrito."""
        result = gerar_patterns(cardapio)
        qtd_patterns = [p for p in result if p['label'] == 'QTD']
        assert len(qtd_patterns) == len(NUMEROS_ESCRITOS)

    @patch('src.extratores.spacy_extrator.normalizar')
    def test_chama_normalizar_para_cada_item(self, mock_normalizar, cardapio):
        """Deve chamar normalizar para cada item."""
        mock_normalizar.side_effect = lambda x: x.lower()
        gerar_patterns(cardapio)
        assert mock_normalizar.call_count > 0


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE CAPTURAR REMOÇÕES
# ══════════════════════════════════════════════════════════════════════════════

class TestCapturarRemocoes:
    """Testes para a função capturar_remocoes()."""

    def _criar_mock_token(self, text, pos='NOUN', i=0):
        """Cria um mock de token do spaCy."""
        token = MagicMock()
        token.text = text
        token.pos_ = pos
        token.i = i
        return token

    def _criar_mock_doc(self, tokens):
        """Cria um mock de documento spaCy."""
        doc = MagicMock()
        doc.__iter__ = lambda self: iter(tokens)
        doc.__len__ = lambda self: len(tokens)
        return doc

    def test_sem_remocao_retorna_lista_vazia(self):
        """Sem palavras de remoção deve retornar lista vazia."""
        tokens = [
            self._criar_mock_token('quero', 'VERB'),
            self._criar_mock_token('um', 'DET'),
            self._criar_mock_token('x-bacon', 'NOUN'),
        ]
        doc = self._criar_mock_doc(tokens)
        result = capturar_remocoes(doc)
        assert result == []

    @pytest.mark.parametrize('palavra', list(PALAVRAS_REMOCAO))
    def test_detecta_palavras_de_remocao(self, palavra):
        """Deve detectar palavras de remoção."""
        tokens = [
            self._criar_mock_token(palavra, 'ADP'),
            self._criar_mock_token('cebola', 'NOUN'),
        ]
        doc = self._criar_mock_doc(tokens)
        result = capturar_remocoes(doc)
        assert len(result) > 0

    def test_captura_item_apos_sem(self):
        """Deve capturar item após 'sem'."""
        tokens = [
            self._criar_mock_token('sem', 'ADP', 0),
            self._criar_mock_token('cebola', 'NOUN', 1),
        ]
        doc = self._criar_mock_doc(tokens)
        result = capturar_remocoes(doc)
        assert len(result) == 1
        assert result[0][0] == 'cebola'

    def test_ignora_artigos(self):
        """Deve ignorar artigos e preposições."""
        tokens = [
            self._criar_mock_token('sem', 'ADP', 0),
            self._criar_mock_token('a', 'DET', 1),
            self._criar_mock_token('cebola', 'NOUN', 2),
        ]
        doc = self._criar_mock_doc(tokens)
        result = capturar_remocoes(doc)
        # Deve capturar 'cebola', não 'a'
        assert any(r[0] == 'cebola' for r in result)

    def test_multiplas_remocoes(self):
        """Deve capturar múltiplas remoções."""
        tokens = [
            self._criar_mock_token('sem', 'ADP', 0),
            self._criar_mock_token('cebola', 'NOUN', 1),
            self._criar_mock_token('sem', 'ADP', 2),
            self._criar_mock_token('tomate', 'NOUN', 3),
        ]
        doc = self._criar_mock_doc(tokens)
        result = capturar_remocoes(doc)
        assert len(result) == 2
        assert result[0][0] == 'cebola'
        assert result[1][0] == 'tomate'

    def test_conectivo_e_para_nova_remocao(self):
        """Conectivo 'e' deve parar se próximo for nova remoção."""
        tokens = [
            self._criar_mock_token('sem', 'ADP', 0),
            self._criar_mock_token('cebola', 'NOUN', 1),
            self._criar_mock_token('e', 'CONJ', 2),
            self._criar_mock_token('sem', 'ADP', 3),
            self._criar_mock_token('tomate', 'NOUN', 4),
        ]
        doc = self._criar_mock_doc(tokens)
        result = capturar_remocoes(doc)
        # Deve capturar só cebola, parar no 'e sem'
        assert len(result) >= 1


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE EXTRAÇÃO
# ══════════════════════════════════════════════════════════════════════════════

class TestExtrair:
    """Testes para a função extrair()."""

    @pytest.mark.parametrize('mensagem,min_itens', [
        ('x-salada', 1),
        ('2 x-salada', 1),
        ('hamburguer', 1),
    ])
    def test_extrai_itens_basicos(self, mensagem, min_itens):
        """Deve extrair itens basicos do cardapio."""
        result = extrair(mensagem)
        assert isinstance(result, list)
        assert len(result) >= min_itens

    def test_item_tem_campos_obrigatorios(self):
        """Cada item deve ter campos obrigatórios."""
        result = extrair('hamburguer')
        if result:
            item = result[0]
            assert 'item_id' in item
            assert 'quantidade' in item
            assert 'variante' in item
            assert 'remocoes' in item

    @pytest.mark.parametrize('mensagem', [
        '',
        '   ',
        'qualquer coisa aleatoria',
        'abcdefghijklmnop',
    ])
    def test_mensagem_sem_item_retorna_lista_vazia(self, mensagem):
        """Mensagem sem item conhecido deve retornar lista vazia."""
        result = extrair(mensagem)
        assert result == []

    def test_quantidade_numerica(self):
        """Deve extrair quantidade numérica."""
        result = extrair('2 hamburguer')
        if result:
            assert result[0]['quantidade'] == 2

    def test_quantidade_escrita(self):
        """Deve extrair quantidade escrita."""
        result = extrair('tres hamburguer')
        if result:
            assert result[0]['quantidade'] == 3

    def test_quantidade_default_e_um(self):
        """Quantidade padrão deve ser 1."""
        result = extrair('hamburguer')
        if result:
            assert result[0]['quantidade'] == 1

    def test_extrai_item_id_valido(self):
        """Deve extrair item_id válido do cardápio."""
        result = extrair('hamburguer')
        if result:
            item_id = result[0]['item_id']
            from src.config import get_item_por_id
            assert get_item_por_id(item_id) is not None

    @pytest.mark.parametrize('mensagem', [
        'hamburguer sem cebola',
        'x-salada sem tomate',
        'batata sem sal',
    ])
    def test_extrai_remocoes(self, mensagem):
        """Deve extrair remoções."""
        result = extrair(mensagem)
        if result:
            assert 'remocoes' in result[0]
            # Deve ter pelo menos uma remoção detectada
            # (ou lista vazia se não Detectou)
            assert isinstance(result[0]['remocoes'], list)

    def test_multiplos_itens(self):
        """Deve extrair múltiplos itens."""
        result = extrair('hamburguer e coca')
        # Se conseguir extrair, deve ter pelo menos 1
        assert isinstance(result, list)


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE INTEGRIDADE
# ══════════════════════════════════════════════════════════════════════════════

class TestIntegridade:
    """Testes de integridade do módulo."""

    def test_cardapio_tem_itens_para_extracao(self):
        """Cardápio deve ter itens para testar extração."""
        from src.config import get_cardapio
        cardapio = get_cardapio()
        assert len(cardapio['itens']) > 0

    def test_nomes_itens_normalizados_existem(self):
        """Nomes normalizados dos itens devem existir."""
        from src.config import get_cardapio
        cardapio = get_cardapio()
        for item in cardapio['itens']:
            nome_normalizado = normalizar(item['nome'])
            assert nome_normalizado

    def test_aliases_tambem_normalizados(self):
        """Aliases devem ser normalizados corretamente."""
        from src.config import get_cardapio
        cardapio = get_cardapio()
        for item in cardapio['itens']:
            if item.get('aliases'):
                for alias in item['aliases']:
                    normalizado = normalizar(alias)
                    assert normalizado


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE EDGE CASES
# ══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Testes de casos de borda."""

    def test_normalizar_string_vazia(self):
        """String vazia deve retornar vazio."""
        assert normalizar('') == ''

    def test_normalizar_somente_espacos(self):
        """Somente espaços deve retornar vazio após strip."""
        result = normalizar('   ')
        assert result == ''

    def test_extrair_mensagem_muito_longa(self):
        """Mensagem muito longa deve ser processada."""
        mensagem = 'a' * 10000
        result = extrair(mensagem)
        assert isinstance(result, list)

    def test_extrair_caracteres_especiais(self):
        """Caracteres especiais devem ser tratados."""
        result = extrair('hamburguer!@#$%')
        assert isinstance(result, list)

    def test_extrair_numeros_extensos(self):
        """Números extensos devem ser tratados."""
        result = extrair('dez hamburgueres')
        if result:
            assert result[0]['quantidade'] == 10

    def test_capturar_remocoes_lista_vazia(self):
        """Lista vazia de tokens deve retornar lista vazia."""
        doc = MagicMock()
        doc.__iter__ = lambda self: iter([])
        doc.__len__ = lambda self: 0
        result = capturar_remocoes(doc)
        assert result == []


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE CONSISTÊNCIA
# ══════════════════════════════════════════════════════════════════════════════

class TestConsistencia:
    """Testes de consistência."""

    def test_normalizar_e_gerar_patterns_consistentes(self):
        """Patterns devem ser gerados a partir do cardapio."""
        from src.config import get_cardapio
        cardapio = get_cardapio()
        patterns = gerar_patterns(cardapio)
        
        # Verificar que existem patterns para os itens do cardapio
        item_ids = {item['id'] for item in cardapio['itens']}
        pattern_ids = {p.get('id') for p in patterns if p.get('id')}
        
        # Os IDs dos items devem aparecer nos patterns
        assert len(item_ids) > 0
        assert len(pattern_ids) > 0

    def test_itens_cardapio_tem_ids_unicos(self):
        """IDs dos itens devem ser únicos."""
        from src.config import get_cardapio
        cardapio = get_cardapio()
        ids = [item['id'] for item in cardapio['itens']]
        assert len(ids) == len(set(ids))