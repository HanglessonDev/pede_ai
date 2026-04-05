"""Testes para EmbeddingService."""

import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.roteador.embedding_service import EmbeddingService
from src.roteador.modelos import ExemploClassificacao

# Import opcional — funcao ainda nao existe (TDD)
try:
    from src.roteador.embedding_service import _hash_texto
except ImportError:
    _hash_texto = None  # type: ignore[misc,assignment]


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

        assert cache_lido.get('format') == 2
        assert len(cache_lido['embeddings']) == 3


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


# ══════════════════════════════════════════════════════════════════════════════
# FUNCAO HASH — TESTES UNITARIOS
# ══════════════════════════════════════════════════════════════════════════════


class TestHashTexto:
    """Testes para _hash_texto."""

    def test_mesmo_texto_mesmo_hash(self):
        """Mesmo texto deve gerar mesmo hash sempre."""
        h1 = _hash_texto('quero um lanche')
        h2 = _hash_texto('quero um lanche')

        assert h1 == h2

    def test_textos_diferentes_hashes_diferentes(self):
        """Textos diferentes devem gerar hashes diferentes."""
        h1 = _hash_texto('quero um lanche')
        h2 = _hash_texto('me ve o cardapio')

        assert h1 != h2

    def test_normalizacao_maiusculas(self):
        """Texto com maiusculas deve gerar mesmo hash que minusculas."""
        h1 = _hash_texto('Quero Um Lanche')
        h2 = _hash_texto('quero um lanche')

        assert h1 == h2

    def test_normalizacao_espacos(self):
        """Texto com espacos extras deve gerar mesmo hash apos strip."""
        h1 = _hash_texto('  quero um lanche  ')
        h2 = _hash_texto('quero um lanche')

        assert h1 == h2

    def test_hash_e_hexadecimal_sha256(self):
        """Hash deve ser hex digest de SHA256 do texto normalizado."""
        texto = 'teste'
        esperado = hashlib.sha256(texto.encode()).hexdigest()
        assert _hash_texto(texto) == esperado

    def test_hash_tamanho_64_caracteres(self):
        """SHA256 hex digest tem 64 caracteres."""
        h = _hash_texto('qualquer texto')

        assert len(h) == 64


# ══════════════════════════════════════════════════════════════════════════════
# MIGRACAO DE FORMATO
# ══════════════════════════════════════════════════════════════════════════════


class TestMigracaoFormato:
    """Testes para migracao do cache formato lista (1) para dict com hashes (2)."""

    def test_migra_formato_lista_para_dict(
        self,
        provider: MagicMock,
        exemplos_path: Path,
        cache_path: Path,
        exemplos_dados: list[dict],
        embeddings_dados: list[list[float]],
    ):
        """Cache formato 1 (lista) deve ser migrado para formato 2 (dict com hashes)."""
        with open(exemplos_path, 'w', encoding='utf-8') as f:
            json.dump(exemplos_dados, f)

        # Formato antigo: lista posicional com "format": 1
        cache_antigo = {
            'format': 1,
            'embeddings': embeddings_dados,
        }
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_antigo, f)

        service = EmbeddingService(provider, exemplos_path, cache_path)

        # Deve ter migrado e ter embeddings
        assert service.tem_embeddings is True
        assert len(service._embeddings) == 3

        # O cache no disco deve estar no formato novo
        with open(cache_path, encoding='utf-8') as f:
            cache_salvo = json.load(f)

        assert cache_salvo.get('format') == 2
        assert 'embeddings' in cache_salvo
        assert isinstance(cache_salvo['embeddings'], dict)

    def test_migra_e_preserva_valores_embeddings(
        self,
        provider: MagicMock,
        exemplos_path: Path,
        cache_path: Path,
        exemplos_dados: list[dict],
    ):
        """Migracao deve preservar os valores dos embeddings originais."""
        embeddings_unicos = [
            [0.11] * 384,
            [0.22] * 384,
            [0.33] * 384,
        ]
        with open(exemplos_path, 'w', encoding='utf-8') as f:
            json.dump(exemplos_dados, f)

        cache_antigo = {
            'format': 1,
            'embeddings': embeddings_unicos,
        }
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_antigo, f)

        service = EmbeddingService(provider, exemplos_path, cache_path)

        # Verifica que os embeddings foram migrados com valores corretos
        h0 = _hash_texto(exemplos_dados[0]['texto'])
        h1 = _hash_texto(exemplos_dados[1]['texto'])
        h2 = _hash_texto(exemplos_dados[2]['texto'])

        cache_migrado = service._embeddings_dict

        assert cache_migrado[h0] == embeddings_unicos[0]
        assert cache_migrado[h1] == embeddings_unicos[1]
        assert cache_migrado[h2] == embeddings_unicos[2]

    def test_cache_sem_format_assume_lista(
        self,
        provider: MagicMock,
        exemplos_path: Path,
        cache_path: Path,
        exemplos_dados: list[dict],
        embeddings_dados: list[list[float]],
    ):
        """Cache sem campo 'format' (lista pura) deve ser tratado como formato 1."""
        with open(exemplos_path, 'w', encoding='utf-8') as f:
            json.dump(exemplos_dados, f)

        # Formato antigo puro (sem campo format)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(embeddings_dados, f)

        service = EmbeddingService(provider, exemplos_path, cache_path)

        assert service.tem_embeddings is True
        assert len(service._embeddings) == 3


# ══════════════════════════════════════════════════════════════════════════════
# CACHE COM HASH — CARREGAMENTO
# ══════════════════════════════════════════════════════════════════════════════


class TestCacheComHash:
    """Testes para carregamento do cache no formato dict com hashes."""

    def test_carrega_formato_novo_direto(
        self,
        provider: MagicMock,
        exemplos_path: Path,
        cache_path: Path,
        exemplos_dados: list[dict],
    ):
        """Cache formato 2 deve carregar direto sem migracao."""
        embeddings = {
            _hash_texto(exemplos_dados[0]['texto']): [0.1] * 384,
            _hash_texto(exemplos_dados[1]['texto']): [0.2] * 384,
            _hash_texto(exemplos_dados[2]['texto']): [0.3] * 384,
        }
        cache_novo = {
            'format': 2,
            'embeddings': embeddings,
        }
        with open(exemplos_path, 'w', encoding='utf-8') as f:
            json.dump(exemplos_dados, f)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_novo, f)

        service = EmbeddingService(provider, exemplos_path, cache_path)

        assert service.tem_embeddings is True
        assert len(service._embeddings) == 3

    def test_embeddings_faltantes_por_hash(
        self,
        provider: MagicMock,
        exemplos_path: Path,
        cache_path: Path,
        exemplos_dados: list[dict],
    ):
        """Se exemplo nao tem hash no cache, nao incluir na lista alinhada."""
        # Cache so tem hash do primeiro exemplo
        embeddings = {
            _hash_texto(exemplos_dados[0]['texto']): [0.1] * 384,
        }
        cache_novo = {
            'format': 2,
            'embeddings': embeddings,
        }
        with open(exemplos_path, 'w', encoding='utf-8') as f:
            json.dump(exemplos_dados, f)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_novo, f)

        service = EmbeddingService(provider, exemplos_path, cache_path)

        # So o primeiro exemplo tem embedding
        assert len(service._embeddings) == 1

    def test_resistencia_reordenacao(
        self,
        provider: MagicMock,
        exemplos_path: Path,
        cache_path: Path,
        exemplos_dados: list[dict],
    ):
        """Reordenar exemplos no JSON ainda associa embeddings corretamente via hash."""
        # Cache com hashes em ordem diferente dos exemplos
        embeddings = {
            _hash_texto(exemplos_dados[2]['texto']): [0.3] * 384,  # ultimo exemplo primeiro
            _hash_texto(exemplos_dados[0]['texto']): [0.1] * 384,
            _hash_texto(exemplos_dados[1]['texto']): [0.2] * 384,
        }
        cache_novo = {
            'format': 2,
            'embeddings': embeddings,
        }
        with open(exemplos_path, 'w', encoding='utf-8') as f:
            json.dump(exemplos_dados, f)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_novo, f)

        service = EmbeddingService(provider, exemplos_path, cache_path)

        # Embeddings devem estar na ordem correta dos exemplos
        assert service._embeddings[0] == [0.1] * 384
        assert service._embeddings[1] == [0.2] * 384
        assert service._embeddings[2] == [0.3] * 384

    def test_insercao_meio_exemplo_novo(
        self,
        provider: MagicMock,
        exemplos_path: Path,
        cache_path: Path,
    ):
        """Inserir exemplo novo no meio: apenas aquele fica sem embedding."""
        exemplos = [
            {'texto': 'quero um lanche', 'intencao': 'pedir'},
            {'texto': 'exemplo novo inserido', 'intencao': 'teste'},
            {'texto': 'oi tudo bem', 'intencao': 'saudacao'},
        ]
        # Cache tem hashes apenas dos exemplos originais (sem o novo do meio)
        embeddings = {
            _hash_texto('quero um lanche'): [0.1] * 384,
            _hash_texto('oi tudo bem'): [0.3] * 384,
        }
        cache_novo = {
            'format': 2,
            'embeddings': embeddings,
        }
        with open(exemplos_path, 'w', encoding='utf-8') as f:
            json.dump(exemplos, f)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_novo, f)

        service = EmbeddingService(provider, exemplos_path, cache_path)

        # 2 embeddings existentes (exemplo do meio nao tem)
        assert len(service._embeddings) == 2
        # O exemplo do meio nao tem embedding ainda
        assert service._embeddings[0] == [0.1] * 384
        assert service._embeddings[1] == [0.3] * 384


# ══════════════════════════════════════════════════════════════════════════════
# ATUALIZAR CACHE COM HASH
# ══════════════════════════════════════════════════════════════════════════════


class TestAtualizarCacheComHash:
    """Testes para atualizar_cache no novo formato com hashes."""

    def test_gera_apenas_faltantes(
        self,
        provider: MagicMock,
        exemplos_path: Path,
        cache_path: Path,
        exemplos_dados: list[dict],
    ):
        """atualizar_cache gera embeddings apenas para hashes ausentes."""
        # Cache tem apenas o primeiro exemplo
        embeddings = {
            _hash_texto(exemplos_dados[0]['texto']): [0.1] * 384,
        }
        cache_novo = {
            'format': 2,
            'embeddings': embeddings,
        }
        with open(exemplos_path, 'w', encoding='utf-8') as f:
            json.dump(exemplos_dados, f)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_novo, f)

        provider.embed_batch.return_value = [
            [0.2] * 384,
            [0.3] * 384,
        ]
        provider.embed_batch.reset_mock()
        service = EmbeddingService(provider, exemplos_path, cache_path)

        service.atualizar_cache()

        # Deve gerar embeddings apenas para os 2 faltantes
        provider.embed_batch.assert_called_once()
        chamados = provider.embed_batch.call_args[0][0]
        assert len(chamados) == 2
        assert exemplos_dados[1]['texto'] in chamados
        assert exemplos_dados[2]['texto'] in chamados

    def test_salva_formato_dict_com_hash(
        self,
        provider: MagicMock,
        exemplos_path: Path,
        cache_path: Path,
        exemplos_dados: list[dict],
    ):
        """atualizar_cache salva no formato dict com hashes."""
        # Sem cache inicial
        with open(exemplos_path, 'w', encoding='utf-8') as f:
            json.dump(exemplos_dados, f)

        provider.embed_batch.return_value = [
            [0.1] * 384,
            [0.2] * 384,
            [0.3] * 384,
        ]
        service = EmbeddingService(provider, exemplos_path, cache_path)

        service.atualizar_cache()

        with open(cache_path, encoding='utf-8') as f:
            cache_salvo = json.load(f)

        assert cache_salvo.get('format') == 2
        assert isinstance(cache_salvo['embeddings'], dict)
        assert len(cache_salvo['embeddings']) == 3

        # Cada chave deve ser o hash do texto correspondente
        for exemplo in exemplos_dados:
            h = _hash_texto(exemplo['texto'])
            assert h in cache_salvo['embeddings']

    def test_ja_tem_todos_nao_chama_provider(
        self,
        provider: MagicMock,
        exemplos_path: Path,
        cache_path: Path,
        exemplos_dados: list[dict],
    ):
        """Todos os hashes presentes nao deve chamar provider."""
        embeddings = {
            _hash_texto(exemplos_dados[0]['texto']): [0.1] * 384,
            _hash_texto(exemplos_dados[1]['texto']): [0.2] * 384,
            _hash_texto(exemplos_dados[2]['texto']): [0.3] * 384,
        }
        cache_novo = {
            'format': 2,
            'embeddings': embeddings,
        }
        with open(exemplos_path, 'w', encoding='utf-8') as f:
            json.dump(exemplos_dados, f)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_novo, f)

        provider.embed_batch.reset_mock()
        service = EmbeddingService(provider, exemplos_path, cache_path)

        service.atualizar_cache()

        provider.embed_batch.assert_not_called()
