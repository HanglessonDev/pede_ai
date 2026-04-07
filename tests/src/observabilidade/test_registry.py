"""Testes para o registry de loggers de observabilidade."""

import pytest


class TestRegistry:
    """Testes para o registry central de loggers."""

    def setup_method(self):
        """Limpa o registry antes de cada teste."""
        from src.observabilidade import registry

        registry._obs = None
        registry._clarificacao = None
        registry._extracao = None
        registry._handler = None
        registry._funil = None

    def test_get_obs_logger_sem_setup_raises(self):
        """Deve levantar RuntimeError se logger não foi configurado."""
        from src.observabilidade.registry import get_obs_logger

        with pytest.raises(RuntimeError, match='nao configurado'):
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

    def test_set_get_extracao_logger(self, tmp_path):
        """Deve permitir setar e recuperar o logger de extração."""
        from src.observabilidade.extracao_logger import ExtracaoLogger
        from src.observabilidade.registry import (
            get_extracao_logger,
            set_extracao_logger,
        )

        csv_path = tmp_path / 'ext.csv'
        logger = ExtracaoLogger(csv_path)
        set_extracao_logger(logger)
        assert get_extracao_logger() is logger

    def test_set_get_handler_logger(self, tmp_path):
        """Deve permitir setar e recuperar o logger de handler."""
        from src.observabilidade.handler_logger import HandlerLogger
        from src.observabilidade.registry import (
            get_handler_logger,
            set_handler_logger,
        )

        csv_path = tmp_path / 'hdl.csv'
        logger = HandlerLogger(csv_path)
        set_handler_logger(logger)
        assert get_handler_logger() is logger

    def test_set_get_funil_logger(self, tmp_path):
        """Deve permitir setar e recuperar o logger de funil."""
        from src.observabilidade.funil_logger import FunilLogger
        from src.observabilidade.registry import (
            get_funil_logger,
            set_funil_logger,
        )

        csv_path = tmp_path / 'fun.csv'
        logger = FunilLogger(csv_path)
        set_funil_logger(logger)
        assert get_funil_logger() is logger

    def test_set_extracao_logger_none(self):
        """Deve permitir limpar o logger de extração."""
        from src.observabilidade.registry import (
            get_extracao_logger,
            set_extracao_logger,
        )

        set_extracao_logger(None)
        assert get_extracao_logger() is None

    def test_set_handler_logger_none(self):
        """Deve permitir limpar o logger de handler."""
        from src.observabilidade.registry import (
            get_handler_logger,
            set_handler_logger,
        )

        set_handler_logger(None)
        assert get_handler_logger() is None

    def test_set_funil_logger_none(self):
        """Deve permitir limpar o logger de funil."""
        from src.observabilidade.registry import (
            get_funil_logger,
            set_funil_logger,
        )

        set_funil_logger(None)
        assert get_funil_logger() is None

    def test_set_get_pedido_logger(self, tmp_path):
        """Deve permitir configurar e obter logger de pedido."""
        from src.observabilidade.pedido_logger import PedidoLogger
        from src.observabilidade.registry import (
            get_pedido_logger,
            set_pedido_logger,
        )

        csv_path = tmp_path / 'ped.csv'
        logger = PedidoLogger(csv_path)
        set_pedido_logger(logger)
        assert get_pedido_logger() is logger

    def test_set_pedido_logger_none(self):
        """Deve permitir limpar o logger de pedido."""
        from src.observabilidade.registry import (
            get_pedido_logger,
            set_pedido_logger,
        )

        set_pedido_logger(None)
        assert get_pedido_logger() is None

    def test_set_get_negocio_logger(self, tmp_path):
        """Deve permitir configurar e obter logger de negocio."""
        from src.observabilidade.negocio_logger import NegocioLogger
        from src.observabilidade.registry import (
            get_negocio_logger,
            set_negocio_logger,
        )

        csv_path = tmp_path / 'neg.csv'
        logger = NegocioLogger(csv_path)
        set_negocio_logger(logger)
        assert get_negocio_logger() is logger

    def test_set_negocio_logger_none(self):
        """Deve permitir limpar o logger de negocio."""
        from src.observabilidade.registry import (
            get_negocio_logger,
            set_negocio_logger,
        )

        set_negocio_logger(None)
        assert get_negocio_logger() is None
