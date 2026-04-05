"""Testes para o classificador LLM fallback."""

from unittest.mock import MagicMock

import pytest

from src.roteador.classificadores.llm import ClassificadorLLM
from src.roteador.modelos import ResultadoClassificacao
from src.roteador.protocolos import LLMProvider


# ══════════════════════════════════════════════════════════════════════════════
# CLASSIFICADOR LLM
# ══════════════════════════════════════════════════════════════════════════════


class TestClassificadorLLM:
    """Testes para ClassificadorLLM."""

    @pytest.fixture
    def mock_llm(self) -> LLMProvider:
        """Mock do LLM provider."""
        llm = MagicMock(spec=LLMProvider)
        llm.completar.return_value = 'pedir'
        return llm

    @pytest.fixture
    def intencoes_validas(self) -> list[str]:
        """Lista de intents validas."""
        return [
            'saudacao',
            'pedir',
            'remover',
            'trocar',
            'carrinho',
            'duvida',
            'confirmar',
            'negar',
            'cancelar',
        ]

    @pytest.fixture
    def prompt_template(self) -> str:
        """Template do prompt."""
        return 'Classifique: {mensagem}'

    @pytest.fixture
    def classificador(
        self,
        mock_llm: LLMProvider,
        prompt_template: str,
        intencoes_validas: list[str],
    ) -> ClassificadorLLM:
        """Classificador LLM com mock."""
        return ClassificadorLLM(mock_llm, prompt_template, intencoes_validas)

    def test_classifica_com_sucesso(
        self,
        classificador: ClassificadorLLM,
    ):
        """Deve classificar via LLM."""
        resultado = classificador.classificar('quero um lanche')

        assert resultado.intent == 'pedir'
        assert resultado.confidence == 1.0
        assert resultado.caminho == 'llm_fixo'

    def test_resposta_invalida_retorna_desconhecido(
        self,
        mock_llm: LLMProvider,
        classificador: ClassificadorLLM,
    ):
        """Resposta invalida deve retornar 'desconhecido'."""
        mock_llm.completar.return_value = 'intencao_xyz'
        resultado = classificador.classificar('teste')

        assert resultado.intent == 'desconhecido'

    def test_resposta_vazia_retorna_desconhecido(
        self,
        mock_llm: LLMProvider,
        classificador: ClassificadorLLM,
    ):
        """Resposta vazia deve retornar 'desconhecido'."""
        mock_llm.completar.return_value = ''
        resultado = classificador.classificar('teste')

        assert resultado.intent == 'desconhecido'

    def test_resposta_com_espacos(
        self,
        mock_llm: LLMProvider,
        classificador: ClassificadorLLM,
    ):
        """Deve extrair primeira palavra da resposta."""
        mock_llm.completar.return_value = '  pedir  '
        resultado = classificador.classificar('teste')

        assert resultado.intent == 'pedir'

    def test_resposta_maiusculas(
        self,
        mock_llm: LLMProvider,
        classificador: ClassificadorLLM,
    ):
        """Deve normalizar para lowercase."""
        mock_llm.completar.return_value = 'PEDIR'
        resultado = classificador.classificar('teste')

        assert resultado.intent == 'pedir'

    def test_resposta_multipalavras(
        self,
        mock_llm: LLMProvider,
        classificador: ClassificadorLLM,
    ):
        """Deve usar apenas a primeira palavra."""
        mock_llm.completar.return_value = 'pedir lanche'
        resultado = classificador.classificar('teste')

        assert resultado.intent == 'pedir'

    def test_primeira_palavra_invalida_segunda_valida(
        self,
        mock_llm: LLMProvider,
        classificador: ClassificadorLLM,
    ):
        """Se primeira palavra e invalida, retorna desconhecido."""
        mock_llm.completar.return_value = 'xyz pedir'
        resultado = classificador.classificar('teste')

        assert resultado.intent == 'desconhecido'

    def test_llm_recebe_prompt_formatado(
        self,
        mock_llm: LLMProvider,
        classificador: ClassificadorLLM,
    ):
        """LLM deve receber prompt com a mensagem."""
        classificador.classificar('quero pizza')

        mock_llm.completar.assert_called_once()
        prompt = mock_llm.completar.call_args[0][0]
        assert 'quero pizza' in prompt

    def test_llm_recebe_max_tokens(
        self,
        mock_llm: LLMProvider,
        classificador: ClassificadorLLM,
    ):
        """LLM deve receber max_tokens=10."""
        classificador.classificar('teste')

        mock_llm.completar.assert_called_once()
        max_tokens = mock_llm.completar.call_args[1].get('max_tokens')
        assert max_tokens == 10

    def test_nunca_retorna_none(
        self,
        classificador: ClassificadorLLM,
    ):
        """LLM nunca retorna None — e fallback definitivo."""
        resultado = classificador.classificar('qualquer coisa')

        assert resultado is not None
        assert isinstance(resultado, ResultadoClassificacao)

    def test_metadata_preenchida(
        self,
        classificador: ClassificadorLLM,
    ):
        """Resultado deve ter metadata correta."""
        resultado = classificador.classificar('teste mensagem')

        assert resultado.top1_texto == ''
        assert resultado.top1_intencao == ''
        assert resultado.mensagem_norm == 'teste mensagem'
