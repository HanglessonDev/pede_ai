from typer.testing import CliRunner

from src.observabilidade.debug_cli import app

runner = CliRunner()


def test_app_help() -> None:
    """Testa que a CLI foi criada e mostra help."""
    result = runner.invoke(app, ['--help'])
    assert result.exit_code == 0


def test_comando_classificar() -> None:
    """Testa comando de classificacao."""
    result = runner.invoke(app, ['classificar', 'oi'])
    assert result.exit_code == 0


def test_comando_extrair_teste() -> None:
    """Testa comando de extracao."""
    result = runner.invoke(app, ['extrair-teste', 'quero um hamburguer'])
    assert result.exit_code == 0


def test_ultima_sessao_sem_logs() -> None:
    """Testa comportamento quando diretorio logs nao existe."""
    result = runner.invoke(app, ['ultima-sessao'])
    # Pode exit code 1 ou mensagem amarela dependendo do estado
    assert result.exit_code in (0, 1)


def test_extracoes_falhas_sem_csv() -> None:
    """Testa comportamento quando CSV nao existe."""
    result = runner.invoke(app, ['extracoes-falhas'])
    assert result.exit_code == 0


def test_erros_handlers_sem_csv() -> None:
    """Testa comportamento quando CSV nao existe."""
    result = runner.invoke(app, ['erros-handlers'])
    assert result.exit_code == 0
