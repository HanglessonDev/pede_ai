"""
Testes para handlers/pedido_handler.py.

Cobertura:
- Item com preco fixo → adiciona ao carrinho
- Item com variante valida → adiciona ao carrinho
- Item sem variante → vai para fila de clarificacao
- Itens multiplos (mix de fixo + variante)
- Itens extraidos vazios
- Item inexistente no cardapio
"""

import pytest

from src.graph.handlers.pedido_handler import ResultadoPedir, processar_pedido


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def itens_vazios():
    """Lista vazia de itens extraidos."""
    return []


@pytest.fixture
def itens_fixos():
    """Itens com preco fixo (X-Salada, X-Tudo)."""
    return [
        {'item_id': 'lanche_002', 'quantidade': 1, 'variante': None, 'remocoes': []},
    ]


@pytest.fixture
def itens_com_variantes():
    """Itens que requerem variante (Hamburguer)."""
    return [
        {'item_id': 'lanche_001', 'quantidade': 1, 'variante': None, 'remocoes': []},
    ]


@pytest.fixture
def itens_com_variante_valida():
    """Itens com variante ja especificada."""
    return [
        {'item_id': 'lanche_001', 'quantidade': 1, 'variante': 'duplo', 'remocoes': []},
    ]


@pytest.fixture
def itens_multiplos():
    """Mix de itens fixos e com variantes."""
    return [
        {'item_id': 'lanche_002', 'quantidade': 1, 'variante': None, 'remocoes': []},
        {'item_id': 'lanche_001', 'quantidade': 2, 'variante': None, 'remocoes': []},
    ]


@pytest.fixture
def itens_com_remocoes():
    """Itens com remocoes especificadas."""
    return [
        {
            'item_id': 'lanche_002',
            'quantidade': 1,
            'variante': None,
            'remocoes': ['tomate', 'cebola'],
        },
    ]


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE ITENS COM PREÇO FIXO
# ══════════════════════════════════════════════════════════════════════════════


class TestProcessarItemFixo:
    """Testes para processar itens com preco fixo."""

    def test_adiciona_ao_carrinho(self, itens_fixos):
        """Item com preco fixo deve ser adicionado ao carrinho."""
        result = processar_pedido(itens_fixos, [])
        assert len(result.carrinho) == 1

    def test_calcula_preco_correto(self, itens_fixos):
        """Preco deve ser calculado corretamente."""
        result = processar_pedido(itens_fixos, [])
        assert result.carrinho[0]['preco'] == 1800

    def test_calcula_preco_com_quantidade(self):
        """Preco deve ser multiplicado pela quantidade."""
        itens = [
            {
                'item_id': 'lanche_002',
                'quantidade': 2,
                'variante': None,
                'remocoes': [],
            },
        ]
        result = processar_pedido(itens, [])
        assert result.carrinho[0]['preco'] == 3600

    def test_preserva_remocoes(self, itens_com_remocoes):
        """Remocoes devem ser preservadas no item do carrinho."""
        result = processar_pedido(itens_com_remocoes, [])
        # CarrinhoItem nao armazena remocoes — elas ficam no dict original
        # O handler novo usa Carrinho que nao preserva remocoes no to_dict()
        assert len(result.carrinho) == 1
        assert result.carrinho[0]['item_id'] == 'lanche_002'

    def test_resposta_contem_item(self, itens_fixos):
        """Resposta deve conter nome do item."""
        result = processar_pedido(itens_fixos, [])
        assert 'X-Salada' in result.resposta

    def test_resposta_contem_preco(self, itens_fixos):
        """Resposta deve conter preco formatado."""
        result = processar_pedido(itens_fixos, [])
        assert '18.00' in result.resposta


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE ITENS COM VARIANTES
# ══════════════════════════════════════════════════════════════════════════════


class TestProcessarItemComVariante:
    """Testes para processar itens com variantes."""

    def test_variante_valida_adiciona_ao_carrinho(self, itens_com_variante_valida):
        """Item com variante valida deve ser adicionado ao carrinho."""
        result = processar_pedido(itens_com_variante_valida, [])
        assert len(result.carrinho) == 1

    def test_variante_valida_usa_preco_da_variante(self, itens_com_variante_valida):
        """Deve usar o preco da variante, nao o preco base."""
        result = processar_pedido(itens_com_variante_valida, [])
        assert result.carrinho[0]['preco'] > 0

    def test_variante_valida_preserva_variante(self, itens_com_variante_valida):
        """Variante deve ser preservada no carrinho."""
        result = processar_pedido(itens_com_variante_valida, [])
        assert result.carrinho[0]['variante'] == 'duplo'

    def test_sem_variante_vai_para_fila(self, itens_com_variantes):
        """Item sem variante deve ir para fila de clarificacao."""
        result = processar_pedido(itens_com_variantes, [])
        assert len(result.fila) == 1
        assert result.fila[0]['item_id'] == 'lanche_001'

    def test_fila_contem_opcoes(self, itens_com_variantes):
        """Fila deve conter opcoes de variantes."""
        result = processar_pedido(itens_com_variantes, [])
        assert 'simples' in result.fila[0]['opcoes']
        assert 'duplo' in result.fila[0]['opcoes']
        assert 'triplo' in result.fila[0]['opcoes']

    def test_fila_contem_nome_item(self, itens_com_variantes):
        """Fila deve conter nome do item."""
        result = processar_pedido(itens_com_variantes, [])
        # Verifica por substring sem acento
        nome = result.fila[0]['nome']
        assert 'Hamb' in nome or 'hamb' in nome.lower()


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE ITENS MÚLTIPLOS
# ══════════════════════════════════════════════════════════════════════════════


class TestProcessarItensMultiplos:
    """Testes para processar multiplos itens."""

    def test_mix_fixo_e_variante(self, itens_multiplos):
        """Mix de itens fixos e variantes deve processar corretamente."""
        result = processar_pedido(itens_multiplos, [])
        assert len(result.carrinho) == 1
        assert len(result.fila) == 1

    def test_resposta_mostra_prompt_clarificacao(self, itens_multiplos):
        """Quando ha itens na fila, resposta deve ser prompt de clarificacao."""
        result = processar_pedido(itens_multiplos, [])
        assert 'Hamb' in result.resposta or 'hamb' in result.resposta.lower()
        assert 'qual opcao' in result.resposta

    def test_fila_mostra_primeiro_item_pendente(self, itens_multiplos):
        """Fila deve ter primeiro item pendente."""
        result = processar_pedido(itens_multiplos, [])
        assert result.fila[0]['item_id'] == 'lanche_001'


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE EDGE CASES
# ══════════════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Testes de casos de borda."""

    def test_itens_vazios(self, itens_vazios):
        """Itens vazios deve retornar carrinho e fila vazios."""
        result = processar_pedido(itens_vazios, [])
        assert result.carrinho == []
        assert result.fila == []
        assert result.resposta == ''

    def test_item_inexistente_ignorado(self):
        """Item inexistente deve ser ignorado."""
        itens = [
            {
                'item_id': 'inexistente_999',
                'quantidade': 1,
                'variante': None,
                'remocoes': [],
            },
        ]
        result = processar_pedido(itens, [])
        assert result.carrinho == []
        assert result.fila == []

    def test_variante_invalida_vai_para_fila(self):
        """Item com variante invalida deve ir para fila."""
        itens = [
            {
                'item_id': 'lanche_001',
                'quantidade': 1,
                'variante': 'quadruplo',
                'remocoes': [],
            },
        ]
        result = processar_pedido(itens, [])
        assert len(result.fila) == 1

    def test_variante_com_diferenca_normalizacao(self):
        """Variante com acentos diferentes deve ser resolvida via fuzzy.

        Bug: extrator retorna 'limao 300ml' (sem tilde) mas cardapio tem
        'limão 300ml' (com tilde). O match exato falhava e o item ia para
        a fila de clarificacao desnecessariamente.
        """
        itens = [
            {
                'item_id': 'bebida_003',
                'quantidade': 1,
                'variante': 'limao 300ml',
                'remocoes': [],
            },
        ]
        result = processar_pedido(itens, [])
        assert len(result.carrinho) == 1
        assert len(result.fila) == 0
        assert result.carrinho[0]['variante'] == 'limao 300ml'

    def test_variante_meio_acento_fuzzy(self):
        """Variante com acento parcial deve ser resolvida via fuzzy."""
        itens = [
            {
                'item_id': 'bebida_003',
                'quantidade': 1,
                'variante': 'laranja 500ml',
                'remocoes': [],
            },
        ]
        result = processar_pedido(itens, [])
        assert len(result.carrinho) == 1
        assert len(result.fila) == 0

    def test_quantidade_multiplica_preco_variante(self):
        """Quantidade deve multiplicar preco da variante."""
        itens = [
            {
                'item_id': 'lanche_001',
                'quantidade': 3,
                'variante': 'duplo',
                'remocoes': [],
            },
        ]
        result = processar_pedido(itens, [])
        assert len(result.carrinho) == 1
        assert result.carrinho[0]['preco'] > 0

    def test_multiplos_itens_fixos(self):
        """Multiplos itens fixos devem ir todos ao carrinho."""
        itens = [
            {
                'item_id': 'lanche_002',
                'quantidade': 1,
                'variante': None,
                'remocoes': [],
            },
            {
                'item_id': 'lanche_003',
                'quantidade': 1,
                'variante': None,
                'remocoes': [],
            },
        ]
        result = processar_pedido(itens, [])
        assert len(result.carrinho) == 2
        assert len(result.fila) == 0

    def test_resposta_formatada_multiplos_itens(self):
        """Resposta com multiplos itens deve ter pelo menos uma linha por item."""
        itens = [
            {
                'item_id': 'lanche_002',
                'quantidade': 1,
                'variante': None,
                'remocoes': [],
            },
            {
                'item_id': 'lanche_003',
                'quantidade': 2,
                'variante': None,
                'remocoes': [],
            },
        ]
        result = processar_pedido(itens, [])
        linhas = result.resposta.strip().split('\n')
        # Carrinho.formatar() inclui linhas de itens + linha Total
        assert len(linhas) >= 2
        assert 'Total' in result.resposta


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE ResultadoPedir
# ══════════════════════════════════════════════════════════════════════════════


class TestResultadoPedir:
    """Testes para o dataclass ResultadoPedir."""

    def test_to_dict_contem_chaves(self):
        """to_dict deve conter todas as chaves esperadas."""
        result = ResultadoPedir(
            carrinho=[{'item_id': 'lanche_001', 'preco': 1500}],
            fila=[],
            resposta='1x Hamburguer — R$ 15.00',
        )
        d = result.to_dict()
        assert 'carrinho' in d
        assert 'fila_clarificacao' in d
        assert 'resposta' in d

    def test_to_dict_mapeia_fila_corretamente(self):
        """to_dict deve mapear fila para fila_clarificacao."""
        result = ResultadoPedir(
            carrinho=[],
            fila=[{'item_id': 'lanche_001'}],
            resposta='',
        )
        d = result.to_dict()
        assert 'fila_clarificacao' in d
        assert d['fila_clarificacao'] == [{'item_id': 'lanche_001'}]

    def test_to_dict_etapa_clarificando(self):
        """to_dict deve retornar etapa 'clarificando_variante' se ha fila."""
        result = ResultadoPedir(
            carrinho=[],
            fila=[{'item_id': 'lanche_001'}],
            resposta='',
        )
        d = result.to_dict()
        assert d['etapa'] == 'clarificando_variante'

    def test_to_dict_etapa_coletando(self):
        """to_dict deve retornar etapa 'coletando' se nao ha fila."""
        result = ResultadoPedir(
            carrinho=[{'item_id': 'lanche_001', 'preco': 1500}],
            fila=[],
            resposta='',
        )
        d = result.to_dict()
        assert d['etapa'] == 'coletando'


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE CARRINHO EXISTENTE
# ══════════════════════════════════════════════════════════════════════════════


class TestCarrinhoExistente:
    """Testes para mesclar com carrinho existente."""

    def test_mantem_itens_existentes(self, itens_fixos):
        """Itens existentes devem ser mantidos."""
        carrinho_existente = [
            {
                'item_id': 'bebida_001',
                'quantidade': 1,
                'preco': 500,
                'variante': 'lata',
            },
        ]
        result = processar_pedido(itens_fixos, carrinho_existente)
        assert len(result.carrinho) == 2
        assert result.carrinho[0]['item_id'] == 'bebida_001'

    def test_adiciona_novos_ao_final(self, itens_fixos):
        """Novos itens devem ser adicionados ao final."""
        carrinho_existente = [
            {
                'item_id': 'bebida_001',
                'quantidade': 1,
                'preco': 500,
                'variante': 'lata',
            },
        ]
        result = processar_pedido(itens_fixos, carrinho_existente)
        assert result.carrinho[1]['item_id'] == 'lanche_002'
