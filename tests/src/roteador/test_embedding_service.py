"""Testes para EmbeddingService."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.roteador.embedding_service import EmbeddingService
from src.roteador.modelos import ExemploClassificacao


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def provider() -> MagicMock:
    """Mock do EmbeddingProvider."""
    mock = MagicMock()
    mock.embed.return_value = [0.1] * 384
    mock.embed_batch.return_value = [[0.1] * 384]
    return mock


@pytest.fixture
def exemplos_path(tmp_path: Path) -> Path:
    """Path temporario para arquivo de exemplos."""
    return tmp_path / 'exemplos.json'


@pytest.fixture
def cache_path(tmp_path: Path) -> Path:
    """Path temporario para arquivo de cache."""
    return tmp_path / 'cache.json'


@pytest.fixture
def exemplos_dados() -> list[dict]:
    """Dados de exemplo para JSON."""
    return [
        {'texto': 'quero um lanche', 'intencao': 'pedir'},
        {'texto': 'me ve o cardapio', 'intencao': 'duvida'},
        {'texto': 'oi tudo bem', 'intencao': 'saudacao'},
    ]


@pytest.fixture
def embeddings_dados() -> list[list[float]]:
    """Dados de embeddings para JSON (384 dim)."""
    return [
        [0.1] * 384,
        [0.2] * 384,
        [0.3] * 384,
    ]


# ══════════════════════════════════════════════════════════════════════════════
# CARREGAR EXEMPLOS
# ══════════════════════════════════════════════════════════════════════════════


class TestCarregarExemplos:
    """Testes para _carregar_exemplos."""

    def test_arquivo_nao_existe_retorna_vazio(
        self,
        provider: MagicMock,
        exemplos_path: Path,
        cache_path: Path,
    ):
        """Arquivo nao existente deve retornar lista vazia."""
        service = EmbeddingService(provider, exemplos_path, cache_path)

        assert service.exemplos == []

    def test_arquivo_existe_carrega_corretamente(
        self,
        provider: MagicMock,
        exemplos_path: Path,
        cache_path: Path,
        exemplos_dados: list[dict],
    ):
        """Arquivo existente deve carregar exemplos corretamente."""
        with open(exemplos_path, 'w', encoding='utf-8') as f:
            json.dump(exemplos_dados, f)

        service = EmbeddingService(provider, exemplos_path, cache_path)

        assert len(service.exemplos) == 3
        assert service.exemplos[0] == ExemploClassificacao('quero um lanche', 'pedir')
        assert service.exemplos[1] == ExemploClassificacao('me ve o cardapio', 'duvida')
        assert service.exemplos[2] == ExemploClassificacao('oi tudo bem', 'saudacao')


# ══════════════════════════════════════════════════════════════════════════════
# CARREGAR CACHE
# ══════════════════════════════════════════════════════════════════════════════


class TestCarregarCache:
    """Testes para _carregar_cache."""

    def test_cache_nao_existe_retorna_vazio(
        self,
        provider: MagicMock,
        exemplos_path: Path,
        cache_path: Path,
    ):
        """Cache nao existente deve retornar lista vazia."""
        service = EmbeddingService(provider, exemplos_path, cache_path)

        assert service.tem_embeddings is False

    def test_cache_existe_carrega_corretamente(
        self,
        provider: MagicMock,
        exemplos_path: Path,
        cache_path: Path,
        embeddings_dados: list[list[float]],
    ):
        """Cache existente deve carregar embeddings corretamente."""
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(embeddings_dados, f)

        service = EmbeddingService(provider, exemplos_path, cache_path)

        assert service.tem_embeddings is True
        assert len(service._embeddings) == 3


# ══════════════════════════════════════════════════════════════════════════════
# BUSCAR SIMILARES
# ══════════════════════════════════════════════════════════════════════════════


class TestBuscarSimilares:
    """Testes para buscar_similares."""

    def test_exemplos_vazios_retorna_vazio(
        self,
        provider: MagicMock,
        exemplos_path: Path,
        cache_path: Path,
    ):
        """Sem exemplos deve retornar lista vazia."""
        service = EmbeddingService(provider, exemplos_path, cache_path)

        resultado = service.buscar_similares('teste')

        assert resultado == []

    @pytest.mark.parametrize('top_k', [1, 3, 5])
    def test_busca_normal_retorna_top_k(
        self,
        provider: MagicMock,
        exemplos_path: Path,
        cache_path: Path,
        exemplos_dados: list[dict],
        embeddings_dados: list[list[float]],
        top_k: int,
    ):
        """Busca normal deve retornar ate top_k resultados."""
        with open(exemplos_path, 'w', encoding='utf-8') as f:
            json.dump(exemplos_dados, f)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(embeddings_dados, f)

        provider.embed.return_value = [0.15] * 384
        service = EmbeddingService(provider, exemplos_path, cache_path)

        resultado = service.buscar_similares('teste', top_k=top_k)

        assert len(resultado) <= top_k

    def test_similaridade_abaixo_min_filtra(
        self,
        provider: MagicMock,
        exemplos_path: Path,
        cache_path: Path,
        exemplos_dados: list[dict],
    ):
        """Similaridade abaixo de min_similarity deve ser filtrada."""
        embeddings_opostos = [
            [1.0, 0.0] + [0.0] * 382,
            [1.0, 0.0] + [0.0] * 382,
            [1.0, 0.0] + [0.0] * 382,
        ]
        with open(exemplos_path, 'w', encoding='utf-8') as f:
            json.dump(exemplos_dados, f)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(embeddings_opostos, f)

        provider.embed.return_value = [0.0, 1.0] + [0.0] * 382
        service = EmbeddingService(provider, exemplos_path, cache_path)

        resultado = service.buscar_similares('teste', min_similarity=0.55)

        assert resultado == []


# ══════════════════════════════════════════════════════════════════════════════
# ATUALIZAR CACHE
# ══════════════════════════════════════════════════════════════════════════════


class TestAtualizarCache:
    """Testes para atualizar_cache."""

    def test_ja_tem_todos_nao_faz_nada(
        self,
        provider: MagicMock,
        exemplos_path: Path,
        cache_path: Path,
        exemplos_dados: list[dict],
        embeddings_dados: list[list[float]],
    ):
        """Ja having all embeddings deve retornar sem fazer nada."""
        with open(exemplos_path, 'w', encoding='utf-8') as f:
            json.dump(exemplos_dados, f)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(embeddings_dados, f)

        provider.embed_batch.reset_mock()
        service = EmbeddingService(provider, exemplos_path, cache_path)

        service.atualizar_cache()

        provider.embed_batch.assert_not_called()

    def test_faltam_embeddings_gera_e_salva(
        self,
        provider: MagicMock,
        exemplos_path: Path,
        cache_path: Path,
        exemplos_dados: list[dict],
    ):
        """Faltando embeddings deve gerar e salvar."""
        embeddings_parcial = [[0.1] * 384]
        with open(exemplos_path, 'w', encoding='utf-8') as f:
            json.dump(exemplos_dados, f)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(embeddings_parcial, f)

        provider.embed_batch.return_value = [
            [0.2] * 384,
            [0.3] * 384,
        ]
        service = EmbeddingService(provider, exemplos_path, cache_path)

        service.atualizar_cache()

        provider.embed_batch.assert_called_once()

        with open(cache_path, encoding='utf-8') as f:
            cache_lido = json.load(f)

        assert len(cache_lido) == 3


# ══════════════════════════════════════════════════════════════════════════════
# GERAR EMBEDDING
# ══════════════════════════════════════════════════════════════════════════════


class TestGerarEmbedding:
    """Testes para gerar_embedding."""

    def test_proxy_para_provider(
        self,
        provider: MagicMock,
        exemplos_path: Path,
        cache_path: Path,
    ):
        """gerar_embedding deve chamar provider.embed."""
        service = EmbeddingService(provider, exemplos_path, cache_path)

        resultado = service.gerar_embedding('teste texto')

        provider.embed.assert_called_once_with('teste texto')
        assert resultado == [0.1] * 384


# ══════════════════════════════════════════════════════════════════════════════
# PROPRIEDADES
# ══════════════════════════════════════════════════════════════════════════════


class TestPropriedades:
    """Testes para propriedades."""

    def test_exemplos_retorna_lista(
        self,
        provider: MagicMock,
        exemplos_path: Path,
        cache_path: Path,
        exemplos_dados: list[dict],
    ):
        """exemplos deve retornar lista copiada."""
        with open(exemplos_path, 'w', encoding='utf-8') as f:
            json.dump(exemplos_dados, f)

        service = EmbeddingService(provider, exemplos_path, cache_path)

        exemplos = service.exemplos
        assert isinstance(exemplos, list)
        assert len(exemplos) == 3

    def test_tem_embeddings_false_quando_vazio(
        self,
        provider: MagicMock,
        exemplos_path: Path,
        cache_path: Path,
    ):
        """tem_embeddings deve ser False quando vazio."""
        service = EmbeddingService(provider, exemplos_path, cache_path)

        assert service.tem_embeddings is False

    def test_tem_embeddings_true_quando_com_dados(
        self,
        provider: MagicMock,
        exemplos_path: Path,
        cache_path: Path,
        embeddings_dados: list[list[float]],
    ):
        """tem_embeddings deve ser True quando tem dados."""
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(embeddings_dados, f)

        service = EmbeddingService(provider, exemplos_path, cache_path)

        assert service.tem_embeddings is True
