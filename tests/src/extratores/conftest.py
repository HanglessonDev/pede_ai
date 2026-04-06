"""Fixtures compartilhadas para testes dos extratores."""

import pytest

from src.config.cardapio import get_cardapio
from src.extratores.config import get_extrator_config
from src.extratores.nlp_engine import NlpEngine


@pytest.fixture(scope='session')
def cardapio():
    """Cardapio completo carregado do YAML."""
    return get_cardapio()


@pytest.fixture(scope='session')
def config():
    """Configuracao do extrator."""
    return get_extrator_config()


@pytest.fixture(scope='session')
def engine(config, cardapio):
    """NlpEngine com modelo spaCy lazy-loaded."""
    return NlpEngine(config, cardapio)
