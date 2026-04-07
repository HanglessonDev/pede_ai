import csv
from pathlib import Path

from src.observabilidade.funil_logger import FunilLogger, HEADERS


def test_registra_transicao_funil(tmp_path: Path) -> None:
    csv_path = tmp_path / 'funil.csv'
    logger = FunilLogger(csv_path)
    logger.registrar(
        thread_id='sessao_1',
        modo_anterior='ocioso',
        modo_atual='saudacao',
        intent='saudacao',
    )
    assert csv_path.exists()
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 1
    assert rows[0]['modo_anterior'] == 'ocioso'
    assert rows[0]['modo_atual'] == 'saudacao'


def test_registra_transicao_com_carrinho(tmp_path: Path) -> None:
    csv_path = tmp_path / 'funil.csv'
    logger = FunilLogger(csv_path)
    logger.registrar(
        thread_id='sessao_2',
        modo_anterior='coletando',
        modo_atual='roteado',
        intent='pedir',
        carrinho_size=2,
    )
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert rows[0]['carrinho_size'] == '2'


def test_cria_csv_com_headers(tmp_path: Path) -> None:
    csv_path = tmp_path / 'funil.csv'
    FunilLogger(csv_path)
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)
    assert headers == HEADERS
