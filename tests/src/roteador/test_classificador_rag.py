"""Testes para o classificador RAG."""

from unittest.mock import MagicMock

import pytest

from src.config.roteador_config import RoteadorConfig
from src.roteador.classificadores.rag import ClassificadorRAG
from src.roteador.embedding_service import EmbeddingService
from src.roteador.modelos import ExemploSimilar
from src.roteador.protocolos import LLMProvider


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def mock_embedding_service() -> MagicMock:
    """Mock do EmbeddingService."""
    service = MagicMock(spec=EmbeddingService)
    service.tem_embeddings = True
    service.buscar_similares.return_value = [
        ExemploSimilar('quero xbacon', 'pedir', 0.90),
        ExemploSimilar('me ve lanche', 'pedir', 0.80),
    ]
    return service


@pytest.fixture
def mock_llm() -> MagicMock:
    """Mock do LLM provider."""
    llm = MagicMock(spec=LLMProvider)
    llm.completar.return_value = 'pedir'
    return llm


@pytest.fixture
def config() -> RoteadorConfig:
    """Config padrao."""
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
    mock_embedding_service: MagicMock,
    mock_llm: MagicMock,
    config: RoteadorConfig,
    prompt_template: str,
    intencoes_validas: list[str],
) -> ClassificadorRAG:
    return ClassificadorRAG(
        embedding_service=mock_embedding_service,
        config=config,
        llm=mock_llm,
        prompt_template=prompt_template,
        intencoes_validas=intencoes_validas,
    )


# ══════════════════════════════════════════════════════════════════════════════
# CLASSIFICADOR RAG
# ══════════════════════════════════════════════════════════════════════════════


class TestClassificadorRAG:
    """Testes para ClassificadorRAG."""

    def test_rag_forte_skip_llm(
        self,
        mock_embedding_service: MagicMock,
        mock_llm: MagicMock,
        classificador: ClassificadorRAG,
    ):
        """RAG forte (>= 0.95) nao deve chamar LLM."""
        mock_embedding_service.buscar_similares.return_value = [
            ExemploSimilar('cancela tudo', 'cancelar', 0.98),
        ]

        resultado = classificador.classificar('cancela tudo')

        mock_llm.completar.assert_not_called()
        assert resultado is not None
        assert resultado.intent == 'cancelar'
        assert resultado.caminho == 'rag_forte'
        assert resultado.confidence == 0.98

    def test_rag_medio_chama_llm(
        self,
        mock_embedding_service: MagicMock,
        mock_llm: MagicMock,
        classificador: ClassificadorRAG,
    ):
        """RAG medio (0.50-0.95) deve chamar LLM."""
        mock_embedding_service.buscar_similares.return_value = [
            ExemploSimilar('quero xbacon', 'pedir', 0.75),
        ]

        resultado = classificador.classificar('quero lanche')

        mock_llm.completar.assert_called_once()
        assert resultado is not None
        assert resultado.caminho == 'llm_rag'

    def test_rag_fraco_retorna_none(
        self,
        mock_embedding_service: MagicMock,
        classificador: ClassificadorRAG,
    ):
        """RAG fraco (< 0.50) deve retornar None."""
        mock_embedding_service.buscar_similares.return_value = [
            ExemploSimilar('abc', 'desconhecido', 0.40),
        ]

        resultado = classificador.classificar('mensagem estranha')

        assert resultado is None

    def test_sem_embeddings_retorna_none(
        self,
        mock_embedding_service: MagicMock,
        classificador: ClassificadorRAG,
    ):
        """Sem embeddings deve retornar None."""
        mock_embedding_service.tem_embeddings = False

        resultado = classificador.classificar('teste')

        assert resultado is None

    def test_sem_similares_retorna_none(
        self,
        mock_embedding_service: MagicMock,
        classificador: ClassificadorRAG,
    ):
        """Sem similares deve retornar None."""
        mock_embedding_service.buscar_similares.return_value = []

        resultado = classificador.classificar('teste')

        assert resultado is None

    def test_llm_fallback_usa_votacao(
        self,
        mock_embedding_service: MagicMock,
        mock_llm: MagicMock,
        classificador: ClassificadorRAG,
    ):
        """Se LLM retorna invalido, deve usar votacao RAG."""
        mock_llm.completar.return_value = 'intencao_invalida'
        mock_embedding_service.buscar_similares.return_value = [
            ExemploSimilar('quero xbacon', 'pedir', 0.75),
        ]

        resultado = classificador.classificar('quero lanche')

        assert resultado is not None
        assert resultado.intent == 'pedir'

    def test_resultado_contem_metadata(
        self,
        mock_embedding_service: MagicMock,
        classificador: ClassificadorRAG,
    ):
        """Resultado deve conter metadata."""
        mock_embedding_service.buscar_similares.return_value = [
            ExemploSimilar('quero xbacon', 'pedir', 0.96),
        ]

        resultado = classificador.classificar('quero lanche')

        assert resultado is not None
        assert resultado.top1_texto == 'quero xbacon'
        assert resultado.top1_intencao == 'pedir'
        assert resultado.confidence == 0.96
