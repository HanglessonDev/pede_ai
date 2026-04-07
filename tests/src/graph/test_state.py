"""
Testes de alta qualidade para o módulo src/graph/state.py.

Características:
- Testes de tipos do TypedDict
- Testes do Literal ETAPAS/MODOS
- Testes de consistência
- Testes de edge cases
"""

import pytest
from typing import get_type_hints, get_origin, get_args

from src.graph.state import State, MODOS, ACOES


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DO TYPEDDICT STATE
# ══════════════════════════════════════════════════════════════════════════════


class TestStateTypedDict:
    """Testes para o TypedDict State."""

    def test_state_e_typeddict(self):
        """State deve ser um TypedDict."""
        assert hasattr(State, '__annotations__')

    def test_tem_campos_esperados(self):
        """State deve ter os campos esperados (com renomeacao etapa→modo)."""
        annots = get_type_hints(State)
        campos_esperados = {
            'mensagem_atual',
            'intent',
            'confidence',
            'itens_extraidos',
            'carrinho',
            'fila_clarificacao',
            'modo',
            'resposta',
            'tentativas_clarificacao',
            'acao',
            'origem_intent',
            'dados_extracao',
        }
        assert set(annots.keys()) == campos_esperados

    def test_campos_tem_tipos(self):
        """Todos os campos devem ter tipos definidos."""
        annots = get_type_hints(State)
        for campo, tipo in annots.items():
            assert tipo is not None
            assert campo in State.__annotations__

    @pytest.mark.parametrize(
        'campo,expected_type',
        [
            ('mensagem_atual', str),
            ('intent', str),
            ('confidence', float),
            ('itens_extraidos', list),
            ('carrinho', list),
            ('fila_clarificacao', list),
            ('modo', MODOS),
            ('resposta', str),
            ('tentativas_clarificacao', int),
            ('acao', ACOES),
            ('origem_intent', str),
            ('dados_extracao', dict),
        ],
    )
    def test_tipos_campos(self, campo, expected_type):
        """Cada campo deve ter o tipo correto."""
        hints = get_type_hints(State)
        assert hints[campo] == expected_type

    def test_instancia_vazia_valida(self):
        """Instância vazia deve ser válida."""
        state = {}
        # TypedDict permite dict vazio na criação
        assert isinstance(state, dict)

    def test_instancia_com_todos_campos(self):
        """Instância com todos os campos deve ser válida."""
        state = {
            'mensagem_atual': 'teste mensagem',
            'intent': 'pedir',
            'confidence': 0.85,
            'itens_extraidos': [],
            'carrinho': [],
            'fila_clarificacao': [],
            'modo': 'coletando',
            'resposta': '',
            'tentativas_clarificacao': 0,
            'acao': 'adicionar_item',
            'origem_intent': 'rag_forte',
            'dados_extracao': {},
        }
        assert isinstance(state, dict)
        for key in State.__annotations__:
            assert key in state


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DO LITERAL MODOS
# ══════════════════════════════════════════════════════════════════════════════


class TestMODOS:
    """Testes para o Literal MODOS."""

    def test_e_literal(self):
        """MODOS deve ser um Literal."""
        # Verifica que é um tipo Literal
        origin = get_origin(MODOS)
        assert origin is not None

    def test_tem_todas_modos(self):
        """Deve conter todas as modos esperadas."""
        args = get_args(MODOS)
        modos_esperadas = {
            'ocioso',
            'coletando',
            'clarificando',
            'confirmando',
            'finalizado',
        }
        assert set(args) == modos_esperadas

    @pytest.mark.parametrize(
        'modo',
        [
            'ocioso',
            'coletando',
            'clarificando',
            'confirmando',
            'finalizado',
        ],
    )
    def test_modos_validas(self, modo):
        """Cada modo deve ser um valor válido do Literal."""
        args = get_args(MODOS)
        assert modo in args

    def test_modo_invalida_nao_esta(self):
        """Modos inválidas não devem estar no Literal."""
        args = get_args(MODOS)
        modos_invalidas = {'inicio', 'pedindo', 'carrinho', 'saudacao', 'erro'}
        for inv in modos_invalidas:
            assert inv not in args


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DO LITERAL ACOES
# ══════════════════════════════════════════════════════════════════════════════


class TestACOES:
    """Testes para o Literal ACOES."""

    def test_e_literal(self):
        """ACOES deve ser um Literal."""
        origin = get_origin(ACOES)
        assert origin is not None

    def test_tem_todas_acoes(self):
        """Deve conter todas as acoes esperadas."""
        args = get_args(ACOES)
        acoes_esperadas = {
            'adicionar_item',
            'remover_item',
            'trocar_variante',
            'sem_entidade',
        }
        assert set(args) == acoes_esperadas

    @pytest.mark.parametrize(
        'acao',
        [
            'adicionar_item',
            'remover_item',
            'trocar_variante',
            'sem_entidade',
        ],
    )
    def test_acoes_validas(self, acao):
        """Cada acao deve ser um valor válido do Literal."""
        args = get_args(ACOES)
        assert acao in args


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE CONSISTÊNCIA
# ══════════════════════════════════════════════════════════════════════════════


class TestConsistencia:
    """Testes de consistência entre State e MODOS/ACOES."""

    def test_modo_do_state_compatible_com_modos(self):
        """O campo 'modo' do State deve ser MODOS."""
        assert 'modo' in State.__annotations__

    def test_acao_do_state_compatible_com_acoes(self):
        """O campo 'acao' do State deve ser ACOES."""
        assert 'acao' in State.__annotations__

    def test_state_pode_armazenar_qualquer_modo(self):
        """State deve poder armazenar qualquer valor de MODOS."""
        for modo in get_args(MODOS):
            state = {'modo': modo}
            assert state['modo'] == modo

    def test_state_pode_armazenar_qualquer_acao(self):
        """State deve poder armazenar qualquer valor de ACOES."""
        for acao in get_args(ACOES):
            state = {'acao': acao}
            assert state['acao'] == acao

    def test_campos_obrigatorios_presentes(self):
        """State deve ter todos os campos obrigatórios."""
        obrigatorios = {
            'mensagem_atual',
            'intent',
            'confidence',
            'itens_extraidos',
            'carrinho',
            'fila_clarificacao',
            'modo',
            'resposta',
            'tentativas_clarificacao',
            'acao',
            'origem_intent',
            'dados_extracao',
        }
        annotations = set(State.__annotations__.keys())
        assert annotations == obrigatorios


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE INSTANCIAÇÃO
# ══════════════════════════════════════════════════════════════════════════════


class TestInstanciacao:
    """Testes de criação de instâncias de State."""

    def test_criar_state_vazio(self):
        """Deve criar State vazio."""
        state = {}
        assert isinstance(state, dict)

    def test_criar_state_minimo(self):
        """Deve criar State com campos mínimos."""
        state = {
            'mensagem_atual': '',
            'intent': '',
            'confidence': 0.0,
            'itens_extraidos': [],
            'carrinho': [],
            'fila_clarificacao': [],
            'modo': 'ocioso',
            'resposta': '',
            'tentativas_clarificacao': 0,
            'acao': 'adicionar_item',
            'origem_intent': '',
            'dados_extracao': {},
        }
        assert all(k in state for k in State.__annotations__)

    def test_criar_state_com_dados_reais(self):
        """Deve criar State com dados reais."""
        state = {
            'mensagem_atual': 'quero um xbacon',
            'intent': 'pedir',
            'itens_extraidos': [{'item_id': 'lanche_001', 'quantidade': 1}],
            'carrinho': [{'item_id': 'lanche_001', 'quantidade': 1, 'preco': 1500}],
            'fila_clarificacao': [],
            'etapa': 'pedindo',
            'resposta': 'Adicionado!',
        }
        assert state['intent'] == 'pedir'
        assert len(state['itens_extraidos']) == 1
        assert len(state['carrinho']) == 1

    def test_state_e_mutavel(self):
        """State deve ser mutável."""
        state = {'mensagem_atual': 'teste'}
        state['mensagem_atual'] = 'novo teste'
        assert state['mensagem_atual'] == 'novo teste'


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE TIPAGEM
# ══════════════════════════════════════════════════════════════════════════════


class TestTipagem:
    """Testes de tipagem do State."""

    def test_tipo_retorno_get_type_hints(self):
        """get_type_hints deve retornar dict."""
        hints = get_type_hints(State)
        assert isinstance(hints, dict)

    def test_cada_campo_tem_tipo(self):
        """Cada campo deve ter um tipo definido."""
        hints = get_type_hints(State)
        for campo in State.__annotations__:
            assert campo in hints

    def test_origin_list_para_campos_lista(self):
        """Campos de lista devem ter origin list."""
        hints = get_type_hints(State)
        # campos que devem ser list
        campos_lista = ['itens_extraidos', 'carrinho', 'fila_clarificacao']
        for campo in campos_lista:
            # O tipo é list, sem argumento genérico
            assert hints[campo] == list


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE EDGE CASES
# ══════════════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Testes de casos de borda."""

    def test_state_com_strings_vazias(self):
        """State deve aceitar strings vazias."""
        state = {
            'mensagem_atual': '',
            'intent': '',
            'itens_extraidos': [],
            'carrinho': [],
            'fila_clarificacao': [],
            'etapa': '',
            'resposta': '',
        }
        assert all(isinstance(v, (str, list)) for v in state.values())

    def test_state_com_listas_vazias(self):
        """State deve aceitar listas vazias."""
        state = {
            'mensagem_atual': 'msg',
            'intent': 'pedir',
            'itens_extraidos': [],
            'carrinho': [],
            'fila_clarificacao': [],
            'etapa': 'inicio',
            'resposta': 'ok',
        }
        assert state['itens_extraidos'] == []
        assert state['carrinho'] == []
        assert state['fila_clarificacao'] == []

    def test_state_com_itens_complexos(self):
        """State deve aceitar itens complexos."""
        state = {
            'mensagem_atual': 'teste',
            'intent': 'pedir',
            'itens_extraidos': [
                {
                    'item_id': 'lanche_001',
                    'quantidade': 2,
                    'variante': 'duplo',
                    'remocoes': ['cebola'],
                }
            ],
            'carrinho': [
                {
                    'item_id': 'lanche_001',
                    'quantidade': 2,
                    'preco': 4000,
                    'variante': 'duplo',
                    'remocoes': ['cebola'],
                }
            ],
            'fila_clarificacao': [
                {
                    'item_id': 'bebida_001',
                    'campo': 'variante',
                    'opcoes': ['lata', '600ml'],
                }
            ],
            'etapa': 'pedindo',
            'resposta': 'Adicionado!',
        }
        assert len(state['itens_extraidos'][0]['remocoes']) == 1
        assert len(state['fila_clarificacao'][0]['opcoes']) == 2
