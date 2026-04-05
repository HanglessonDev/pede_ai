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

    def test_meio_vira_num_pending(self, engine):
        """Processar 'meio hamburguer' — entidade 'meio' deve ter label NUM_PENDING."""
        doc = engine.processar('meio hamburguer')
        meio_entities = [ent for ent in doc.ents if ent.text.lower() == 'meio']
        assert len(meio_entities) >= 1
        assert meio_entities[0].label_ == 'NUM_PENDING'

    def test_meia_vira_num_pending(self, engine):
        """Processar 'meia porcao' — entidade 'meia' deve ter label NUM_PENDING."""
        doc = engine.processar('meia porcao')
        meia_entities = [ent for ent in doc.ents if ent.text.lower() == 'meia']
        assert len(meia_entities) >= 1
        assert meia_entities[0].label_ == 'NUM_PENDING'

    def test_numeros_extenso_nao_duplicados(self, engine):
        """Patterns gerados por gerar_patterns() nao devem duplicar numeros por extenso.

        Palavras como 'um', 'dois' devem aparecer exatamente uma vez nos patterns
        do cardapio, sem duplicata.
        """
        from src.extratores.patterns import gerar_patterns
        from src.extratores.normalizador import normalizar_para_busca

        cardapio = get_cardapio()
        patterns = gerar_patterns(cardapio, normalizar_para_busca)

        # Coletar todas palavra LOWER dos patterns
        lower_tokens = []
        for p in patterns:
            for token in p['pattern']:
                if 'LOWER' in token:
                    lower_tokens.append(token['LOWER'])

        # 'um' e 'dois' devem aparecer no maximo 1 vez
        assert lower_tokens.count('um') <= 1, f"'um' aparece {lower_tokens.count('um')} vezes nos patterns"
        assert lower_tokens.count('dois') <= 1, f"'dois' aparece {lower_tokens.count('dois')} vezes nos patterns"
