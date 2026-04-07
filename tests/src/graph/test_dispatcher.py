"""Testes para o dispatcher de modificação de pedido."""

from unittest.mock import patch
from src.graph.nodes import node_dispatcher_modificar
from src.graph.state import State


def _state(mensagem: str, carrinho: list | None = None) -> State:
    """Helper para criar estado mínimo para o dispatcher."""
    s = {
        'mensagem_atual': mensagem,
        'modo': 'coletando',
        'intent': 'modificar_pedido',
        'acao': '',
        'origem_intent': 'rag_forte',
        'confidence': 0.9,
        'itens_extraidos': [],
        'dados_extracao': {},
        'carrinho': carrinho or [],
        'fila_clarificacao': [],
        'tentativas_clarificacao': 0,
        'resposta': '',
    }
    return s  # type: ignore[return-value]


# ── Helpers de mock ──────────────────────────────────────────────────────────


def _mock_troca(caso, item_original=None, variante_nova=None):
    return {
        'caso': caso,
        'item_original': item_original,
        'variante_nova': variante_nova,
    }


def _mock_item_original(item_id='lanche_001', indices=None):
    return {'item_id': item_id, 'nome': 'Hamburguer', 'indices': indices or [0]}


_CARRINHO_COM_HAMBURGUER = [
    {'item_id': 'lanche_001', 'quantidade': 1, 'preco': 1500, 'variante': 'simples'}
]
_CARRINHO_COM_COCA = [
    {'item_id': 'bebida_001', 'quantidade': 1, 'preco': 800, 'variante': None}
]
_CARRINHO_DOIS_ITENS = _CARRINHO_COM_HAMBURGUER + _CARRINHO_COM_COCA


# ── Troca válida ─────────────────────────────────────────────────────────────


class TestDispatcherTroca:
    @patch('src.graph.nodes.extrair_itens_troca')
    @patch('src.graph.nodes.extrair')
    def test_caso_a_com_extrair_itens_vai_para_adicao(self, mock_extrair, mock_troca):
        """'2 xtudo e 1 coca' — Caso A com itens extraídos → adicionar_item.

        O carrinho NÃO é critério — se extrair() retorna itens, é adição.
        """
        mock_troca.return_value = _mock_troca('A')
        mock_extrair.return_value = [
            {
                'item_id': 'lanche_003',
                'quantidade': 2,
                'variante': None,
                'remocoes': [],
            },
            {
                'item_id': 'bebida_001',
                'quantidade': 1,
                'variante': None,
                'remocoes': [],
            },
        ]
        # Carrinho tem itens, mas mesmo assim é adição
        result = node_dispatcher_modificar(
            _state('2 xtudo e 1 coca', _CARRINHO_COM_COCA)
        )
        assert result['acao'] == 'adicionar_item'
        assert len(result['itens_extraidos']) == 2

    @patch('src.graph.nodes.extrair_itens_troca')
    @patch('src.graph.nodes.extrair')
    def test_caso_a_carrinho_vazio_vai_para_adicao(self, mock_extrair, mock_troca):
        """'2 xtudo e 1 coca' — carrinho vazio → adicionar_item."""
        mock_troca.return_value = _mock_troca('A')
        mock_extrair.return_value = [
            {
                'item_id': 'lanche_003',
                'quantidade': 2,
                'variante': None,
                'remocoes': [],
            },
            {
                'item_id': 'bebida_001',
                'quantidade': 1,
                'variante': None,
                'remocoes': [],
            },
        ]
        result = node_dispatcher_modificar(_state('2 xtudo e 1 coca', []))
        assert result['acao'] == 'adicionar_item'
        assert len(result['itens_extraidos']) == 2

    @patch('src.graph.nodes.extrair_itens_troca')
    @patch('src.graph.nodes.extrair')
    def test_caso_a_sem_itens_extraidos_vai_para_sem_entidade(
        self, mock_extrair, mock_troca
    ):
        """'troca isso por aquilo' — Caso A sem itens reconhecidos → sem_entidade."""
        mock_troca.return_value = _mock_troca('A')
        mock_extrair.return_value = []
        result = node_dispatcher_modificar(
            _state('troca isso por aquilo', _CARRINHO_COM_COCA)
        )
        assert result['acao'] == 'sem_entidade'

    @patch('src.graph.nodes.extrair_itens_troca')
    def test_caso_b_item_e_variante_vai_para_troca(self, mock_troca):
        """'muda o hamburguer pra duplo' — item no carrinho + variante → trocar_variante."""
        mock_troca.return_value = _mock_troca('B', _mock_item_original(), 'duplo')
        result = node_dispatcher_modificar(
            _state('muda o hamburguer pra duplo', _CARRINHO_COM_HAMBURGUER)
        )
        assert result['acao'] == 'trocar_variante'

    @patch('src.graph.nodes.extrair_itens_troca')
    def test_caso_c_com_carrinho_vai_para_troca(self, mock_troca):
        """'muda pra duplo' — só variante, carrinho tem hamburguer → trocar_variante."""
        mock_troca.return_value = _mock_troca('C', None, 'duplo')
        result = node_dispatcher_modificar(
            _state('muda pra duplo', _CARRINHO_COM_HAMBURGUER)
        )
        assert result['acao'] == 'trocar_variante'

    @patch('src.graph.nodes.extrair_itens_troca')
    def test_caso_b_item_e_variante_dados_extracao_preenchido(self, mock_troca):
        """Dados de extração devem vir preenchidos para o handler."""
        troca = _mock_troca('B', _mock_item_original(), 'duplo')
        mock_troca.return_value = troca
        result = node_dispatcher_modificar(
            _state('muda o hamburguer pra duplo', _CARRINHO_COM_HAMBURGUER)
        )
        assert result['dados_extracao'] == troca


# ── Remoção de item do carrinho ───────────────────────────────────────────────


class TestDispatcherRemocao:
    @patch('src.graph.nodes.extrair_itens_troca')
    def test_caso_b_item_sem_variante_com_verbo_remocao(self, mock_troca):
        """'tira o hamburguer' — item no carrinho, verbo remoção → remover_item."""
        mock_troca.return_value = _mock_troca('B', _mock_item_original(), None)
        result = node_dispatcher_modificar(
            _state('tira o hamburguer', _CARRINHO_COM_HAMBURGUER)
        )
        assert result['acao'] == 'remover_item'

    @patch('src.graph.nodes.extrair_itens_troca')
    def test_remove_item_com_verbo_remove(self, mock_troca):
        """'remove o xbacon' — verbo remove → remover_item."""
        mock_troca.return_value = _mock_troca('B', _mock_item_original(), None)
        result = node_dispatcher_modificar(
            _state('remove o xbacon', _CARRINHO_COM_HAMBURGUER)
        )
        assert result['acao'] == 'remover_item'

    @patch('src.graph.nodes.extrair_itens_troca')
    @patch('src.graph.nodes.extrair_item_carrinho')
    def test_tira_tudo_via_caso_vazio(self, mock_carrinho, mock_troca):
        """'tira tudo' — caso vazio, verbo remoção, extrair_item_carrinho retorna tudo → remover_item."""
        mock_troca.return_value = _mock_troca('vazio')
        mock_carrinho.return_value = [
            {'item_id': 'lanche_001', 'variante': None, 'indices': [0]},
            {'item_id': 'bebida_001', 'variante': None, 'indices': [1]},
        ]
        result = node_dispatcher_modificar(_state('tira tudo', _CARRINHO_DOIS_ITENS))
        assert result['acao'] == 'remover_item'

    @patch('src.graph.nodes.extrair_itens_troca')
    @patch('src.graph.nodes.extrair_item_carrinho')
    def test_remocao_via_caso_vazio_item_encontrado(self, mock_carrinho, mock_troca):
        """'tira a coca' quando TrocaExtrator retorna vazio mas CarrinhoExtrator encontra → remover_item."""
        mock_troca.return_value = _mock_troca('vazio')
        mock_carrinho.return_value = [
            {'item_id': 'bebida_001', 'variante': None, 'indices': [0]}
        ]
        result = node_dispatcher_modificar(_state('tira a coca', _CARRINHO_COM_COCA))
        assert result['acao'] == 'remover_item'

    @patch('src.graph.nodes.extrair_itens_troca')
    @patch('src.graph.nodes.extrair_item_carrinho')
    @patch('src.graph.nodes.extrair')
    def test_carrinho_vazio_tentativa_remocao_vai_para_sem_entidade(
        self, mock_extrair, mock_carrinho, mock_troca
    ):
        """'tira aquilo' com carrinho vazio e sem item reconhecido → sem_entidade."""
        mock_troca.return_value = _mock_troca('vazio')
        mock_extrair.return_value = []  # nenhum item reconhecido
        result = node_dispatcher_modificar(_state('tira aquilo', []))
        mock_carrinho.assert_not_called()
        assert result['acao'] == 'sem_entidade'


# ── Adição de item ────────────────────────────────────────────────────────────


class TestDispatcherAdicao:
    @patch('src.graph.nodes.extrair_itens_troca')
    @patch('src.graph.nodes.extrair')
    def test_caso_b_item_nao_no_carrinho_vai_para_adicao(
        self, mock_extrair, mock_troca
    ):
        """'quero um xbacon' — item não está no carrinho → adicionar_item."""
        mock_troca.return_value = _mock_troca('B', None, None)
        mock_extrair.return_value = [
            {'item_id': 'lanche_003', 'quantidade': 1, 'variante': None, 'remocoes': []}
        ]
        result = node_dispatcher_modificar(_state('quero um xbacon', []))
        assert result['acao'] == 'adicionar_item'
        assert len(result['itens_extraidos']) == 1

    @patch('src.graph.nodes.extrair_itens_troca')
    @patch('src.graph.nodes.extrair')
    def test_item_com_remocao_de_ingrediente_vai_para_adicao(
        self, mock_extrair, mock_troca
    ):
        """'quero xbacon sem cebola' — item novo com remoção de ingrediente → adicionar_item."""
        mock_troca.return_value = _mock_troca('B', None, None)
        mock_extrair.return_value = [
            {
                'item_id': 'lanche_003',
                'quantidade': 1,
                'variante': None,
                'remocoes': ['cebola'],
            }
        ]
        result = node_dispatcher_modificar(_state('quero xbacon sem cebola', []))
        assert result['acao'] == 'adicionar_item'
        assert result['itens_extraidos'][0]['remocoes'] == ['cebola']

    @patch('src.graph.nodes.extrair_itens_troca')
    @patch('src.graph.nodes.extrair')
    def test_quantidade_multipla_vai_para_adicao(self, mock_extrair, mock_troca):
        """'2 xbacon' — item com quantidade → adicionar_item."""
        mock_troca.return_value = _mock_troca('B', None, None)
        mock_extrair.return_value = [
            {'item_id': 'lanche_003', 'quantidade': 2, 'variante': None, 'remocoes': []}
        ]
        result = node_dispatcher_modificar(_state('2 xbacon', []))
        assert result['acao'] == 'adicionar_item'
        assert result['itens_extraidos'][0]['quantidade'] == 2

    @patch('src.graph.nodes.extrair_itens_troca')
    @patch('src.graph.nodes.extrair')
    def test_caso_c_carrinho_vazio_item_encontrado_vai_para_adicao(
        self, mock_extrair, mock_troca
    ):
        """'muda pra lata' — caso C, carrinho vazio, 'lata' é item do cardápio → adicionar_item."""
        mock_troca.return_value = _mock_troca('C', None, 'lata')
        mock_extrair.return_value = [
            {'item_id': 'bebida_005', 'quantidade': 1, 'variante': None, 'remocoes': []}
        ]
        result = node_dispatcher_modificar(_state('muda pra lata', []))
        assert result['acao'] == 'adicionar_item'


# ── Troca incompleta → sem_entidade ──────────────────────────────────────────


class TestDispatcherSemEntidade:
    @patch('src.graph.nodes.extrair_itens_troca')
    def test_caso_b_item_sem_variante_sem_verbo_remocao(self, mock_troca):
        """'muda o hamburguer' — item no carrinho, sem variante, verbo troca → sem_entidade."""
        mock_troca.return_value = _mock_troca('B', _mock_item_original(), None)
        result = node_dispatcher_modificar(
            _state('muda o hamburguer', _CARRINHO_COM_HAMBURGUER)
        )
        assert result['acao'] == 'sem_entidade'

    @patch('src.graph.nodes.extrair_itens_troca')
    @patch('src.graph.nodes.extrair')
    def test_caso_c_carrinho_vazio_sem_item(self, mock_extrair, mock_troca):
        """'muda pra duplo' — caso C, carrinho vazio, 'duplo' não é item → sem_entidade."""
        mock_troca.return_value = _mock_troca('C', None, 'duplo')
        mock_extrair.return_value = []  # 'duplo' não é item do cardápio
        result = node_dispatcher_modificar(_state('muda pra duplo', []))
        assert result['acao'] == 'sem_entidade'

    @patch('src.graph.nodes.extrair_itens_troca')
    @patch('src.graph.nodes.extrair_item_carrinho')
    @patch('src.graph.nodes.extrair')
    def test_referencia_anaforica_sem_entidade(
        self, mock_extrair, mock_carrinho, mock_troca
    ):
        """'mais um desse' — nada reconhecido → sem_entidade."""
        mock_troca.return_value = _mock_troca('vazio')
        mock_carrinho.return_value = []
        mock_extrair.return_value = []
        result = node_dispatcher_modificar(
            _state('mais um desse', _CARRINHO_COM_HAMBURGUER)
        )
        assert result['acao'] == 'sem_entidade'

    @patch('src.graph.nodes.extrair_itens_troca')
    @patch('src.graph.nodes.extrair_item_carrinho')
    @patch('src.graph.nodes.extrair')
    def test_mensagem_sem_item_reconhecivel(
        self, mock_extrair, mock_carrinho, mock_troca
    ):
        """'pode caprichar' — sem item → sem_entidade."""
        mock_troca.return_value = _mock_troca('vazio')
        mock_carrinho.return_value = []
        mock_extrair.return_value = []
        result = node_dispatcher_modificar(
            _state('pode caprichar', _CARRINHO_COM_HAMBURGUER)
        )
        assert result['acao'] == 'sem_entidade'


# ── Edge cases ────────────────────────────────────────────────────────────────


class TestDispatcherEdgeCases:
    @patch('src.graph.nodes.extrair_itens_troca')
    @patch('src.graph.nodes.extrair')
    def test_caso_a_carrinho_vazio_sem_item_sem_entidade(
        self, mock_extrair, mock_troca
    ):
        """Caso A, carrinho vazio, extrair() não acha nada → sem_entidade."""
        mock_troca.return_value = _mock_troca('A')
        mock_extrair.return_value = []
        result = node_dispatcher_modificar(_state('troca isso por aquilo', []))
        assert result['acao'] == 'sem_entidade'

    @patch('src.graph.nodes.extrair_itens_troca')
    @patch('src.graph.nodes.extrair_item_carrinho')
    def test_extrair_item_carrinho_nao_chamado_com_carrinho_vazio(
        self, mock_carrinho, mock_troca
    ):
        """extrair_item_carrinho não deve ser chamado se carrinho está vazio."""
        mock_troca.return_value = _mock_troca('vazio')
        node_dispatcher_modificar(_state('tira a coca', []))
        mock_carrinho.assert_not_called()

    @patch('src.graph.nodes.extrair_itens_troca')
    @patch('src.graph.nodes.extrair_item_carrinho')
    def test_extrair_item_carrinho_nao_chamado_sem_verbo_remocao(
        self, mock_carrinho, mock_troca
    ):
        """extrair_item_carrinho não deve ser chamado sem verbo de remoção no caso vazio."""
        mock_troca.return_value = _mock_troca('vazio')
        node_dispatcher_modificar(_state('quero xbacon', _CARRINHO_COM_HAMBURGUER))
        mock_carrinho.assert_not_called()

    @patch('src.graph.nodes.extrair_itens_troca')
    @patch('src.graph.nodes.extrair')
    def test_caso_b_item_original_none_chama_extrair(self, mock_extrair, mock_troca):
        """Caso B sem item_original deve chamar extrair() para verificar adição."""
        mock_troca.return_value = _mock_troca('B', None, None)
        mock_extrair.return_value = []
        node_dispatcher_modificar(_state('quero xbacon', []))
        mock_extrair.assert_called_once_with('quero xbacon')
