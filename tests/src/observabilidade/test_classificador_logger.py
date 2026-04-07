"""Testes para ClassificadorLogger."""

import csv
import json
import threading
from pathlib import Path

import pytest

from src.observabilidade.classificador_logger import ClassificadorLogger


class TestClassificadorLogger:
    """Testes para ClassificadorLogger."""

    @pytest.fixture
    def csv_path(self, tmp_path: Path) -> Path:
        return tmp_path / 'classificadores.csv'

    @pytest.fixture
    def logger(self, csv_path: Path) -> ClassificadorLogger:
        return ClassificadorLogger(csv_path)

    def test_headers_contem_campos_obrigatorios(self, logger: ClassificadorLogger):
        """Headers devem conter campos obrigatorios."""
        expected = [
            'timestamp',
            'thread_id',
            'turn_id',
            'nivel',
            'classificador',
            'resultado',
            'intent',
            'confidence',
            'detalhes',
            'tempo_ms',
        ]
        assert logger.headers == expected

    def test_registrar_lookup_sucesso(self, logger: ClassificadorLogger):
        """Deve registrar classificacao por lookup."""
        logger.registrar(
            thread_id='sessao_1',
            turn_id='turn_001',
            classificador='lookup',
            resultado='sucesso',
            intent='saudacao',
            confidence=1.0,
            detalhes={'token_match': 'oi'},
            tempo_ms=0.5,
        )

        with open(logger.csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0][4] == 'lookup'
        assert rows[0][5] == 'sucesso'
        assert rows[0][6] == 'saudacao'
        assert rows[0][7] == '1.0'

    def test_registrar_lookup_falha(self, logger: ClassificadorLogger):
        """Deve registrar falha do lookup."""
        logger.registrar(
            thread_id='sessao_2',
            turn_id='turn_002',
            classificador='lookup',
            resultado='falha',
            intent='',
            confidence=0.0,
            detalhes={'tokens_procurados': ['quero', 'xbacon']},
            tempo_ms=0.3,
        )

        with open(logger.csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0][5] == 'falha'

    def test_registrar_rag_detalhes(self, logger: ClassificadorLogger):
        """Deve registrar detalhes do RAG."""
        detalhes = {
            'top1_texto': 'quero um x-burguer',
            'top1_score': 0.92,
            'top1_intent': 'pedido_lanche',
            'caminho': 'forte',
            'validou_llm': False,
        }
        logger.registrar(
            thread_id='sessao_3',
            turn_id='turn_003',
            classificador='rag',
            resultado='sucesso',
            intent='pedido_lanche',
            confidence=0.92,
            detalhes=detalhes,
            tempo_ms=15.0,
        )

        with open(logger.csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            rows = list(reader)

        dados = json.loads(rows[0][8])
        assert dados['top1_score'] == 0.92
        assert dados['caminho'] == 'forte'

    def test_registrar_llm_detalhes(self, logger: ClassificadorLogger):
        """Deve registrar detalhes do LLM."""
        detalhes = {
            'prompt': 'Classifique: quero um lanche',
            'resposta_bruta': 'pedido_lanche',
            'intent_extraida': 'pedido_lanche',
            'fallback_desconhecido': False,
        }
        logger.registrar(
            thread_id='sessao_4',
            turn_id='turn_004',
            classificador='llm',
            resultado='sucesso',
            intent='pedido_lanche',
            confidence=1.0,
            detalhes=detalhes,
            tempo_ms=250.0,
        )

        with open(logger.csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            rows = list(reader)

        dados = json.loads(rows[0][8])
        assert dados['resposta_bruta'] == 'pedido_lanche'

    def test_detalhes_vazio_serializa(self, logger: ClassificadorLogger):
        """Detalhes vazio deve serializar como objeto vazio."""
        logger.registrar(
            thread_id='sessao_5',
            turn_id='turn_005',
            classificador='service',
            resultado='sucesso',
            intent='pedir',
            confidence=0.8,
            detalhes={},
            tempo_ms=100.0,
        )

        with open(logger.csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            rows = list(reader)

        assert rows[0][8] == '{}'

    def test_nivel_padrao_info(self, logger: ClassificadorLogger):
        """Nivel padrao deve ser INFO."""
        assert logger.nivel == 'INFO'

    def test_filtro_nivel(self, csv_path: Path):
        """Nivel inferior nao deve loggar."""
        logger = ClassificadorLogger(csv_path, nivel='INFO')
        logger.registrar(
            thread_id='sessao_6',
            turn_id='turn_006',
            classificador='debug',
            resultado='debug',
            intent='',
            confidence=0.0,
            detalhes={},
            tempo_ms=0.0,
            nivel='DEBUG',
        )

        with open(logger.csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            rows = list(reader)

        assert len(rows) == 0

    def test_thread_safe(self, logger: ClassificadorLogger):
        """Deve ser thread-safe."""

        def registrar(valor: int) -> None:
            logger.registrar(
                thread_id='sessao_multi',
                turn_id=f'turn_{valor:03d}',
                classificador='lookup',
                resultado='sucesso',
                intent='pedir',
                confidence=1.0,
                detalhes={},
                tempo_ms=0.5,
            )

        threads = [threading.Thread(target=registrar, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        with open(logger.csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            rows = list(reader)

        assert len(rows) == 10
