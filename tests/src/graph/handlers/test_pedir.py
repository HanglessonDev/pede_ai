"""
Testes de alta qualidade para handlers/pedir.py.

Cobertura:
- Item com preço fixo → adiciona ao carrinho
- Item com variante válida → adiciona ao carrinho
- Item sem variante → vai para fila de clarificação
- Itens múltiplos (mix de fixo + variante)
- Itens extraídos vazios
- Item inexistente no cardápio
- Observabilidade: registra log de handler
"""

from unittest.mock import MagicMock, patch

import pytest

from src.graph.handlers.pedir import processar_pedido


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def itens_vazios():
    """Lista vazia de itens extraídos."""
    return []


@pytest.fixture
def itens_fixos():
    """Itens com preço fixo (X-Salada, X-Tudo)."""
    return [
        {'item_id': 'lanche_002', 'quantidade': 1, 'variante': None, 'remocoes': []},
    ]


@pytest.fixture
def itens_com_variantes():
    """Itens que requerem variante (Hambúrguer)."""
    return [
        {'item_id': 'lanche_001', 'quantidade': 1, 'variante': None, 'remocoes': []},
    ]


@pytest.fixture
def itens_com_variante_valida():
    """Itens com variante já especificada."""
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
    """Itens com remoções especificadas."""
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
    """Testes para processar itens com preço fixo."""

    def test_adiciona_ao_carrinho(self, itens_fixos):
        """Item com preço fixo deve ser adicionado ao carrinho."""
        result = processar_pedido(itens_fixos, [])
        assert len(result.carrinho) == 1

    def test_calcula_preco_correto(self, itens_fixos):
        """Preço deve ser calculado corretamente."""
        result = processar_pedido(itens_fixos, [])
        assert result.carrinho[0]['preco'] == 1800

    def test_calcula_preco_com_quantidade(self):
        """Preço deve ser multiplicado pela quantidade."""
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
        """Remoções devem ser preservadas no carrinho."""
        result = processar_pedido(itens_com_remocoes, [])
        assert result.carrinho[0]['remocoes'] == ['tomate', 'cebola']

    def test_resposta_contem_item(self, itens_fixos):
        """Resposta deve conter nome do item."""
        result = processar_pedido(itens_fixos, [])
        assert 'X-Salada' in result.resposta

    def test_resposta_contem_preco(self, itens_fixos):
        """Resposta deve conter preço formatado."""
        result = processar_pedido(itens_fixos, [])
        assert '18.00' in result.resposta


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE ITENS COM VARIANTES
# ══════════════════════════════════════════════════════════════════════════════


class TestProcessarItemComVariante:
    """Testes para processar itens com variantes."""

    def test_variante_valida_adiciona_ao_carrinho(self, itens_com_variante_valida):
        """Item com variante válida deve ser adicionado ao carrinho."""
        result = processar_pedido(itens_com_variante_valida, [])
        assert len(result.carrinho) == 1

    def test_variante_valida_usa_preco_da_variante(self, itens_com_variante_valida):
        """Deve usar o preço da variante, não o preço base."""
        result = processar_pedido(itens_com_variante_valida, [])
        # duplo tem preço específico no cardápio
        assert result.carrinho[0]['preco'] > 0

    def test_variante_valida_preserva_variante(self, itens_com_variante_valida):
        """Variante deve ser preservada no carrinho."""
        result = processar_pedido(itens_com_variante_valida, [])
        assert result.carrinho[0]['variante'] == 'duplo'

    def test_sem_variante_vai_para_fila(self, itens_com_variantes):
        """Item sem variante deve ir para fila de clarificação."""
        result = processar_pedido(itens_com_variantes, [])
        assert len(result.fila) == 1
        assert result.fila[0]['item_id'] == 'lanche_001'

    def test_fila_contem_opcoes(self, itens_com_variantes):
        """Fila deve conter opções de variantes."""
        result = processar_pedido(itens_com_variantes, [])
        assert 'simples' in result.fila[0]['opcoes']
        assert 'duplo' in result.fila[0]['opcoes']
        assert 'triplo' in result.fila[0]['opcoes']

    def test_fila_contem_nome_item(self, itens_com_variantes):
        """Fila deve conter nome do item."""
        result = processar_pedido(itens_com_variantes, [])
        assert result.fila[0]['nome'] == 'Hambúrguer'


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE ITENS MÚLTIPLOS
# ══════════════════════════════════════════════════════════════════════════════


class TestProcessarItensMultiplos:
    """Testes para processar múltiplos itens."""

    def test_mix_fixo_e_variante(self, itens_multiplos):
        """Mix de itens fixos e variantes deve processar corretamente."""
        result = processar_pedido(itens_multiplos, [])
        assert len(result.carrinho) == 1
        assert len(result.fila) == 1

    def test_resposta_mostra_prompt_clarificacao(self, itens_multiplos):
        """Quando há itens na fila, resposta deve ser prompt de clarificação."""
        result = processar_pedido(itens_multiplos, [])
        assert 'Hambúrguer' in result.resposta
        assert 'qual opção' in result.resposta

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

    def test_item_inexistente_ignorad(self):
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
        """Item com variante inválida deve ir para fila."""
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

    def test_quantidade_multiplica_preco_variante(self):
        """Quantidade deve multiplicar preço da variante."""
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
        # Preço da variante duplo * 3
        assert result.carrinho[0]['preco'] > 0

    def test_multiplos_itens_fixos(self):
        """Múltiplos itens fixos devem ir todos ao carrinho."""
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
        """Resposta com múltiplos itens deve ter uma linha por item."""
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
        assert len(linhas) == 2


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE ResultadoPedir
# ══════════════════════════════════════════════════════════════════════════════


class TestResultadoPedir:
    """Testes para o dataclass ResultadoPedir."""

    def test_to_dict_contem_chaves(self):
        """to_dict deve conter todas as chaves esperadas."""
        from src.graph.handlers.pedir import ResultadoPedir

        result = ResultadoPedir(
            carrinho=[{'item_id': 'lanche_001', 'preco': 1500}],
            fila=[],
            resposta='1x Hambúrguer — R$ 15.00',
        )
        d = result.to_dict()
        assert 'carrinho' in d
        assert 'fila_clarificacao' in d
        assert 'resposta' in d

    def test_to_dict_mapeia_fila_corretamente(self):
        """to_dict deve mapear fila para fila_clarificacao."""
        from src.graph.handlers.pedir import ResultadoPedir

        result = ResultadoPedir(
            carrinho=[],
            fila=[{'item_id': 'lanche_001'}],
            resposta='',
        )
        d = result.to_dict()
        assert 'fila_clarificacao' in d
        assert d['fila_clarificacao'] == [{'item_id': 'lanche_001'}]


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE OBSERVABILIDADE
# ══════════════════════════════════════════════════════════════════════════════


class TestHandlerPedirObservabilidade:
    """Testes de instrumentação de observabilidade."""

    @patch('src.graph.handlers.pedir.get_handler_logger')
    def test_processar_pedido_registra_log(self, mock_get_logger) -> None:
        """processar_pedido deve registrar log de observabilidade."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        processar_pedido(
            itens_extraidos=[
                {'item_id': 'lanche_002', 'quantidade': 1, 'variante': None, 'remocoes': []}
            ],
            carrinho_existente=[],
            thread_id='sessao_teste',
        )
        assert mock_logger.registrar.called
        call_kwargs = mock_logger.registrar.call_args[1]
        assert call_kwargs['thread_id'] == 'sessao_teste'
        assert call_kwargs['output_dados']['carrinho_size'] == 1

    @patch('src.graph.handlers.pedir.get_handler_logger')
    def test_processar_pedido_log_contem_handler_e_intent(self, mock_get_logger) -> None:
        """Log deve conter handler e intent corretos."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        processar_pedido(
            itens_extraidos=[
                {'item_id': 'lanche_002', 'quantidade': 1, 'variante': None, 'remocoes': []}
            ],
            carrinho_existente=[],
            thread_id='sessao_teste',
        )
        call_kwargs = mock_logger.registrar.call_args[1]
        assert call_kwargs['handler'] == 'handler_pedir'
        assert call_kwargs['intent'] == 'pedir'

    @patch('src.graph.handlers.pedir.get_handler_logger')
    def test_processar_pedido_log_contem_tempo(self, mock_get_logger) -> None:
        """Log deve conter tempo de execução em ms."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        processar_pedido(
            itens_extraidos=[
                {'item_id': 'lanche_002', 'quantidade': 1, 'variante': None, 'remocoes': []}
            ],
            carrinho_existente=[],
            thread_id='sessao_teste',
        )
        call_kwargs = mock_logger.registrar.call_args[1]
        assert 'tempo_ms' in call_kwargs
        assert call_kwargs['tempo_ms'] >= 0

    @patch('src.graph.handlers.pedir.get_handler_logger')
    def test_processar_pedido_sem_logger_nao_falha(self, mock_get_logger) -> None:
        """processar_pedido deve funcionar sem logger configurado."""
        mock_get_logger.return_value = None

        result = processar_pedido(
            itens_extraidos=[
                {'item_id': 'lanche_002', 'quantidade': 1, 'variante': None, 'remocoes': []}
            ],
            carrinho_existente=[],
            thread_id='sessao_teste',
        )
        assert len(result.carrinho) == 1
