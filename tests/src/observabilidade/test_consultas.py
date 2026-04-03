"""Testes para consultas DuckDB."""

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
