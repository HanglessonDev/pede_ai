import csv
from pathlib import Path

from src.observabilidade.extracao_logger import HEADERS, ExtracaoLogger


def test_registra_extracao_sucesso(tmp_path: Path) -> None:
    csv_path = tmp_path / 'extracoes.csv'
    logger = ExtracaoLogger(csv_path)
    logger.registrar(
        thread_id='sessao_1',
        mensagem='quero um suco de laranja',
        itens_extraidos=[
            {
                'item_id': 'bebida_004',
                'quantidade': 1,
                'variante': None,
                'remocoes': [],
            }
        ],
        tempo_ms=45.2,
    )
    assert csv_path.exists()
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 1
    assert rows[0]['thread_id'] == 'sessao_1'
    assert rows[0]['itens_encontrados'] == '1'
    assert rows[0]['tempo_ms'] == '45.20'


def test_headers_contem_colunas_esperadas() -> None:
    assert 'timestamp' in HEADERS
    assert 'thread_id' in HEADERS
    assert 'mensagem' in HEADERS
    assert 'itens_encontrados' in HEADERS
    assert 'itens_ids' in HEADERS
    assert 'variantes_encontradas' in HEADERS
    assert 'tempo_ms' in HEADERS


def test_registra_multiplas_extracoes(tmp_path: Path) -> None:
    csv_path = tmp_path / 'extracoes.csv'
    logger = ExtracaoLogger(csv_path)
    logger.registrar(
        thread_id='sessao_1',
        mensagem='quero x-burguer e coca',
        itens_extraidos=[
            {
                'item_id': 'lanche_001',
                'quantidade': 1,
                'variante': 'simples',
                'remocoes': [],
            },
            {
                'item_id': 'bebida_001',
                'quantidade': 1,
                'variante': None,
                'remocoes': [],
            },
        ],
        tempo_ms=62.5,
    )
    logger.registrar(
        thread_id='sessao_2',
        mensagem='uma batata frita',
        itens_extraidos=[
            {
                'item_id': 'acompanhamento_001',
                'quantidade': 2,
                'variante': 'grande',
                'remocoes': ['cebola'],
            }
        ],
        tempo_ms=30.0,
    )
    with open(csv_path, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2
    assert rows[0]['itens_encontrados'] == '2'
    assert rows[0]['itens_ids'] == 'lanche_001|bebida_001'
    assert rows[0]['variantes_encontradas'] == 'simples|None'
    assert rows[1]['itens_encontrados'] == '1'
    assert rows[1]['itens_ids'] == 'acompanhamento_001'
    assert rows[1]['variantes_encontradas'] == 'grande'


def test_registra_lista_vazia_de_itens(tmp_path: Path) -> None:
    csv_path = tmp_path / 'extracoes.csv'
    logger = ExtracaoLogger(csv_path)
    logger.registrar(
        thread_id='sessao_3',
        mensagem='isso nao tem nada a ver',
        itens_extraidos=[],
        tempo_ms=10.0,
    )
    with open(csv_path, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]['itens_encontrados'] == '0'
    assert rows[0]['itens_ids'] == ''
    assert rows[0]['variantes_encontradas'] == ''


def test_cria_diretorio_pai(tmp_path: Path) -> None:
    csv_path = tmp_path / 'subdir' / 'nested' / 'extracoes.csv'
    logger = ExtracaoLogger(csv_path)
    logger.registrar(
        thread_id='sessao_1',
        mensagem='teste',
        itens_extraidos=[],
        tempo_ms=5.0,
    )
    assert csv_path.exists()


def test_tempo_ms_formatado_com_duas_casas_decimais(tmp_path: Path) -> None:
    csv_path = tmp_path / 'extracoes.csv'
    logger = ExtracaoLogger(csv_path)
    logger.registrar(
        thread_id='sessao_1',
        mensagem='teste',
        itens_extraidos=[
            {'item_id': 'item_1', 'quantidade': 1, 'variante': None, 'remocoes': []}
        ],
        tempo_ms=100.0,
    )
    with open(csv_path, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    assert rows[0]['tempo_ms'] == '100.00'
