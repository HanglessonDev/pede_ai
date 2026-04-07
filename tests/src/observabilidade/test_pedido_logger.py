"""Testes para PedidoLogger."""

import csv
from pathlib import Path

import pytest

from src.observabilidade.pedido_logger import PedidoLogger


class TestPedidoLogger:
    """Testes para PedidoLogger."""

    @pytest.fixture
    def csv_path(self, tmp_path: Path) -> Path:
        return tmp_path / 'pedidos.csv'

    @pytest.fixture
    def logger(self, csv_path: Path) -> PedidoLogger:
        return PedidoLogger(csv_path)

    def test_headers_contem_campos_obrigatorios(self, logger: PedidoLogger):
        """Headers devem conter campos obrigatorios."""
        expected = [
            'timestamp',
            'thread_id',
            'turn_id',
            'nivel',
            'itens_adicionados',
            'itens_fila',
            'total_itens',
            'preco_total_centavos',
            'modo_saida',
            'resposta',
        ]
        assert logger.headers == expected

    def test_registrar_pedido_simples(self, logger: PedidoLogger):
        """Deve registrar pedido com itens adicionados."""
        logger.registrar(
            thread_id='sessao_1',
            turn_id='turn_001',
            itens_adicionados=[
                {'item_id': 'lanche_001', 'nome': 'Hamburguer', 'quantidade': 1, 'variante': 'simples', 'preco_centavos': 1500},
            ],
            itens_fila=[],
            total_itens=1,
            preco_total_centavos=1500,
            modo_saida='coletando',
            resposta='Adicionado!',
        )

        with open(logger.csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # headers
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0][6] == '1'  # total_itens
        assert rows[0][7] == '1500'  # preco_total_centavos
        assert rows[0][8] == 'coletando'  # modo_saida

    def test_registrar_com_itens_fila(self, logger: PedidoLogger):
        """Deve registrar itens na fila de clarificacao."""
        logger.registrar(
            thread_id='sessao_2',
            turn_id='turn_002',
            itens_adicionados=[],
            itens_fila=[
                {'item_id': 'lanche_001', 'nome': 'Hamburguer', 'campo': 'variante', 'opcoes': ['simples', 'duplo']},
            ],
            total_itens=0,
            preco_total_centavos=0,
            modo_saida='clarificando',
            resposta='Hamburguer: qual opcao? simples, duplo',
        )

        with open(logger.csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0][6] == '0'  # total_itens
        assert rows[0][8] == 'clarificando'
        assert 'Hamburguer' in rows[0][9]  # resposta

    def test_registrar_multiplos_itens(self, logger: PedidoLogger):
        """Deve registrar multiplos itens."""
        logger.registrar(
            thread_id='sessao_3',
            turn_id='turn_003',
            itens_adicionados=[
                {'item_id': 'lanche_001', 'nome': 'Hamburguer', 'quantidade': 2, 'variante': None, 'preco_centavos': 3000},
                {'item_id': 'bebida_001', 'nome': 'Coca-Cola', 'quantidade': 1, 'variante': None, 'preco_centavos': 500},
            ],
            itens_fila=[],
            total_itens=2,
            preco_total_centavos=3500,
            modo_saida='coletando',
            resposta='Pedido atualizado',
        )

        with open(logger.csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0][6] == '2'
        assert rows[0][7] == '3500'

    def test_itens_adicionados_serializa_json(self, logger: PedidoLogger):
        """itens_adicionados deve ser serializado como JSON."""
        import json

        itens = [
            {'item_id': 'lanche_001', 'nome': 'Hamburguer', 'quantidade': 1, 'variante': 'simples', 'preco_centavos': 1500},
        ]
        logger.registrar(
            thread_id='sessao_4',
            turn_id='turn_004',
            itens_adicionados=itens,
            itens_fila=[],
            total_itens=1,
            preco_total_centavos=1500,
            modo_saida='coletando',
            resposta='ok',
        )

        with open(logger.csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            rows = list(reader)

        dados = json.loads(rows[0][4])
        assert len(dados) == 1
        assert dados[0]['item_id'] == 'lanche_001'

    def test_nivel_padrao_info(self, logger: PedidoLogger):
        """Nivel padrao deve ser INFO."""
        assert logger.nivel == 'INFO'

    def test_thread_safe(self, logger: PedidoLogger):
        """Deve ser thread-safe."""
        import threading

        def registrar(valor: int) -> None:
            logger.registrar(
                thread_id='sessao_multi',
                turn_id=f'turn_{valor:03d}',
                itens_adicionados=[],
                itens_fila=[],
                total_itens=valor,
                preco_total_centavos=valor * 100,
                modo_saida='coletando',
                resposta='ok',
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
