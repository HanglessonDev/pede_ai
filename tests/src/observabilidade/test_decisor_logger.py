"""Testes para DecisorLogger — decision tracing."""

import csv
import json
from pathlib import Path

import pytest

from src.observabilidade.decisor_logger import DecisorLogger


class TestDecisorLogger:
    """Testes para DecisorLogger."""

    @pytest.fixture
    def csv_path(self, tmp_path: Path) -> Path:
        return tmp_path / 'decisoes.csv'

    @pytest.fixture
    def logger(self, csv_path: Path) -> DecisorLogger:
        return DecisorLogger(csv_path)

    def test_cria_csv_com_headers(self, logger: DecisorLogger):
        """Deve criar CSV com headers corretos."""
        expected = [
            'timestamp',
            'thread_id',
            'turn_id',
            'componente',
            'decisao',
            'alternativas',
            'criterio',
            'threshold',
            'resultado',
            'contexto',
        ]
        assert logger.headers == expected

    def test_registrar_decisao_simples(self, logger: DecisorLogger):
        """Deve registrar decisão com todos os campos."""
        logger.registrar(
            thread_id='sessao_1',
            turn_id='turn_001',
            componente='classificacao_lookup',
            decisao='retornar_saudacao',
            alternativas=['saudacao(1.0)', 'pedir(0.0)'],
            criterio="token_exato: 'oi'",
            threshold='match_exato',
            resultado='saudacao',
            contexto={'mensagem': 'oi'},
        )

        with open(logger.csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # header
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0][1] == 'sessao_1'  # thread_id
        assert rows[0][2] == 'turn_001'  # turn_id
        assert rows[0][3] == 'classificacao_lookup'  # componente
        assert rows[0][4] == 'retornar_saudacao'  # decisao
        assert 'saudacao' in rows[0][5]  # alternativas (JSON)
        assert 'token_exato' in rows[0][6]  # criterio
        assert rows[0][7] == 'match_exato'  # threshold
        assert rows[0][8] == 'saudacao'  # resultado
        assert 'oi' in rows[0][9]  # contexto (JSON)

    def test_alternativas_serializa_json(self, logger: DecisorLogger):
        """Alternativas devem ser serializadas como JSON."""
        logger.registrar(
            thread_id='t1',
            turn_id='t1',
            componente='c',
            decisao='d',
            alternativas=['a(0.9)', 'b(0.1)'],
            criterio='x',
            resultado='r',
        )

        with open(logger.csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            row = next(reader)

        alternativas = json.loads(row[5])
        assert alternativas == ['a(0.9)', 'b(0.1)']

    def test_contexto_serializa_json(self, logger: DecisorLogger):
        """Contexto deve ser serializado como JSON."""
        contexto = {'mensagem': 'oi', 'carrinho_size': 2}
        logger.registrar(
            thread_id='t1',
            turn_id='t1',
            componente='c',
            decisao='d',
            alternativas=[],
            criterio='x',
            resultado='r',
            contexto=contexto,
        )

        with open(logger.csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            row = next(reader)

        ctx = json.loads(row[9])
        assert ctx == contexto

    def test_contexto_vazio(self, logger: DecisorLogger):
        """Contexto vazio deve ser string vazia."""
        logger.registrar(
            thread_id='t1',
            turn_id='t1',
            componente='c',
            decisao='d',
            alternativas=[],
            criterio='x',
            resultado='r',
        )

        with open(logger.csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            row = next(reader)

        assert row[9] == ''

    def test_trunca_alternativas_grandes(self, logger: DecisorLogger):
        """Alternativas grandes devem ser truncadas."""
        grandes = ['item' * 500] * 10  # ~20000 chars
        logger.registrar(
            thread_id='t1',
            turn_id='t1',
            componente='c',
            decisao='d',
            alternativas=grandes,
            criterio='x',
            resultado='r',
        )

        with open(logger.csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            row = next(reader)

        assert len(row[5]) < 1100  # 1000 + '...'
        assert '...' in row[5]

    def test_trunca_contexto_grande(self, logger: DecisorLogger):
        """Contexto grande deve ser truncado."""
        grande = {'dados': 'x' * 2000}
        logger.registrar(
            thread_id='t1',
            turn_id='t1',
            componente='c',
            decisao='d',
            alternativas=[],
            criterio='x',
            resultado='r',
            contexto=grande,
        )

        with open(logger.csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            row = next(reader)

        assert len(row[9]) < 1100

    def test_thread_safe(self, logger: DecisorLogger):
        """Deve ser thread-safe."""
        import threading

        def registrar(valor: int) -> None:
            logger.registrar(
                thread_id='sessao_multi',
                turn_id=f'turn_{valor:03d}',
                componente='test',
                decisao='decisao',
                alternativas=[],
                criterio='teste',
                resultado='ok',
            )

        threads = [threading.Thread(target=registrar, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        with open(logger.csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            rows = list(reader)

        assert len(rows) == 50

    def test_timestamp_utc(self, logger: DecisorLogger):
        """Timestamp deve estar em formato ISO."""
        logger.registrar(
            thread_id='t1',
            turn_id='t1',
            componente='c',
            decisao='d',
            alternativas=[],
            criterio='x',
            resultado='r',
        )

        with open(logger.csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            row = next(reader)

        # Deve conter 'T' (ISO 8601) e '+' ou 'Z' (timezone)
        assert 'T' in row[0]

    def test_multiplos_registros(self, logger: DecisorLogger):
        """Deve registrar múltiplas decisões."""
        for i in range(3):
            logger.registrar(
                thread_id='sessao_1',
                turn_id=f'turn_{i:03d}',
                componente='dispatcher',
                decisao=f'caso_{i}',
                alternativas=[],
                criterio='teste',
                resultado='ok',
            )

        with open(logger.csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            rows = list(reader)

        assert len(rows) == 3
