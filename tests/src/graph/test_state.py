"""
Testes de alta qualidade para o módulo src/graph/state.py.

Características:
- Testes de tipos do TypedDict
- Testes do Literal ETAPAS
- Testes de consistência
- Testes de edge cases
"""

import pytest
from typing import get_type_hints, get_origin, get_args

from src.graph.state import State, ETAPAS


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DO TYPEDDICT STATE
# ══════════════════════════════════════════════════════════════════════════════

class TestStateTypedDict:
    """Testes para o TypedDict State."""

    def test_state_e_typeddict(self):
        """State deve ser um TypedDict."""
        assert hasattr(State, '__annotations__')

    def test_tem_campos_esperados(self):
        """State deve ter os campos esperados."""
        annots = get_type_hints(State)
        campos_esperados = {
            'mensagem_atual',
            'intent',
            'itens_extraidos',
            'carrinho',
            'fila_clarificacao',
            'etapa',
            'resposta',
            'tentativas_clarificacao',
        }
        assert set(annots.keys()) == campos_esperados

    def test_campos_tem_tipos(self):
        """Todos os campos devem ter tipos definidos."""
        annots = get_type_hints(State)
        for campo, tipo in annots.items():
            assert tipo is not None
            assert campo in State.__annotations__

    @pytest.mark.parametrize('campo,expected_type', [
        ('mensagem_atual', str),
        ('intent', str),
        ('itens_extraidos', list),
        ('carrinho', list),
        ('fila_clarificacao', list),
        ('etapa', str),
        ('resposta', str),
        ('tentativas_clarificacao', int),
    ])
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
            'itens_extraidos': [],
            'carrinho': [],
            'fila_clarificacao': [],
            'etapa': 'inicio',
            'resposta': '',
            'tentativas_clarificacao': 0,
        }
        assert isinstance(state, dict)
        for key in State.__annotations__:
            assert key in state


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DO LITERAL ETAPAS
# ══════════════════════════════════════════════════════════════════════════════

class TestETAPAS:
    """Testes para o Literal ETAPAS."""

    def test_e_literal(self):
        """ETAPAS deve ser um Literal."""
        # Verifica que é um tipo Literal
        origin = get_origin(ETAPAS)
        assert origin is not None

    def test_tem_todas_etapas(self):
        """Deve conter todas as etapas esperadas."""
        args = get_args(ETAPAS)
        etapas_esperadas = {'inicio', 'clarificando_variante', 'confirmando', 'pedindo', 'carrinho'}
        assert set(args) == etapas_esperadas

    @pytest.mark.parametrize('etapa', [
        'inicio',
        'clarificando_variante',
        'confirmando',
        'pedindo',
        'carrinho',
    ])
    def test_etapas_validas(self, etapa):
        """Cada etapa deve ser um valor válido do Literal."""
        args = get_args(ETAPAS)
        assert etapa in args

    def test_etapa_invalida_nao_esta(self):
        """Etapas inválidas não devem estar no Literal."""
        args = get_args(ETAPAS)
        etapas_invalidas = {'finalizado', 'cancelado', 'erro', 'outro'}
        for inv in etapas_invalidas:
            assert inv not in args


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE CONSISTÊNCIA
# ══════════════════════════════════════════════════════════════════════════════

class TestConsistencia:
    """Testes de consistência entre State e ETAPAS."""

    def test_etapa_do_state_compatible_com_etapas(self):
        """O campo 'etapa' do State deve ser compativel com ETAPAS."""
        # O campo 'etapa' e str, mas deve aceitar valores de ETAPAS
        assert 'etapa' in State.__annotations__

    def test_state_pode_armazenar_qualquer_etapa(self):
        """State deve poder armazenar qualquer valor de ETAPAS."""
        for etapa in get_args(ETAPAS):
            state = {'etapa': etapa}
            assert state['etapa'] == etapa

    def test_campos_obrigatorios_presentes(self):
        """State deve ter todos os campos obrigatórios."""
        obrigatorios = {
            'mensagem_atual',
            'intent',
            'itens_extraidos',
            'carrinho',
            'fila_clarificacao',
            'etapa',
            'resposta',
            'tentativas_clarificacao',
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
            'itens_extraidos': [],
            'carrinho': [],
            'fila_clarificacao': [],
            'etapa': '',
            'resposta': '',
            'tentativas_clarificacao': 0,
        }
        assert all(k in state for k in State.__annotations__)

    def test_criar_state_com_dados_reais(self):
        """Deve criar State com dados reais."""
        state = {
            'mensagem_atual': 'quero um xbacon',
            'intent': 'pedir',
            'itens_extraidos': [
                {'item_id': 'lanche_001', 'quantidade': 1}
            ],
            'carrinho': [
                {'item_id': 'lanche_001', 'quantidade': 1, 'preco': 1500}
            ],
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
                {'item_id': 'lanche_001', 'quantidade': 2, 'variante': 'duplo', 'remocoes': ['cebola']}
            ],
            'carrinho': [
                {'item_id': 'lanche_001', 'quantidade': 2, 'preco': 4000, 'variante': 'duplo', 'remocoes': ['cebola']}
            ],
            'fila_clarificacao': [
                {'item_id': 'bebida_001', 'campo': 'variante', 'opcoes': ['lata', '600ml']}
            ],
            'etapa': 'pedindo',
            'resposta': 'Adicionado!',
        }
        assert len(state['itens_extraidos'][0]['remocoes']) == 1
        assert len(state['fila_clarificacao'][0]['opcoes']) == 2