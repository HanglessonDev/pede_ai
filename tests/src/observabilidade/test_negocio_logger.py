"""Testes para NegocioLogger."""

import csv
from pathlib import Path

import pytest

from src.observabilidade.negocio_logger import NegocioLogger


class TestNegocioLogger:
    """Testes para NegocioLogger."""

    @pytest.fixture
    def csv_path(self, tmp_path: Path) -> Path:
        return tmp_path / 'negocio.csv'

    @pytest.fixture
    def logger(self, csv_path: Path) -> NegocioLogger:
        return NegocioLogger(csv_path)

    def test_headers_contem_campos_obrigatorios(self, logger: NegocioLogger):
        """Headers devem conter campos obrigatorios.

        Versao simplificada: sem campo 'nivel' (nao necessario para metricas).
        """
        expected = [
            'timestamp',
            'thread_id',
            'turn_id',
            'evento',
            'carrinho_size',
            'preco_total_centavos',
            'intent',
            'resposta',
            'tentativas_clarificacao',
        ]
        assert logger.headers == expected

    def test_registrar_confirmacao(self, logger: NegocioLogger):
        """Deve registrar evento de confirmacao."""
        logger.registrar(
            thread_id='sessao_1',
            turn_id='turn_001',
            evento='confirmar',
            carrinho_size=2,
            preco_total_centavos=3500,
            intent='confirmar',
            resposta='Pedido confirmado! Total: R$ 35.00',
            tentativas_clarificacao=0,
        )

        with open(logger.csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0][3] == 'confirmar'  # evento (index 3 sem nivel)
        assert rows[0][4] == '2'  # carrinho_size
        assert rows[0][5] == '3500'  # preco_total_centavos

    def test_registrar_cancelamento(self, logger: NegocioLogger):
        """Deve registrar evento de cancelamento."""
        logger.registrar(
            thread_id='sessao_2',
            turn_id='turn_002',
            evento='cancelar',
            carrinho_size=1,
            preco_total_centavos=1500,
            intent='cancelar',
            resposta='Pedido cancelado. Total descartado: R$ 15.00',
            tentativas_clarificacao=2,
        )

        with open(logger.csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0][3] == 'cancelar'  # evento
        assert rows[0][8] == '2'  # tentativas_clarificacao

    def test_registrar_saudacao(self, logger: NegocioLogger):
        """Deve registrar evento de saudacao."""
        logger.registrar(
            thread_id='sessao_3',
            turn_id='turn_003',
            evento='saudacao',
            carrinho_size=0,
            preco_total_centavos=0,
            intent='saudacao',
            resposta='Bem-vindo!',
            tentativas_clarificacao=0,
        )

        with open(logger.csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0][3] == 'saudacao'  # evento

    def test_registrar_desconhecido(self, logger: NegocioLogger):
        """Deve registrar evento desconhecido."""
        logger.registrar(
            thread_id='sessao_4',
            turn_id='turn_004',
            evento='desconhecido',
            carrinho_size=0,
            preco_total_centavos=0,
            intent='desconhecido',
            resposta='Nao entendi. Pode reformular?',
            tentativas_clarificacao=0,
        )

        with open(logger.csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0][3] == 'desconhecido'  # evento

    def test_registrar_remocao(self, logger: NegocioLogger):
        """Deve registrar evento de remocao."""
        logger.registrar(
            thread_id='sessao_5',
            turn_id='turn_005',
            evento='remover',
            carrinho_size=1,
            preco_total_centavos=2000,
            intent='remover',
            resposta='Itens removidos!',
            tentativas_clarificacao=0,
        )

        with open(logger.csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0][3] == 'remover'  # evento
        assert rows[0][4] == '1'  # carrinho_size

    def test_registrar_troca(self, logger: NegocioLogger):
        """Deve registrar evento de troca."""
        logger.registrar(
            thread_id='sessao_6',
            turn_id='turn_006',
            evento='trocar',
            carrinho_size=2,
            preco_total_centavos=3000,
            intent='modificar_pedido',
            resposta='Pedido atualizado',
            tentativas_clarificacao=0,
        )

        with open(logger.csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0][3] == 'trocar'  # evento

    def test_registrar_carrinho(self, logger: NegocioLogger):
        """Deve registrar evento de consulta ao carrinho."""
        logger.registrar(
            thread_id='sessao_7',
            turn_id='turn_007',
            evento='carrinho',
            carrinho_size=3,
            preco_total_centavos=5000,
            intent='ver_carrinho',
            resposta='Seu pedido: ...',
            tentativas_clarificacao=0,
        )

        with open(logger.csv_path, encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0][3] == 'carrinho'  # evento

    def test_nivel_padrao_info(self, logger: NegocioLogger):
        """Nivel padrao deve ser INFO."""
        assert logger.nivel == 'INFO'

    def test_thread_safe(self, logger: NegocioLogger):
        """Deve ser thread-safe."""
        import threading

        def registrar(valor: int) -> None:
            logger.registrar(
                thread_id='sessao_multi',
                turn_id=f'turn_{valor:03d}',
                evento='confirmar',
                carrinho_size=valor,
                preco_total_centavos=valor * 100,
                intent='confirmar',
                resposta='ok',
                tentativas_clarificacao=0,
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
