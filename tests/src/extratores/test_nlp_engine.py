"""Testes para NlpEngine — EntityRuler e label NUM_PENDING."""

import pytest

from src.extratores.nlp_engine import NlpEngine
from src.extratores.config import get_extrator_config
from src.config import get_cardapio


@pytest.fixture
def cardapio():
    """Cardapio para testes."""
    return get_cardapio()


@pytest.fixture
def engine(cardapio):
    """NlpEngine inicializado."""
    return NlpEngine(get_extrator_config(), cardapio)


class TestEntityRulerNumPending:
    """EntityRuler deve marcar digitos como NUM_PENDING, nao QTD."""

    def test_digito_vira_num_pending(self, engine):
        """Processar '2 hamburguer' — entidade '2' deve ter label NUM_PENDING."""
        doc = engine.processar('2 hamburguer')
        digit_entities = [ent for ent in doc.ents if ent.text == '2']
        assert len(digit_entities) >= 1
        assert digit_entities[0].label_ == 'NUM_PENDING'

    def test_digito_nao_vira_qtd(self, engine):
        """Processar '2 hamburguer' — NAO deve existir entidade com label QTD."""
        doc = engine.processar('2 hamburguer')
        qtd_entities = [ent for ent in doc.ents if ent.label_ == 'QTD']
        assert len(qtd_entities) == 0
