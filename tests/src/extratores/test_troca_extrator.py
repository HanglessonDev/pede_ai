"""Testes unitarios para o modulo src/extratores/troca_extrator.py.

Testa a classe TrocaExtrator e suas funcoes auxiliares:
- extrair()
- _processar_caso_b()
- _tentar_fuzzy_variante()
- _fallback_fuzzy_completo()
- _buscar_matches_no_carrinho()
- _verificar_match_nome()
- _verificar_match_variante()
- _adicionar_ou_atualizar_resultado()
"""

import pytest
from unittest.mock import MagicMock, patch

from src.extratores.config import ExtratorConfig
from src.extratores.modelos import (
    ExtracaoTroca,
    ItemMencionado,
    MatchCarrinho,
)
from src.extratores.troca_extrator import TrocaExtrator


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def config():
    """Configuracao padrao do extrator."""
    return ExtratorConfig(
        fuzzy_item_cutoff=75,
        fuzzy_variante_cutoff=75,
    )


@pytest.fixture
def carrinho_completo():
    """Carrinho com itens variados para testes."""
    return [
        {
            'item_id': 'lanche_001',
            'quantidade': 1,
            'preco': 1500,
            'variante': 'simples',
        },
        {'item_id': 'lanche_001', 'quantidade': 1, 'preco': 2000, 'variante': 'duplo'},
        {'item_id': 'bebida_001', 'quantidade': 2, 'preco': 500, 'variante': 'lata'},
        {'item_id': 'acomp_001', 'quantidade': 1, 'preco': 900, 'variante': 'pequena'},
    ]


@pytest.fixture
def carrinho_vazio():
    """Carrinho vazio."""
    return []


@pytest.fixture
def mock_entity_item():
    """Cria um mock de entidade ITEM para spaCy."""
    ent = MagicMock()
    ent.label_ = 'ITEM'
    ent.text = 'hamburguer'
    ent.ent_id_ = 'lanche_001'
    return ent


@pytest.fixture
def mock_entity_variante():
    """Cria um mock de entidade VARIANTE para spaCy."""
    ent = MagicMock()
    ent.label_ = 'VARIANTE'
    ent.text = 'duplo'
    ent.ent_id_ = ''
    return ent


@pytest.fixture
def mock_doc_com_item(mock_entity_item):
    """Cria um mock de Doc com entidade ITEM."""
    doc = MagicMock()
    doc.ents = [mock_entity_item]
    return doc


@pytest.fixture
def mock_doc_com_dois_itens(mock_entity_item):
    """Cria um mock de Doc com 2 entidades ITEM."""
    ent1 = MagicMock()
    ent1.label_ = 'ITEM'
    ent1.text = 'hamburguer'
    ent1.ent_id_ = 'lanche_001'

    ent2 = MagicMock()
    ent2.label_ = 'ITEM'
    ent2.text = 'coca'
    ent2.ent_id_ = 'bebida_001'

    doc = MagicMock()
    doc.ents = [ent1, ent2]
    return doc


@pytest.fixture
def mock_doc_com_variante_sozinha(mock_entity_variante):
    """Cria um mock de Doc com VARIANTE isolada."""
    doc = MagicMock()
    doc.ents = [mock_entity_variante]
    return doc


@pytest.fixture
def mock_doc_vazio():
    """Cria um mock de Doc sem entidades."""
    doc = MagicMock()
    doc.ents = []
    return doc


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE EXTRAIR() - CASO A (2+ ITEMS)
# ══════════════════════════════════════════════════════════════════════════════


class TestExtrairCasoA:
    """Testes para o caso A: 2+ itens mencionados."""

    def test_duas_itens_retorna_caso_a(
        self, config, carrinho_completo, mock_doc_com_dois_itens
    ):
        """2 ITEMs mencionados deve retornar caso='A'."""
        engine = MagicMock()
        engine.processar.return_value = mock_doc_com_dois_itens

        extrator = TrocaExtrator(engine, config)
        resultado = extrator.extrair('muda hamburguer por coca', carrinho_completo)

        assert resultado.caso == 'A'
        assert resultado.item_original is None
        assert resultado.variante_nova is None

    def test_tres_itens_retorna_caso_a(self, config, carrinho_completo):
        """3 ITEMs mencionados deve retornar caso='A'."""
        engine = MagicMock()

        ent1 = MagicMock()
        ent1.label_ = 'ITEM'
        ent1.text = 'hamburguer'
        ent1.ent_id_ = 'lanche_001'

        ent2 = MagicMock()
        ent2.label_ = 'ITEM'
        ent2.text = 'x-salada'
        ent2.ent_id_ = 'lanche_002'

        ent3 = MagicMock()
        ent3.label_ = 'ITEM'
        ent3.text = 'coca'
        ent3.ent_id_ = 'bebida_001'

        doc = MagicMock()
        doc.ents = [ent1, ent2, ent3]
        engine.processar.return_value = doc

        extrator = TrocaExtrator(engine, config)
        resultado = extrator.extrair(
            'troca hamburguer x-salada por coca', carrinho_completo
        )

        assert resultado.caso == 'A'


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE EXTRAIR() - CASO C (0 ITEMS + 1 VARIANTE ISOLADA)
# ══════════════════════════════════════════════════════════════════════════════


class TestExtrairCasoC:
    """Testes para o caso C: variante isolada."""

    def test_variante_sozinha_retorna_caso_c(
        self, config, carrinho_completo, mock_doc_com_variante_sozinha
    ):
        """0 ITEMs + 1 VARIANTE isolada deve retornar caso='C'."""
        engine = MagicMock()
        engine.processar.return_value = mock_doc_com_variante_sozinha

        extrator = TrocaExtrator(engine, config)
        resultado = extrator.extrair('muda pra lata', carrinho_completo)

        assert resultado.caso == 'C'
        assert resultado.item_original is None
        assert resultado.variante_nova == 'duplo'


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE EXTRAIR() - CASO B (1 ITEM)
# ══════════════════════════════════════════════════════════════════════════════


class TestExtrairCasoB:
    """Testes para o caso B: 1 item mencionado."""

    def test_um_item_com_match_no_carrinho(
        self, config, carrinho_completo, mock_doc_com_item
    ):
        """1 ITEM com match no carrinho deve ter item_original preenchido."""
        engine = MagicMock()
        engine.processar.return_value = mock_doc_com_item

        extrator = TrocaExtrator(engine, config)
        resultado = extrator.extrair('muda o hamburguer', carrinho_completo)

        assert resultado.caso == 'B'
        assert resultado.item_original is not None
        assert resultado.item_original.item_id == 'lanche_001'

    def test_um_item_sem_match_no_carrinho(
        self, config, carrinho_vazio, mock_doc_com_item
    ):
        """1 ITEM sem match no carrinho deve ter item_original=None."""
        engine = MagicMock()
        engine.processar.return_value = mock_doc_com_item

        extrator = TrocaExtrator(engine, config)
        resultado = extrator.extrair('muda o hamburguer', carrinho_vazio)

        assert resultado.caso == 'B'
        assert resultado.item_original is None

    def test_um_item_com_variante(self, config, carrinho_completo):
        """1 ITEM com variante deve retornar variante_nova."""
        engine = MagicMock()

        ent_item = MagicMock()
        ent_item.label_ = 'ITEM'
        ent_item.text = 'hamburguer'
        ent_item.ent_id_ = 'lanche_001'

        ent_var = MagicMock()
        ent_var.label_ = 'VARIANTE'
        ent_var.text = 'duplo'
        ent_var.ent_id_ = ''

        doc = MagicMock()
        doc.ents = [ent_item, ent_var]
        engine.processar.return_value = doc

        extrator = TrocaExtrator(engine, config)
        resultado = extrator.extrair('muda pra duplo', carrinho_completo)

        assert resultado.caso == 'B'
        assert resultado.variante_nova == 'duplo'


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE _PROCESSAR_CASO_B()
# ══════════════════════════════════════════════════════════════════════════════


class TestProcessarCasoB:
    """Testes para o metodo _processar_caso_b()."""

    def test_item_com_match_retorna_item_original(self, config, carrinho_completo):
        """Com match no carrinho deve retornar item_original preenchido."""
        engine = MagicMock()
        extrator = TrocaExtrator(engine, config)

        item_mencionado = ItemMencionado(
            texto='hamburguer',
            variante=None,
            ent_id='lanche_001',
        )
        resultado = extrator._processar_caso_b(
            item_mencionado, carrinho_completo, 'muda o hamburguer'
        )

        assert resultado.item_original is not None
        assert resultado.item_original.item_id == 'lanche_001'

    def test_item_sem_match_retorna_item_original_none(self, config, carrinho_vazio):
        """Sem match no carrinho deve retornar item_original=None."""
        engine = MagicMock()
        extrator = TrocaExtrator(engine, config)

        item_mencionado = ItemMencionado(
            texto='hamburguer',
            variante=None,
            ent_id='lanche_001',
        )
        resultado = extrator._processar_caso_b(
            item_mencionado, carrinho_vazio, 'muda o hamburguer'
        )

        assert resultado.item_original is None


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE _TENTAR_FUZZY_VARIANTE()
# ══════════════════════════════════════════════════════════════════════════════


class TestTentarFuzzyVariante:
    """Testes para o metodo _tentar_fuzzy_variante()."""

    @patch('src.config.get_cardapio')
    def test_com_item_id_valido_retorna_variante(self, mock_get_cardapio, config):
        """Com item_id valido deve buscar variantes apenas daquele item."""
        mock_get_cardapio.return_value = {
            'itens': [
                {
                    'id': 'lanche_001',
                    'nome': 'Hamburguer',
                    'variantes': [
                        {'opcao': 'simples', 'preco': 1500},
                        {'opcao': 'duplo', 'preco': 2000},
                    ],
                }
            ]
        }

        engine = MagicMock()
        extrator = TrocaExtrator(engine, config)

        with patch(
            'src.extratores.troca_extrator.fuzzy_match_variante',
            return_value=('duplo', 90.0),
        ) as mock_fuzzy:
            resultado = extrator._tentar_fuzzy_variante('muda pra duplo', 'lanche_001')

        assert mock_fuzzy.called
        assert resultado == 'duplo'

    @patch('src.config.get_cardapio')
    def test_sem_item_id_busca_todas_variantes(self, mock_get_cardapio, config):
        """Sem item_id deve buscar variantes de todos os itens."""
        mock_get_cardapio.return_value = {
            'itens': [
                {
                    'id': 'lanche_001',
                    'nome': 'Hamburguer',
                    'variantes': [
                        {'opcao': 'simples', 'preco': 1500},
                        {'opcao': 'duplo', 'preco': 2000},
                    ],
                },
                {
                    'id': 'bebida_001',
                    'nome': 'Coca-Cola',
                    'variantes': [
                        {'opcao': 'lata', 'preco': 500},
                        {'opcao': '350ml', 'preco': 500},
                    ],
                },
            ]
        }

        engine = MagicMock()
        extrator = TrocaExtrator(engine, config)

        with patch(
            'src.extratores.troca_extrator.fuzzy_match_variante',
            return_value=('lata', 90.0),
        ) as mock_fuzzy:
            resultado = extrator._tentar_fuzzy_variante('muda pra lata', None)

        assert mock_fuzzy.called
        assert resultado == 'lata'


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE _FALLBACK_FUZZY_COMPLETO()
# ══════════════════════════════════════════════════════════════════════════════


class TestFallbackFuzzyCompleto:
    """Testes para o metodo _fallback_fuzzy_completo()."""

    @patch('src.config.get_cardapio')
    @patch('src.extratores.fuzzy_extrator.fuzzy_match_item')
    def test_fuzzy_encontra_item_retorna_caso_b(
        self, mock_fuzzy_item, mock_get_cardapio, config, carrinho_completo
    ):
        """Fuzzy encontra item deve retornar caso='B'."""
        mock_get_cardapio.return_value = {
            'itens': [
                {
                    'id': 'lanche_001',
                    'nome': 'Hamburguer',
                    'aliases': ['hamburguer'],
                    'variantes': [
                        {'opcao': 'simples', 'preco': 1500},
                        {'opcao': 'duplo', 'preco': 2000},
                    ],
                }
            ]
        }
        mock_fuzzy_item.return_value = ('hamburguer', 95.0, 'lanche_001')

        engine = MagicMock()
        extrator = TrocaExtrator(engine, config)

        with patch.object(extrator, '_tentar_fuzzy_variante', return_value='duplo'):
            resultado = extrator._fallback_fuzzy_completo(
                'muda o hamburguer', carrinho_completo
            )

        assert resultado.caso == 'B'
        assert resultado.item_original is not None

    @patch('src.config.get_cardapio')
    @patch('src.extratores.fuzzy_extrator.fuzzy_match_item')
    def test_fuzzy_nao_encontra_retorna_vazio(
        self, mock_fuzzy_item, mock_get_cardapio, config, carrinho_completo
    ):
        """Fuzzy nao encontra item deve retornar caso='vazio'."""
        mock_get_cardapio.return_value = {'itens': []}
        mock_fuzzy_item.return_value = (None, 0.0, None)

        engine = MagicMock()
        extrator = TrocaExtrator(engine, config)

        resultado = extrator._fallback_fuzzy_completo('muda o pizza', carrinho_completo)

        assert resultado.caso == 'vazio'
        assert resultado.item_original is None


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE _BUSCAR_MATCHES_NO_CARRINHO()
# ══════════════════════════════════════════════════════════════════════════════


class TestBuscarMatchesNoCarrinho:
    """Testes para a funcao _buscar_matches_no_carrinho()."""

    def test_encontra_item_por_nome(self, carrinho_completo):
        """Deve encontrar item por nome."""
        from src.extratores.troca_extrator import _buscar_matches_no_carrinho

        itens = [ItemMencionado(texto='hamburguer', variante=None, ent_id='')]
        resultados = _buscar_matches_no_carrinho(itens, carrinho_completo)

        assert len(resultados) >= 1
        assert resultados[0].item_id == 'lanche_001'

    def test_encontra_item_por_id(self, carrinho_completo):
        """Deve encontrar item por ID."""
        from src.extratores.troca_extrator import _buscar_matches_no_carrinho

        itens = [ItemMencionado(texto='', variante=None, ent_id='lanche_001')]
        resultados = _buscar_matches_no_carrinho(itens, carrinho_completo)

        assert len(resultados) >= 1

    def test_nao_encontra_item_inexistente(self, carrinho_completo):
        """Item inexistente deve retornar lista vazia."""
        from src.extratores.troca_extrator import _buscar_matches_no_carrinho

        itens = [ItemMencionado(texto='pizza', variante=None, ent_id='')]
        resultados = _buscar_matches_no_carrinho(itens, carrinho_completo)

        assert resultados == []

    def test_carrinho_vazio_retorna_vazio(self, carrinho_vazio):
        """Carrinho vazio deve retornar lista vazia."""
        from src.extratores.troca_extrator import _buscar_matches_no_carrinho

        itens = [ItemMencionado(texto='hamburguer', variante=None, ent_id='')]
        resultados = _buscar_matches_no_carrinho(itens, carrinho_vazio)

        assert resultados == []


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE _VERIFICAR_MATCH_NOME()
# ══════════════════════════════════════════════════════════════════════════════


class TestVerificarMatchNome:
    """Testes para a funcao _verificar_match_nome()."""

    def test_match_por_texto(self):
        """Texto mencionado deve fazer match por texto."""
        from src.extratores.troca_extrator import _verificar_match_nome

        resultado = _verificar_match_nome(
            texto_mencionado='hamburguer',
            ent_id='',
            item_id_carrinho='lanche_001',
            nome_normalizado='hamburguer',
        )
        assert resultado is True

    def test_match_por_ent_id(self):
        """ent_id igual ao item_id deve fazer match."""
        from src.extratores.troca_extrator import _verificar_match_nome

        resultado = _verificar_match_nome(
            texto_mencionado='',
            ent_id='lanche_001',
            item_id_carrinho='lanche_001',
            nome_normalizado='x-salada',
        )
        assert resultado is True

    def test_nao_match(self):
        """Texto diferente e ent_id diferente nao deve fazer match."""
        from src.extratores.troca_extrator import _verificar_match_nome

        resultado = _verificar_match_nome(
            texto_mencionado='pizza',
            ent_id='',
            item_id_carrinho='lanche_001',
            nome_normalizado='hamburguer',
        )
        assert resultado is False


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE _VERIFICAR_MATCH_VARIANTE()
# ══════════════════════════════════════════════════════════════════════════════


class TestVerificarMatchVariante:
    """Testes para a funcao _verificar_match_variante()."""

    def test_variante_matcha(self):
        """Variante mencionada deve fazer match."""
        from src.extratores.troca_extrator import _verificar_match_variante

        resultado = _verificar_match_variante(
            variante_mencionada='duplo',
            variante_carrinho='duplo',
        )
        assert resultado is True

    def test_variante_nao_matcha(self):
        """Variante diferente nao deve fazer match."""
        from src.extratores.troca_extrator import _verificar_match_variante

        resultado = _verificar_match_variante(
            variante_mencionada='simples',
            variante_carrinho='duplo',
        )
        assert resultado is False

    def test_sem_variante_mencionada_retorna_true(self):
        """Sem variante mencionada deve retornar True (any)."""
        from src.extratores.troca_extrator import _verificar_match_variante

        resultado = _verificar_match_variante(
            variante_mencionada=None,
            variante_carrinho='duplo',
        )
        assert resultado is True


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE _ADICIONAR_OU_ATUALIZAR_RESULTADO()
# ══════════════════════════════════════════════════════════════════════════════


class TestAdicionarOuAtualizarResultado:
    """Testes para a funcao _adicionar_ou_atualizar_resultado()."""

    def test_adiciona_novo_item(self):
        """Deve adicionar novo item aos resultados."""
        from src.extratores.troca_extrator import _adicionar_ou_atualizar_resultado

        resultados: list[MatchCarrinho] = []
        indices_adicionados: set[int] = set()
        item_carrinho = {'item_id': 'lanche_001', 'variante': 'simples'}

        _adicionar_ou_atualizar_resultado(
            resultados, item_carrinho, 0, indices_adicionados
        )

        assert len(resultados) == 1
        assert resultados[0].item_id == 'lanche_001'
        assert 0 in indices_adicionados

    def test_atualiza_item_existente(self):
        """Item existente deve ter indices atualizados."""
        from src.extratores.troca_extrator import _adicionar_ou_atualizar_resultado

        resultados = [
            MatchCarrinho(item_id='lanche_001', variante='simples', indices=[0])
        ]
        indices_adicionados: set[int] = {0}
        item_carrinho = {'item_id': 'lanche_001', 'variante': 'duplo'}

        _adicionar_ou_atualizar_resultado(
            resultados, item_carrinho, 1, indices_adicionados
        )

        assert len(resultados) == 1
        assert resultados[0].indices == [0, 1]
        assert 1 in indices_adicionados


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE MENSAGEM VAZIA
# ══════════════════════════════════════════════════════════════════════════════


class TestMensagemVazia:
    """Testes para mensagens vazias ou invalidas."""

    def test_mensagem_vazia_retorna_vazio(self, config):
        """Mensagem vazia deve retornar caso='vazio'."""
        engine = MagicMock()
        extrator = TrocaExtrator(engine, config)

        resultado = extrator.extrair('', [])

        assert resultado.caso == 'vazio'
        assert resultado.item_original is None

    def test_mensagem_somente_espacos_retorna_vazio(self, config):
        """Mensagem com espacos deve retornar caso='vazio'."""
        engine = MagicMock()
        extrator = TrocaExtrator(engine, config)

        resultado = extrator.extrair('   ', [])

        assert resultado.caso == 'vazio'


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE EDGE CASES
# ══════════════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Testes de casos de borda."""

    def test_variante_associada_a_item_anterior(self, config, carrinho_completo):
        """VARIANTE com ITEM anterior deve ser associada ao item."""
        engine = MagicMock()

        ent_item = MagicMock()
        ent_item.label_ = 'ITEM'
        ent_item.text = 'hamburguer'
        ent_item.ent_id_ = 'lanche_001'

        ent_var = MagicMock()
        ent_var.label_ = 'VARIANTE'
        ent_var.text = 'duplo'
        ent_var.ent_id_ = ''

        doc = MagicMock()
        doc.ents = [ent_item, ent_var]
        engine.processar.return_value = doc

        extrator = TrocaExtrator(engine, config)
        resultado = extrator.extrair('muda pra duplo', carrinho_completo)

        assert resultado.variante_nova == 'duplo'
        assert resultado.item_original is not None

    def test_dois_itens_com_variantes_separados(self, config, carrinho_completo):
        """2 ITEMs devem retornar caso A independentemente de variantes."""
        engine = MagicMock()

        ent1 = MagicMock()
        ent1.label_ = 'ITEM'
        ent1.text = 'hamburguer'
        ent1.ent_id_ = 'lanche_001'

        ent2 = MagicMock()
        ent2.label_ = 'ITEM'
        ent2.text = 'x-salada'
        ent2.ent_id_ = 'lanche_002'

        doc = MagicMock()
        doc.ents = [ent1, ent2]
        engine.processar.return_value = doc

        extrator = TrocaExtrator(engine, config)
        resultado = extrator.extrair('troca hamburguer por x-salada', carrinho_completo)

        assert resultado.caso == 'A'

    def test_zero_itens_zero_variantes_vai_para_fallback(
        self, config, carrinho_completo, mock_doc_vazio
    ):
        """0 ITEMs + 0 VARIANTEs deve acionar fallback fuzzy."""
        engine = MagicMock()
        engine.processar.return_value = mock_doc_vazio

        with patch.object(TrocaExtrator, '_fallback_fuzzy_completo') as mock_fallback:
            mock_fallback.return_value = ExtracaoTroca(
                caso='vazio', item_original=None, variante_nova=None
            )
            extrator = TrocaExtrator(engine, config)
            extrator.extrair('mensagem qualquer', carrinho_completo)

            mock_fallback.assert_called_once()
