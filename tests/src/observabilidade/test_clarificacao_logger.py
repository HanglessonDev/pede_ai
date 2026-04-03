"""Testes para o logger de clarificação de variantes."""

import csv
import threading

import pytest


class TestClarificacaoLogger:
    """Testes para ClarificacaoLogger."""

    def test_cria_arquivo_csv_se_nao_existir(self, tmp_path):
        """Deve criar o arquivo CSV com headers se não existir."""
        from src.observabilidade.clarificacao_logger import ClarificacaoLogger

        csv_path = tmp_path / 'clarificacoes.csv'
        ClarificacaoLogger(csv_path)

        assert csv_path.exists()
        with open(csv_path, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            assert 'timestamp' in reader.fieldnames
            assert 'thread_id' in reader.fieldnames
            assert 'item_id' in reader.fieldnames
            assert 'nome_item' in reader.fieldnames
            assert 'campo' in reader.fieldnames
            assert 'opcoes' in reader.fieldnames
            assert 'mensagem' in reader.fieldnames
            assert 'tentativas' in reader.fieldnames
            assert 'resultado' in reader.fieldnames
            assert 'variante_escolhida' in reader.fieldnames

    def test_registra_evento_sucesso(self, tmp_path):
        """Deve registrar clarificação com sucesso."""
        from src.observabilidade.clarificacao_logger import ClarificacaoLogger

        csv_path = tmp_path / 'clarificacoes.csv'
        logger = ClarificacaoLogger(csv_path)

        logger.registrar(
            thread_id='sessao-1',
            item_id='lanche_001',
            nome_item='Hambúrguer',
            campo='variante',
            opcoes=['simples', 'duplo'],
            mensagem='duplo',
            tentativas=0,
            resultado='sucesso',
            variante_escolhida='duplo',
        )

        with open(csv_path, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]['thread_id'] == 'sessao-1'
            assert rows[0]['item_id'] == 'lanche_001'
            assert rows[0]['nome_item'] == 'Hambúrguer'
            assert rows[0]['campo'] == 'variante'
            assert rows[0]['opcoes'] == 'simples,duplo'
            assert rows[0]['mensagem'] == 'duplo'
            assert rows[0]['tentativas'] == '0'
            assert rows[0]['resultado'] == 'sucesso'
            assert rows[0]['variante_escolhida'] == 'duplo'

    def test_registra_evento_desistencia(self, tmp_path):
        """Deve registrar clarificação com desistência após tentativas."""
        from src.observabilidade.clarificacao_logger import ClarificacaoLogger

        csv_path = tmp_path / 'clarificacoes.csv'
        logger = ClarificacaoLogger(csv_path)

        logger.registrar(
            thread_id='sessao-2',
            item_id='lanche_002',
            nome_item='Coca-Cola',
            campo='variante',
            opcoes=['P', 'M', 'G'],
            mensagem='quero XL',
            tentativas=3,
            resultado='invalida_desistiu',
        )

        with open(csv_path, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]['tentativas'] == '3'
            assert rows[0]['resultado'] == 'invalida_desistiu'
            assert rows[0]['variante_escolhida'] == ''

    def test_thread_safe_append(self, tmp_path):
        """Deve ser thread-safe para múltiplos threads."""
        from src.observabilidade.clarificacao_logger import ClarificacaoLogger

        csv_path = tmp_path / 'clarificacoes.csv'
        logger = ClarificacaoLogger(csv_path)

        def registrar(i):
            logger.registrar(
                thread_id=f'thread-{i}',
                item_id=f'item_{i}',
                nome_item=f'Item {i}',
                campo='variante',
                opcoes=['a', 'b'],
                mensagem=f'msg {i}',
                tentativas=0,
                resultado='sucesso',
                variante_escolhida='a',
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

    def test_multiplos_registros_mesma_sessao(self, tmp_path):
        """Deve permitir múltiplos registros na mesma sessão."""
        from src.observabilidade.clarificacao_logger import ClarificacaoLogger

        csv_path = tmp_path / 'clarificacoes.csv'
        logger = ClarificacaoLogger(csv_path)

        logger.registrar(
            thread_id='sessao-1',
            item_id='lanche_001',
            nome_item='Hambúrguer',
            campo='variante',
            opcoes=['simples', 'duplo'],
            mensagem='duplo',
            tentativas=1,
            resultado='sucesso',
            variante_escolhida='duplo',
        )
        logger.registrar(
            thread_id='sessao-1',
            item_id='bebida_001',
            nome_item='Coca-Cola',
            campo='variante',
            opcoes=['P', 'M', 'G'],
            mensagem='M',
            tentativas=0,
            resultado='sucesso',
            variante_escolhida='M',
        )

        with open(csv_path, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 2
            assert rows[0]['item_id'] == 'lanche_001'
            assert rows[1]['item_id'] == 'bebida_001'

    def test_rejeita_caminho_invalido(self, tmp_path):
        """Deve levantar ValueError para resultado inválido."""
        from src.observabilidade.clarificacao_logger import (
            ClarificacaoLogger,
            RESULTADOS_VALIDOS,
        )

        assert 'sucesso' in RESULTADOS_VALIDOS
        assert 'invalida_reprompt' in RESULTADOS_VALIDOS
        assert 'invalida_desistiu' in RESULTADOS_VALIDOS
        assert len(RESULTADOS_VALIDOS) == 3

        csv_path = tmp_path / 'clarificacoes.csv'
        logger = ClarificacaoLogger(csv_path)

        with pytest.raises(ValueError, match=r'[Rr]esultado invalido'):
            logger.registrar(
                thread_id='sessao-1',
                item_id='lanche_001',
                nome_item='Teste',
                campo='variante',
                opcoes=['a'],
                mensagem='x',
                tentativas=0,
                resultado='invalido',
            )
