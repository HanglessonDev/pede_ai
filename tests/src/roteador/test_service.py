"""Testes para o service ClassificadorIntencoes."""

from unittest.mock import MagicMock

import pytest

from src.config.roteador_config import RoteadorConfig
from src.roteador.embedding_service import EmbeddingService
from src.roteador.modelos import (
    ExemploSimilar,
)
from src.roteador.protocolos import LLMProvider
from src.roteador.service import ClassificadorIntencoes


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def mock_llm() -> MagicMock:
    llm = MagicMock(spec=LLMProvider)
    llm.completar.return_value = 'pedir'
    return llm


@pytest.fixture
def mock_embedding_service() -> MagicMock:
    service = MagicMock(spec=EmbeddingService)
    service.tem_embeddings = True
    service.buscar_similares.return_value = []
    return service


@pytest.fixture
def config() -> RoteadorConfig:
    from src.config import get_roteador_config

    return get_roteador_config()


@pytest.fixture
def intencoes_validas() -> list[str]:
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
def prompt_template() -> str:
    return 'Classifique: {mensagem}'


@pytest.fixture
def classificador(
    mock_llm: MagicMock,
    mock_embedding_service: MagicMock,
    config: RoteadorConfig,
    prompt_template: str,
    intencoes_validas: list[str],
) -> ClassificadorIntencoes:
    return ClassificadorIntencoes(
        llm=mock_llm,
        embedding_service=mock_embedding_service,
        config=config,
        prompt_template=prompt_template,
        intencoes_validas=intencoes_validas,
    )


# ══════════════════════════════════════════════════════════════════════════════
# CLASSIFICADOR INTENCOES
# ══════════════════════════════════════════════════════════════════════════════


class TestClassificadorIntencoes:
    """Testes para ClassificadorIntencoes."""

    def test_lookup_directo(
        self,
        classificador: ClassificadorIntencoes,
    ):
        """Lookup direto deve classificar tokens unicos."""
        resultado = classificador.classificar('sim')

        assert resultado.intent == 'confirmar'
        assert resultado.caminho == 'lookup'
        assert resultado.confidence == 1.0

    def test_rag_forte(
        self,
        mock_embedding_service: MagicMock,
        classificador: ClassificadorIntencoes,
    ):
        """RAG forte deve classificar sem LLM."""
        mock_embedding_service.buscar_similares.return_value = [
            ExemploSimilar('quero xbacon', 'pedir', 0.98),
        ]

        resultado = classificador.classificar('quero xbacon')

        assert resultado.intent == 'pedir'
        assert resultado.caminho == 'rag_forte'

    def test_llm_fallback(
        self,
        mock_embedding_service: MagicMock,
        mock_llm: MagicMock,
        classificador: ClassificadorIntencoes,
    ):
        """LLM deve ser chamado quando lookup e RAG falham."""
        mock_embedding_service.buscar_similares.return_value = []
        mock_llm.completar.return_value = 'duvida'

        resultado = classificador.classificar('mensagem estranha xyz')

        assert resultado.intent == 'duvida'
        assert resultado.caminho == 'llm_fixo'

    def test_mensagem_vazia_usa_llm(
        self,
        mock_llm: MagicMock,
        classificador: ClassificadorIntencoes,
    ):
        """Mensagem vazia deve ir direto para LLM."""
        mock_llm.completar.return_value = 'saudacao'

        resultado = classificador.classificar('')

        assert resultado.caminho == 'llm_fixo'
        mock_llm.completar.assert_called_once()

    def test_mensagem_so_espacos_usa_llm(
        self,
        mock_llm: MagicMock,
        classificador: ClassificadorIntencoes,
    ):
        """Mensagem so espacos deve ir direto para LLM."""
        mock_llm.completar.return_value = 'saudacao'

        resultado = classificador.classificar('   ')

        assert resultado.caminho == 'llm_fixo'

    def test_normalizacao_trunca(
        self,
        mock_llm: MagicMock,
        classificador: ClassificadorIntencoes,
    ):
        """Mensagem longa deve ser truncada para max_chars."""
        mock_llm.completar.return_value = 'pedir'
        mensagem_longa = 'a' * 1000

        classificador.classificar(mensagem_longa)

        prompt = mock_llm.completar.call_args[0][0]
        # A mensagem truncada tem max 500 chars + template (~13 chars)
        assert len(prompt) < 520

    def test_classificar_simples_retorna_str(
        self,
        classificador: ClassificadorIntencoes,
    ):
        """classificar_simples deve retornar string."""
        resultado = classificador.classificar_simples('sim')

        assert isinstance(resultado, str)
        assert resultado == 'confirmar'

    def test_cadeia_lookup_primeiro(
        self,
        mock_embedding_service: MagicMock,
        mock_llm: MagicMock,
        classificador: ClassificadorIntencoes,
    ):
        """Lookup deve ser tentado antes de RAG."""
        resultado = classificador.classificar('oi')

        assert resultado.caminho == 'lookup'
        mock_embedding_service.buscar_similares.assert_not_called()
        mock_llm.completar.assert_not_called()

    def test_cadeia_rag_segundo(
        self,
        mock_embedding_service: MagicMock,
        mock_llm: MagicMock,
        classificador: ClassificadorIntencoes,
    ):
        """RAG deve ser tentado se lookup falhar."""
        mock_embedding_service.buscar_similares.return_value = [
            ExemploSimilar('quero xbacon', 'pedir', 0.98),
        ]

        resultado = classificador.classificar('quero xbacon')

        assert resultado.caminho == 'rag_forte'
        mock_llm.completar.assert_not_called()

    def test_cadeia_llm_ultimo(
        self,
        mock_embedding_service: MagicMock,
        mock_llm: MagicMock,
        classificador: ClassificadorIntencoes,
    ):
        """LLM deve ser o ultimo recurso."""
        mock_embedding_service.buscar_similares.return_value = []
        mock_llm.completar.return_value = 'duvida'

        classificador.classificar('abc xyz 123')

        mock_llm.completar.assert_called_once()
