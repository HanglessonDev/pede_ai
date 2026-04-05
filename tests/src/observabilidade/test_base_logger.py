"""Testes para BaseCsvLogger."""

import csv
from pathlib import Path

import pytest

from src.observabilidade.base_logger import BaseCsvLogger


class _TestLogger(BaseCsvLogger):
    """Logger concreto para testes."""

    @property
    def headers(self) -> list[str]:
        return ['timestamp', 'mensagem', 'valor']

    def _to_row(self, **kwargs) -> list:
        return [
            kwargs.get('timestamp', ''),
            kwargs.get('mensagem', ''),
            kwargs.get('valor', 0),
        ]


class TestBaseCsvLogger:
    """Testes para BaseCsvLogger."""

    @pytest.fixture
    def csv_path(self, tmp_path: Path) -> Path:
        return tmp_path / 'test.csv'

    @pytest.fixture
    def logger(self, csv_path: Path) -> _TestLogger:
        return _TestLogger(csv_path)

    def test_cria_diretorio_pai(self, tmp_path: Path):
        """Deve criar diretorio pai se nao existir."""
        caminho = tmp_path / 'subdir' / 'test.csv'
        _TestLogger(caminho)
        assert caminho.parent.exists()

    def test_cria_csv_com_headers(self, logger: _TestLogger):
        """Deve criar CSV com headers."""
        with open(logger.csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
        assert headers == ['timestamp', 'mensagem', 'valor']

    def test_registrar_adiciona_linha(self, logger: _TestLogger):
        """Deve adicionar linha ao CSV."""
        logger.registrar(mensagem='teste', valor=42)

        with open(logger.csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # headers
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0][1] == 'teste'
        assert rows[0][2] == '42'

    def test_registrar_multiplos(self, logger: _TestLogger):
        """Deve adicionar multiplas linhas."""
        logger.registrar(mensagem='um', valor=1)
        logger.registrar(mensagem='dois', valor=2)
        logger.registrar(mensagem='tres', valor=3)

        with open(logger.csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            rows = list(reader)

        assert len(rows) == 3

    def test_csv_path_property(self, logger: _TestLogger):
        """csv_path deve retornar Path absoluto."""
        assert isinstance(logger.csv_path, Path)
        assert logger.csv_path.is_absolute()

    def test_append_mode(self, csv_path: Path):
        """Novas chamadas de registrar devem adicionar ao final."""
        logger1 = _TestLogger(csv_path)
        logger1.registrar(mensagem='primeiro', valor=1)

        logger2 = _TestLogger(csv_path)
        logger2.registrar(mensagem='segundo', valor=2)

        with open(csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            rows = list(reader)

        assert len(rows) == 2

    def test_thread_safety(self, logger: _TestLogger):
        """Deve ser seguro para multiplas threads."""
        import threading

        def escrever(valor: int) -> None:
            logger.registrar(mensagem=f'msg-{valor}', valor=valor)

        threads = [threading.Thread(target=escrever, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        with open(logger.csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            rows = list(reader)

        assert len(rows) == 10

    def test_headers_abstrato(self, tmp_path: Path):
        """Classe sem headers deve levantar TypeError."""
        from src.observabilidade.base_logger import BaseCsvLogger

        class Incompleto(BaseCsvLogger):
            def _to_row(self, **kwargs) -> list:
                return []

        with pytest.raises(TypeError):
            Incompleto(tmp_path / 'test.csv')

    def test_to_row_abstrato(self, tmp_path: Path):
        """Classe sem _to_row deve levantar TypeError."""
        from src.observabilidade.base_logger import BaseCsvLogger

        class Incompleto(BaseCsvLogger):
            @property
            def headers(self) -> list[str]:
                return []

        with pytest.raises(TypeError):
            Incompleto(tmp_path / 'test.csv')
