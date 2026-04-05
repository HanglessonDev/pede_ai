"""Testes para consultas DuckDB."""

import csv

from unittest.mock import patch, MagicMock


class TestConsultasBaixaConfianca:
    """Testes para consultas de baixa confiança."""

    def test_baixa_confianca_retorna_llm_primeiro(self):
        """Deve retornar casos de LLM ordenados por confidence."""
        from src.observabilidade.consultas import baixa_confianca

        mock_csv = 'mock.csv'
        with patch('src.observabilidade.consultas.duckdb') as mock_duckdb:
            mock_conn = MagicMock()
            mock_duckdb.connect.return_value = mock_conn
            mock_conn.execute.return_value.fetchall.return_value = [
                ('qual o total', 'duvida', 0.45, 'llm_rag'),
            ]
            mock_conn.execute.return_value.description = [
                ('mensagem',),
                ('intent',),
                ('confidence',),
                ('caminho',),
            ]

            resultados = baixa_confianca(mock_csv, limit=10)

            assert len(resultados) == 1
            assert resultados[0]['mensagem'] == 'qual o total'
            assert resultados[0]['confidence'] == 0.45


class TestDistribuicaoCaminhos:
    """Testes para distribuição de caminhos."""

    def test_distribuicao_retorna_contagem(self):
        """Deve retornar contagem por caminho."""
        from src.observabilidade.consultas import distribuicao_caminhos

        mock_csv = 'mock.csv'
        with patch('src.observabilidade.consultas.duckdb') as mock_duckdb:
            mock_conn = MagicMock()
            mock_duckdb.connect.return_value = mock_conn
            mock_conn.execute.return_value.fetchall.return_value = [
                ('lookup', 100),
                ('rag_forte', 50),
                ('llm_rag', 10),
            ]
            mock_conn.execute.return_value.description = [('caminho',), ('total',)]

            resultados = distribuicao_caminhos(mock_csv)

            assert len(resultados) == 3
            assert resultados[0]['caminho'] == 'lookup'
            assert resultados[0]['total'] == 100


class TestNovasConsultas:
    """Testes para novas consultas DuckDB."""

    def test_extracoes_sem_itens(self, tmp_path) -> None:
        csv_path = tmp_path / 'extracoes.csv'
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    'timestamp',
                    'thread_id',
                    'mensagem',
                    'itens_encontrados',
                    'itens_ids',
                    'variantes_encontradas',
                    'tempo_ms',
                ]
            )
            writer.writerow(
                ['2026-01-01', 's1', 'quero algo estranho', '0', '', '', '12.50']
            )
            writer.writerow(
                [
                    '2026-01-02',
                    's2',
                    'quero hamburguer',
                    '1',
                    'lanche_001',
                    'simples',
                    '8.30',
                ]
            )

        from src.observabilidade.consultas import extracoes_sem_itens

        resultados = extracoes_sem_itens(str(csv_path))
        assert len(resultados) == 1
        assert resultados[0]['mensagem'] == 'quero algo estranho'

    def test_handlers_com_erro(self, tmp_path) -> None:
        csv_path = tmp_path / 'handlers.csv'
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    'timestamp',
                    'thread_id',
                    'handler',
                    'intent',
                    'input_resumo',
                    'output_resumo',
                    'tempo_ms',
                    'erro',
                ]
            )
            writer.writerow(
                [
                    '2026-01-01',
                    's1',
                    'handler_pedir',
                    'pedir',
                    '{}',
                    '{}',
                    '5.0',
                    'KeyError',
                ]
            )
            writer.writerow(
                ['2026-01-02', 's2', 'handler_pedir', 'pedir', '{}', '{}', '3.0', '']
            )

        from src.observabilidade.consultas import handlers_com_erro

        resultados = handlers_com_erro(str(csv_path))
        assert len(resultados) == 1
        assert resultados[0]['erro'] == 'KeyError'

    def test_tempo_medio_handlers(self, tmp_path) -> None:
        csv_path = tmp_path / 'handlers.csv'
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    'timestamp',
                    'thread_id',
                    'handler',
                    'intent',
                    'input_resumo',
                    'output_resumo',
                    'tempo_ms',
                    'erro',
                ]
            )
            writer.writerow(
                ['2026-01-01', 's1', 'handler_pedir', 'pedir', '{}', '{}', '10.0', '']
            )
            writer.writerow(
                ['2026-01-02', 's2', 'handler_pedir', 'pedir', '{}', '{}', '20.0', '']
            )

        from src.observabilidade.consultas import tempo_medio_handlers

        resultados = tempo_medio_handlers(str(csv_path))
        assert len(resultados) == 1
        assert resultados[0]['handler'] == 'handler_pedir'
        assert float(resultados[0]['tempo_medio_ms']) == 15.0

    def test_funil_com_abandono_sem_filtro(self, tmp_path) -> None:
        csv_path = tmp_path / 'funil.csv'
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(
                ['timestamp', 'thread_id', 'etapa_atual', 'intent', 'carrinho_size']
            )
            writer.writerow(['2026-01-01', 's1', 'revisao', 'pedir', '2'])
            writer.writerow(['2026-01-02', 's2', 'pagamento', 'pedir', '1'])

        from src.observabilidade.consultas import funil_com_abandono

        resultados = funil_com_abandono(str(csv_path))
        assert len(resultados) == 2
        assert resultados[0]['thread_id'] == 's2'

    def test_funil_com_abandono_com_thread_id(self, tmp_path) -> None:
        csv_path = tmp_path / 'funil.csv'
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(
                ['timestamp', 'thread_id', 'etapa_atual', 'intent', 'carrinho_size']
            )
            writer.writerow(['2026-01-01', 's1', 'revisao', 'pedir', '2'])
            writer.writerow(['2026-01-02', 's2', 'pagamento', 'pedir', '1'])

        from src.observabilidade.consultas import funil_com_abandono

        resultados = funil_com_abandono(str(csv_path), thread_id='s1')
        assert len(resultados) == 1
        assert resultados[0]['thread_id'] == 's1'
