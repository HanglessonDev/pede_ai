"""Testes para o logger de observabilidade."""

import csv
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


class TestObservabilidadeLogger:
    """Testes para ObservabilidadeLogger."""

    def test_cria_arquivo_csv_se_nao_existir(self, tmp_path):
        """Deve criar o arquivo CSV com headers se não existir."""
        from src.observabilidade.logger import ObservabilidadeLogger

        csv_path = tmp_path / 'test.csv'
        logger = ObservabilidadeLogger(csv_path)

        assert csv_path.exists()
        with open(csv_path, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            assert 'timestamp' in reader.fieldnames
            assert 'thread_id' in reader.fieldnames
            assert 'mensagem' in reader.fieldnames
            assert 'mensagem_norm' in reader.fieldnames
            assert 'intent' in reader.fieldnames
            assert 'confidence' in reader.fieldnames
            assert 'caminho' in reader.fieldnames
            assert 'top1_texto' in reader.fieldnames
            assert 'top1_intencao' in reader.fieldnames

    def test_registra_evento_no_csv(self, tmp_path):
        """Deve registrar um evento no CSV."""
        from src.observabilidade.logger import ObservabilidadeLogger

        csv_path = tmp_path / 'test.csv'
        logger = ObservabilidadeLogger(csv_path)

        logger.registrar(
            thread_id='thread-123',
            mensagem='quero um xbacon',
            mensagem_norm='quero um xbacon',
            intent='pedir',
            confidence=0.95,
            caminho='rag_forte',
            top1_texto='quero um xbacon',
            top1_intencao='pedir',
        )

        with open(csv_path, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]['thread_id'] == 'thread-123'
            assert rows[0]['intent'] == 'pedir'
            assert rows[0]['confidence'] == '0.95'
            assert rows[0]['caminho'] == 'rag_forte'

    def test_thread_safe_append(self, tmp_path):
        """Deve ser thread-safe para múltiplos threads."""
        from src.observabilidade.logger import ObservabilidadeLogger

        csv_path = tmp_path / 'test.csv'
        logger = ObservabilidadeLogger(csv_path)

        def registrar(i):
            logger.registrar(
                thread_id=f'thread-{i}',
                mensagem=f'mensagem {i}',
                mensagem_norm=f'mensagem {i}',
                intent='pedir',
                confidence=0.9,
                caminho='lookup',
                top1_texto=f'exemplo {i}',
                top1_intencao='pedir',
            )

        threads = [threading.Thread(target=registrar, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        with open(csv_path, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 10


class TestCaminhosValidos:
    """Testes para validar caminhos possíveis."""

    def test_caminhos_validos(self):
        """Deve ter os caminhos esperados."""
        from src.observabilidade.logger import CAMINHOS_VALIDOS

        assert 'lookup' in CAMINHOS_VALIDOS
        assert 'rag_forte' in CAMINHOS_VALIDOS
        assert 'llm_rag' in CAMINHOS_VALIDOS
        assert 'llm_fixo' in CAMINHOS_VALIDOS
        assert 'desconhecido' in CAMINHOS_VALIDOS
        assert len(CAMINHOS_VALIDOS) == 5
