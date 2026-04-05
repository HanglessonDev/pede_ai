"""Testes para ExtratorConfig — novos campos (Fase 1.5)."""

from src.extratores.config import get_extrator_config


def test_config_tem_palavras_complemento():
    """get_extrator_config().palavras_complemento contém 'com', 'extra', 'adicional'."""
    config = get_extrator_config()
    assert 'com' in config.palavras_complemento
    assert 'extra' in config.palavras_complemento
    assert 'adicional' in config.palavras_complemento


def test_config_tem_numeros_fracionarios():
    """config.numeros_fracionarios['meio'] == 0.5."""
    config = get_extrator_config()
    assert config.numeros_fracionarios['meio'] == 0.5


def test_config_tem_palavras_negacao_coloquiais():
    """'esquece' e 'cancela' estão em config.palavras_negacao."""
    config = get_extrator_config()
    assert 'esquece' in config.palavras_negacao
    assert 'cancela' in config.palavras_negacao
