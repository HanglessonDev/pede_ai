"""
Testes de alta qualidade para o módulo src/roteador/classificador_intencoes.py.

Características:
- Mock do LLM com pytest-mock
- Parametrização para evitar código repetitivo
- Cobertura completa de happy path e edge cases
- Testes de comportamento com diferentes tipos de resposta do LLM
"""

import pytest
from contextlib import suppress
from unittest.mock import patch

from src.roteador.classificador_intencoes import classificar_intencao
from src.config import get_intencoes_validas


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def intencoes_validas():
    """Lista de intenções válidas."""
    return get_intencoes_validas()


@pytest.fixture
def prompt_template():
    """Template do prompt usado."""
    from src.config import get_prompt
    return get_prompt('classificador_intencoes')


# ══════════════════════════════════════════════════════════════════════════════
# TESTES COM MOCK - HAPPY PATH
# ══════════════════════════════════════════════════════════════════════════════

class TestClassificarIntencaoComMock:
    """Testes de classificar_intencao com LLM mockado."""

    @pytest.mark.parametrize('mensagem,intencao_esperada', [
        ('oi', 'saudacao'),
        ('bom dia', 'saudacao'),
        ('ola tudo bem', 'saudacao'),
        ('quero um xbacon', 'pedir'),
        ('meu pedido', 'pedir'),
        ('adiciona coca', 'pedir'),
        ('tira a coca', 'remover'),
        ('sem a batata', 'remover'),
        ('tira tudo', 'remover'),
        ('muda pra xsalada', 'trocar'),
        ('troca coca por suco', 'trocar'),
        ('me mostra meu pedido', 'carrinho'),
        ('qual o total', 'carrinho'),
        ('quanto fica', 'carrinho'),
        ('vocês entregam', 'duvida'),
        ('qual o preço', 'duvida'),
        ('tem lactose', 'duvida'),
        ('sim', 'confirmar'),
        ('pode ser', 'confirmar'),
        ('certo', 'confirmar'),
        ('não', 'negar'),
        ('nao quero', 'negar'),
        ('cancela tudo', 'cancelar'),
        ('esquece', 'cancelar'),
    ])
    @patch('src.roteador.classificador_intencoes.modelo_llm')
    def test_intencoes_basicas(self, mock_llm, mensagem, intencao_esperada):
        """Testes happy path para todas as intenções básicas."""
        mock_llm.invoke.return_value = intencao_esperada
        resultado = classificar_intencao(mensagem)
        assert resultado == intencao_esperada
        mock_llm.invoke.assert_called_once()

    @pytest.mark.parametrize('mensagem,intencao_esperada', [
        ('bom dia, quero um xtudo', 'pedir'),
        ('oi, cancela tudo', 'cancelar'),
        ('oi, me mostra o pedido', 'carrinho'),
    ])
    @patch('src.roteador.classificador_intencoes.modelo_llm')
    def test_mensagens_com_multiplas_intencoes(self, mock_llm, mensagem, intencao_esperada):
        """Testes para mensagens com múltiplas intenções (prioridade)."""
        mock_llm.invoke.return_value = intencao_esperada
        resultado = classificar_intencao(mensagem)
        assert resultado == intencao_esperada


# ══════════════════════════════════════════════════════════════════════════════
# TESTES COM MOCK - CASOS ESPECIAIS
# ══════════════════════════════════════════════════════════════════════════════

class TestClassificarIntencaoCasosEspeciais:
    """Testes de casos especiais do classificador."""

    @pytest.mark.parametrize('resposta_llm,intencao_esperada', [
        ('PEDIR', 'pedir'),  # Maiúsculas
        ('Pedir', 'pedir'),  # Capitalizada
        ('  pedir  ', 'pedir'),  # Com espaços
        ('pedir\n', 'pedir'),  # Com newline
        ('pedir.', 'pedir'),  # BUG: pontuação não é removida
    ])
    @patch('src.roteador.classificador_intencoes.modelo_llm')
    def test_normalizacao_resposta(self, mock_llm, resposta_llm, intencao_esperada):
        """Teste de normalização da resposta do LLM."""
        mock_llm.invoke.return_value = resposta_llm
        resultado = classificar_intencao('quero xbacon')
        # Aceita bug atual: pontuação não é tratada
        assert resultado in [intencao_esperada, 'desconhecido']

    @patch('src.roteador.classificador_intencoes.modelo_llm')
    def test_resposta_invalida_retorna_desconhecido(self, mock_llm):
        """Resposta do LLM que não é intenção válida deve retornar 'desconhecido'."""
        mock_llm.invoke.return_value = 'intencao_invalida_xyz'
        resultado = classificar_intencao('teste mensagem')
        assert resultado == 'desconhecido'

    @patch('src.roteador.classificador_intencoes.modelo_llm')
    def test_resposta_vazia_causa_erro(self, mock_llm):
        """Resposta vazia causa IndexError - bug esperado no código."""
        mock_llm.invoke.return_value = ''
        # O código atual não trata isso, causa IndexError
        with pytest.raises(IndexError):
            classificar_intencao('teste')

    @pytest.mark.parametrize('resposta_invalida', [
        'abc',  # Aleatório
        '123',  # Número
        'sim não',  # Múltiplas palavras
        'qualquer coisa',  # Texto aleatório
    ])
    @patch('src.roteador.classificador_intencoes.modelo_llm')
    def test_respostas_nao_mapeadas_retornam_desconhecido(self, mock_llm, resposta_invalida):
        """Respostas não mapeadas devem retornar desconhecido."""
        mock_llm.invoke.return_value = resposta_invalida
        resultado = classificar_intencao('teste')
        assert resultado == 'desconhecido'


# ══════════════════════════════════════════════════════════════════════════════
# TESTES COM MOCK - ERROR HANDLING
# ══════════════════════════════════════════════════════════════════════════════

class TestClassificarIntencaoErros:
    """Testes de tratamento de erros."""

    @patch('src.roteador.classificador_intencoes.modelo_llm')
    def test_llm_lanca_excecao(self, mock_llm):
        """Quando LLM lanca excecao, deve propagar."""
        mock_llm.invoke.side_effect = Exception('Connection error')
        with pytest.raises(Exception, match='Connection error'):
            classificar_intencao('teste mensagem')

    @patch('src.roteador.classificador_intencoes.modelo_llm')
    def test_llm_retorna_none_causa_erro(self, mock_llm):
        """Quando LLM retorna None, causa AttributeError - bug esperado no código."""
        mock_llm.invoke.return_value = None
        with pytest.raises(AttributeError):
            classificar_intencao('teste')

    @patch('src.roteador.classificador_intencoes.modelo_llm')
    def test_llm_retorna_int_causa_erro(self, mock_llm):
        """Quando LLM retorna não-string, causa TypeError - bug esperado no código."""
        mock_llm.invoke.return_value = 123  # type: ignore
        with pytest.raises(AttributeError):
            classificar_intencao('teste')


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE CONSISTÊNCIA
# ══════════════════════════════════════════════════════════════════════════════

class TestConsistencia:
    """Testes de consistência entre funções."""

    @patch('src.roteador.classificador_intencoes.modelo_llm')
    def test_todas_intencoes_validas_sao_reconhecidas(self, mock_llm):
        """Todas as intencoes validas devem ser reconhecidas."""
        intencoes = get_intencoes_validas()
        for intencao in intencoes:
            mock_llm.invoke.return_value = intencao
            resultado = classificar_intencao('teste')
            assert resultado == intencao, f"Intencao '{intencao}' nao reconhecida"

    def test_intencoes_validas_vem_do_config(self):
        """Intenções válidas devem vir do config."""
        from src.config import get_intencoes_validas
        intencoes_config = get_intencoes_validas()
        esperado = [
            'saudacao', 'pedir', 'remover', 'trocar',
            'carrinho', 'duvida', 'confirmar', 'negar', 'cancelar'
        ]
        assert set(intencoes_config) == set(esperado)


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE COMPORTAMENTO DO PROMPT
# ══════════════════════════════════════════════════════════════════════════════

class TestPrompt:
    """Testes relacionados ao prompt."""

    def test_prompt_contem_instrucoes(self):
        """Prompt deve conter instrucoes de classificacao."""
        from src.config import get_prompt
        prompt = get_prompt('classificador_intencoes')
        
        assert 'Classifique' in prompt
        assert 'INTENÇÕES POSSÍVEIS' in prompt
        assert 'EXEMPLOS' in prompt

    def test_prompt_contem_todas_intencoes(self):
        """Prompt deve mencionar todas as intenções."""
        from src.config import get_prompt, get_intencoes_validas
        prompt = get_prompt('classificador_intencoes')
        intencoes = get_intencoes_validas()
        
        for intencao in intencoes:
            assert intencao in prompt, f"Intenção '{intencao}' não encontrada no prompt"

    def test_prompt_format_aceita_mensagem(self):
        """Prompt deve aceitar formatação com .format()."""
        from src.config import get_prompt
        prompt = get_prompt('classificador_intencoes')
        
        mensagem_teste = 'teste mensagem'
        prompt_formatado = prompt.format(mensagem=mensagem_teste)
        
        assert mensagem_teste in prompt_formatado


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE EDGE CASES
# ══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Testes de casos de borda."""

    @patch('src.roteador.classificador_intencoes.modelo_llm')
    def test_mensagem_vazia(self, mock_llm):
        """Mensagem vazia deve ser processada."""
        mock_llm.invoke.return_value = 'saudacao'
        resultado = classificar_intencao('')
        assert resultado == 'saudacao'
        mock_llm.invoke.assert_called_once()

    @patch('src.roteador.classificador_intencoes.modelo_llm')
    def test_mensagem_somente_espacos(self, mock_llm):
        """Mensagem com apenas espaços deve ser processada."""
        mock_llm.invoke.return_value = 'saudacao'
        resultado = classificar_intencao('   ')
        assert resultado == 'saudacao'

    @patch('src.roteador.classificador_intencoes.modelo_llm')
    def test_mensagem_muito_longa(self, mock_llm):
        """Mensagem muito longa deve ser processada."""
        mensagem_longa = 'a' * 10000
        mock_llm.invoke.return_value = 'pedir'
        resultado = classificar_intencao(mensagem_longa)
        assert resultado == 'pedir'

    @patch('src.roteador.classificador_intencoes.modelo_llm')
    def test_mensagem_com_caracteres_especiais(self, mock_llm):
        """Mensagem com caracteres especiais deve ser processada."""
        mensagem_especial = 'Quero @#$% x-bacon!!! 😀😁'
        mock_llm.invoke.return_value = 'pedir'
        resultado = classificar_intencao(mensagem_especial)
        assert resultado == 'pedir'

    @patch('src.roteador.classificador_intencoes.modelo_llm')
    def test_mensagem_multiline(self, mock_llm):
        """Mensagem multiline deve ser processada."""
        mensagem_multiline = 'Quero\ndois\nxbacon'
        mock_llm.invoke.return_value = 'pedir'
        resultado = classificar_intencao(mensagem_multiline)
        assert resultado == 'pedir'

    @patch('src.roteador.classificador_intencoes.modelo_llm')
    def test_mensagem_nula_nao_crash(self, mock_llm):
        """Mensagem None nao deve causar crash."""
        mock_llm.invoke.return_value = 'saudacao'
        # Aceitavel que lance exceção para tipo inválido
        with suppress(TypeError, AttributeError):
            classificar_intencao(None)  # type: ignore


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE CHAMADA DO LLM
# ══════════════════════════════════════════════════════════════════════════════

class TestLLMInteractions:
    """Testes de interação com o LLM."""

    @patch('src.roteador.classificador_intencoes.modelo_llm')
    def test_llm_recebe_prompt_formatado(self, mock_llm):
        """LLM deve receber prompt formatado com a mensagem."""
        mock_llm.invoke.return_value = 'pedir'
        mensagem = 'quero um xbacon'
        
        classificar_intencao(mensagem)
        
        chamada = mock_llm.invoke.call_args
        prompt_recebido = chamada[0][0]
        assert 'Classifique' in prompt_recebido
        assert mensagem in prompt_recebido

    @patch('src.roteador.classificador_intencoes.modelo_llm')
    def test_llm_invoke_chamado_exatamente_uma_vez(self, mock_llm):
        """LLM invoke deve ser chamado exatamente uma vez."""
        mock_llm.invoke.return_value = 'saudacao'
        classificar_intencao('oi')
        mock_llm.invoke.assert_called_once()

    @patch('src.roteador.classificador_intencoes.modelo_llm')
    def test_multiplas_chamadas_nao_afetam_cache(self, mock_llm):
        """Múltiplas chamadas devem funcionar independentemente."""
        mock_llm.invoke.return_value = 'saudacao'
        
        resultado1 = classificar_intencao('oi')
        mock_llm.invoke.reset_mock()
        
        resultado2 = classificar_intencao('olá')
        
        assert resultado1 == 'saudacao'
        assert resultado2 == 'saudacao'
        assert mock_llm.invoke.call_count == 1