"""Testes para consultas DuckDB."""

import csv
from pathlib import Path

import pytest


@pytest.fixture
def mock_csv(tmp_path: Path) -> Path:
    """CSV mock com dados de classificacao."""
    path = tmp_path / 'classificacoes.csv'
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                'timestamp',
                'thread_id',
                'mensagem',
                'mensagem_norm',
                'intent',
                'confidence',
                'caminho',
                'top1_texto',
                'top1_intencao',
            ]
        )
        writer.writerow(
            [
                '2024-01-01T00:00:00',
                't1',
                'qual o total',
                'qual total',
                'duvida',
                0.45,
                'llm_rag',
                '',
                '',
            ]
        )
        writer.writerow(
            [
                '2024-01-01T00:01:00',
                't2',
                'oi',
                'oi',
                'saudacao',
                0.99,
                'lookup',
                'oi',
                'saudacao',
            ]
        )
        writer.writerow(
            [
                '2024-01-01T00:02:00',
                't3',
                'quero lanche',
                'querer lanche',
                'pedir',
                0.30,
                'llm_fixo',
                '',
                '',
            ]
        )
    return path


@pytest.fixture
def mock_csv_extracao(tmp_path: Path) -> Path:
    """CSV mock com dados de extracao."""
    path = tmp_path / 'extracoes.csv'
    with open(path, 'w', newline='', encoding='utf-8') as f:
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
            ['2024-01-01T00:00:00', 't1', 'quero pizza', 0, '', '', '15.50']
        )
        writer.writerow(
            ['2024-01-01T00:01:00', 't2', 'xbacon', 1, 'lanche_003', 'None', '12.30']
        )
    return path


@pytest.fixture
def mock_csv_funil(tmp_path: Path) -> Path:
    """CSV mock com dados de funil."""
    path = tmp_path / 'funil.csv'
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                'timestamp',
                'thread_id',
                'etapa_anterior',
                'etapa_atual',
                'intent',
                'carrinho_size',
            ]
        )
        writer.writerow(
            ['2024-01-01T00:00:00', 't1', 'inicio', 'roteado', 'saudacao', 0]
        )
        writer.writerow(
            ['2024-01-01T00:01:00', 't1', 'saudacao', 'roteado', 'pedir', 0]
        )
        writer.writerow(['2024-01-01T00:02:00', 't2', 'inicio', 'roteado', 'pedir', 0])
    return path


@pytest.fixture
def mock_csv_handler(tmp_path: Path) -> Path:
    """CSV mock com dados de handler."""
    path = tmp_path / 'handlers.csv'
    with open(path, 'w', newline='', encoding='utf-8') as f:
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
                '2024-01-01T00:00:00',
                't1',
                'handler_pedir',
                'pedir',
                '{}',
                '{}',
                '5.50',
                '',
            ]
        )
        writer.writerow(
            [
                '2024-01-01T00:01:00',
                't2',
                'handler_trocar',
                'trocar',
                '{}',
                '{}',
                '8.20',
                'variante invalida',
            ]
        )
    return path


class TestConsultasBaixaConfianca:
    """Testes para consultas de baixa confianca."""

    def test_baixa_confianca_retorna_llm_primeiro(self, mock_csv: Path):
        """Deve retornar casos de LLM ordenados por confidence."""
        from src.observabilidade.consultas import baixa_confianca

        resultados = baixa_confianca(str(mock_csv), limit=10)

        assert len(resultados) == 2
        assert resultados[0]['confidence'] <= resultados[1]['confidence']
        assert resultados[0]['caminho'] in ('llm_rag', 'llm_fixo')

    def test_baixa_confianca_limit(self, mock_csv: Path):
        """Deve respeitar limite."""
        from src.observabilidade.consultas import baixa_confianca

        resultados = baixa_confianca(str(mock_csv), limit=1)
        assert len(resultados) == 1


class TestDistribuicaoCaminhos:
    """Testes para distribuicao de caminhos."""

    def test_distribuicao_retorna_contagem(self, mock_csv: Path):
        """Deve retornar contagem por caminho."""
        from src.observabilidade.consultas import distribuicao_caminhos

        resultados = distribuicao_caminhos(str(mock_csv))

        caminhos = {r['caminho']: r['total'] for r in resultados}
        assert caminhos.get('llm_rag', 0) == 1
        assert caminhos.get('lookup', 0) == 1
        assert caminhos.get('llm_fixo', 0) == 1


class TestExtracoesSemItens:
    """Testes para extracoes sem itens."""

    def test_retorna_mensagens_sem_itens(self, mock_csv_extracao: Path):
        """Deve retornar mensagens onde itens_encontrados = 0."""
        from src.observabilidade.consultas import extracoes_sem_itens

        resultados = extracoes_sem_itens(str(mock_csv_extracao))
        assert len(resultados) == 1
        assert resultados[0]['mensagem'] == 'quero pizza'


class TestFunilComAbandono:
    """Testes para funil com abandono."""

    def test_sem_filtro_retorna_todos(self, mock_csv_funil: Path):
        """Sem thread_id deve retornar todos."""
        from src.observabilidade.consultas import funil_com_abandono

        resultados = funil_com_abandono(str(mock_csv_funil))
        assert len(resultados) == 3

    def test_com_thread_id_filtra(self, mock_csv_funil: Path):
        """Com thread_id deve filtrar."""
        from src.observabilidade.consultas import funil_com_abandono

        resultados = funil_com_abandono(str(mock_csv_funil), thread_id='t1')
        assert len(resultados) == 2
        assert all(r['thread_id'] == 't1' for r in resultados)


class TestHandlersComErro:
    """Testes para handlers com erro."""

    def test_retorna_handlers_com_erro(self, mock_csv_handler: Path):
        """Deve retornar apenas handlers com erro."""
        from src.observabilidade.consultas import handlers_com_erro

        resultados = handlers_com_erro(str(mock_csv_handler))
        assert len(resultados) == 1
        assert resultados[0]['erro'] == 'variante invalida'


class TestTempoMedioHandlers:
    """Testes para tempo medio de handlers."""

    def test_retorna_tempo_medio(self, mock_csv_handler: Path):
        """Deve retornar tempo medio por handler."""
        from src.observabilidade.consultas import tempo_medio_handlers

        resultados = tempo_medio_handlers(str(mock_csv_handler))
        assert len(resultados) == 2
        assert all('tempo_medio_ms' in r for r in resultados)


class TestSanitizarPath:
    """Testes para _sanitizar_path."""

    def test_path_inexistente_levanta_erro(self, tmp_path: Path):
        """Path inexistente deve levantar FileNotFoundError."""
        from src.observabilidade.consultas import _sanitizar_path

        with pytest.raises(FileNotFoundError):
            _sanitizar_path(str(tmp_path / 'nao_existe.csv'))

    def test_path_valido_retorna_absoluto(self, tmp_path: Path):
        """Path valido deve retornar path absoluto."""
        csv_file = tmp_path / 'test.csv'
        csv_file.touch()

        from src.observabilidade.consultas import _sanitizar_path

        result = _sanitizar_path(str(csv_file))
        assert Path(result).is_absolute()
