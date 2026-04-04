"""Testes para HandlerLogger."""

import csv
from pathlib import Path

from src.observabilidade.handler_logger import HandlerLogger


def test_registra_execucao_handler(tmp_path: Path) -> None:
    csv_path = tmp_path / 'handlers.csv'
    logger = HandlerLogger(csv_path)
    logger.registrar(
        thread_id='sessao_1',
        handler='handler_pedir',
        intent='pedir',
        input_dados={'itens_extraidos': [{'item_id': 'bebida_004'}]},
        output_dados={'carrinho': [{'item_id': 'bebida_004', 'preco': 500}]},
        tempo_ms=12.5,
        erro=None,
    )
    assert csv_path.exists()
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 1
    assert rows[0]['handler'] == 'handler_pedir'
    assert rows[0]['erro'] == ''


def test_registra_com_erro(tmp_path: Path) -> None:
    csv_path = tmp_path / 'handlers.csv'
    logger = HandlerLogger(csv_path)
    logger.registrar(
        thread_id='sessao_2',
        handler='handler_trocar',
        intent='trocar',
        input_dados={},
        output_dados={},
        tempo_ms=5.0,
        erro='KeyError: item_id',
    )
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert rows[0]['erro'] == 'KeyError: item_id'


def test_input_output_truncados(tmp_path: Path) -> None:
    csv_path = tmp_path / 'handlers.csv'
    logger = HandlerLogger(csv_path)
    dado_grande = 'x' * 300
    logger.registrar(
        thread_id='sessao_3',
        handler='handler_pedir',
        intent='pedir',
        input_dados={'grande': dado_grande},
        output_dados={},
        tempo_ms=1.0,
    )
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows[0]['input_resumo']) <= 200
