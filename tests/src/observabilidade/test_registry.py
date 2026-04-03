"""Testes para o registry de loggers de observabilidade."""

import pytest


class TestRegistry:
    """Testes para o registry central de loggers."""

    def setup_method(self):
        """Limpa o registry antes de cada teste."""
        from src.observabilidade import registry

        registry._obs = None
        registry._clarificacao = None

    def test_get_obs_logger_sem_setup_raises(self):
        """Deve levantar RuntimeError se logger não foi configurado."""
        from src.observabilidade.registry import get_obs_logger

        with pytest.raises(RuntimeError, match='Use set_obs_logger'):
            get_obs_logger()

    def test_get_clarificacao_logger_sem_setup_retorna_none(self):
        """Deve retornar None se logger de clarificação não foi configurado."""
        from src.observabilidade.registry import get_clarificacao_logger

        assert get_clarificacao_logger() is None

    def test_set_get_obs_logger(self, tmp_path):
        """Deve permitir setar e recuperar o logger de observabilidade."""
        from src.observabilidade.logger import ObservabilidadeLogger
        from src.observabilidade.registry import get_obs_logger, set_obs_logger

        csv_path = tmp_path / 'classificacoes.csv'
        logger = ObservabilidadeLogger(csv_path)
        set_obs_logger(logger)

        assert get_obs_logger() is logger

    def test_set_get_clarificacao_logger(self, tmp_path):
        """Deve permitir setar e recuperar o logger de clarificação."""
        from src.observabilidade.clarificacao_logger import ClarificacaoLogger
        from src.observabilidade.registry import (
            get_clarificacao_logger,
            set_clarificacao_logger,
        )

        csv_path = tmp_path / 'clarificacoes.csv'
        logger = ClarificacaoLogger(csv_path)
        set_clarificacao_logger(logger)

        assert get_clarificacao_logger() is logger

    def test_set_clarificacao_logger_none(self):
        """Deve permitir limpar o logger de clarificação."""
        from src.observabilidade.registry import (
            get_clarificacao_logger,
            set_clarificacao_logger,
        )

        set_clarificacao_logger(None)
        assert get_clarificacao_logger() is None
