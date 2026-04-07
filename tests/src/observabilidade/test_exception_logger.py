"""Testes para ExceptionLogger."""

import json
from pathlib import Path

import pytest

from src.observabilidade.exception_logger import ExceptionLogger


class TestExceptionLogger:
    """Testes para ExceptionLogger."""

    @pytest.fixture
    def jsonl_path(self, tmp_path: Path) -> Path:
        return tmp_path / 'erros.jsonl'

    @pytest.fixture
    def logger(self, jsonl_path: Path) -> ExceptionLogger:
        return ExceptionLogger(jsonl_path)

    def test_registra_excecao(self, logger: ExceptionLogger):
        """Deve registrar excecao com stack trace."""
        try:
            raise ValueError('teste de erro')
        except ValueError as e:
            logger.registrar(
                thread_id='sessao_1',
                turn_id='turn_001',
                componente='node_handler_pedir',
                exception=e,
                estado={'mensagem_atual': 'quero x-burguer'},
            )

        with open(logger.jsonl_path, encoding='utf-8') as f:
            lines = f.readlines()

        assert len(lines) == 1
        dados = json.loads(lines[0])
        assert dados['componente'] == 'node_handler_pedir'
        assert dados['exception_type'] == 'ValueError'
        assert dados['exception_message'] == 'teste de erro'
        assert 'Traceback' in dados['traceback']
        assert dados['estado']['mensagem_atual'] == 'quero x-burguer'

    def test_registra_sem_estado(self, logger: ExceptionLogger):
        """Deve registrar excecao mesmo sem estado."""
        try:
            raise KeyError('chave faltando')
        except KeyError as e:
            logger.registrar(
                thread_id='sessao_2',
                turn_id='turn_002',
                componente='extrator',
                exception=e,
            )

        with open(logger.jsonl_path, encoding='utf-8') as f:
            lines = f.readlines()

        assert len(lines) == 1
        dados = json.loads(lines[0])
        assert dados['estado'] == {}

    def test_thread_safe(self, logger: ExceptionLogger):
        """Deve ser thread-safe."""
        import threading

        def registrar(valor: int) -> None:
            try:
                raise ValueError(f'erro-{valor}')
            except ValueError as e:
                logger.registrar(
                    thread_id='sessao_multi',
                    turn_id=f'turn_{valor:03d}',
                    componente='test',
                    exception=e,
                )

        threads = [threading.Thread(target=registrar, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        with open(logger.jsonl_path, encoding='utf-8') as f:
            lines = f.readlines()

        assert len(lines) == 10
