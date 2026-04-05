"""Testes para o loader de configuracao do roteador."""

import pytest

from src.config.roteador_config import (
    _RoteadorCache,
    get_roteador_config,
)


# ══════════════════════════════════════════════════════════════════════════════
# ROTEADOR CONFIG
# ══════════════════════════════════════════════════════════════════════════════


class TestRoteadorConfig:
    """Testes para RoteadorConfig dataclass."""

    def test_imutavel(self):
        """Deve ser imutavel (frozen)."""
        config = get_roteador_config()

        with pytest.raises(AttributeError):
            config.rag_forte_threshold = 0.99  # type: ignore

    def test_valores_padrao(self):
        """Deve carregar valores corretos do YAML."""
        config = get_roteador_config()

        assert config.rag_forte_threshold == 0.95
        assert config.rag_fraco_threshold == 0.50
        assert config.min_similarity == 0.55
        assert config.max_chars == 500
        assert config.top_k == 5

    def test_alta_prioridade(self):
        """Deve carregar alta_prioridade como frozenset."""
        config = get_roteador_config()

        assert isinstance(config.alta_prioridade, frozenset)
        assert 'pedir' in config.alta_prioridade
        assert 'remover' in config.alta_prioridade
        assert 'trocar' in config.alta_prioridade
        assert 'carrinho' in config.alta_prioridade
        assert 'confirmar' in config.alta_prioridade
        assert 'cancelar' in config.alta_prioridade
        assert 'saudacao' not in config.alta_prioridade

    def test_llm_config(self):
        """Deve carregar config do LLM."""
        config = get_roteador_config()

        assert config.llm_provider == 'groq'
        assert config.llm_model == 'llama-3.1-8b-instant'

    def test_embedding_config(self):
        """Deve carregar config de embedding."""
        config = get_roteador_config()

        assert config.embedding_model == 'sentence-transformers/all-MiniLM-L6-v2'
        assert 'all-MiniLM-L6-v2' in str(config.embedding_cache_path)

    def test_exemplos_path(self):
        """Deve carregar caminho dos exemplos."""
        config = get_roteador_config()

        assert 'exemplos-classificacao' in str(config.exemplos_path)


# ══════════════════════════════════════════════════════════════════════════════
# CACHE
# ══════════════════════════════════════════════════════════════════════════════


class TestCache:
    """Testes para o cache lazy."""

    def test_cache_retorna_mesma_instancia(self):
        """Chamadas multiplas devem retornar o mesmo objeto."""
        a = get_roteador_config()
        b = get_roteador_config()

        assert a is b

    def test_cache_carrega_do_yaml(self):
        """Primeira chamada deve carregar do YAML."""
        # Reset cache para testar carregamento
        _RoteadorCache._config = None

        config = get_roteador_config()
        assert config is not None
        assert config.rag_forte_threshold == 0.95
