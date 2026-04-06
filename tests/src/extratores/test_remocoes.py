"""Testes para capturar_remocoes_v2 — filtragem scope-aware.

Bug: a funcao original capturar_remocoes() nao filtra tokens que sao ITEMs
do cardapio. Ex: "sem cebola hamburguer" capturava ['cebola', 'hamburguer']
quando deveria capturar apenas ['cebola'].
"""

from src.extratores.normalizador import normalizar_para_busca
from src.extratores.remocoes import capturar_remocoes_v2
from src.extratores.config import get_extrator_config


def _build_itens_ids() -> frozenset[str]:
    """Constroi set de nomes + aliases normalizados do cardapio."""
    from src.config import get_cardapio

    cardapio = get_cardapio()
    ids: set[str] = set()
    for item in cardapio['itens']:
        ids.add(normalizar_para_busca(item['nome']))
        for alias in item.get('aliases', []):
            ids.add(normalizar_para_busca(alias))
    return frozenset(ids)


def _mock_doc(text: str):
    """Cria um mock Doc com tokens simples (sem spaCy real)."""
    from unittest.mock import MagicMock

    tokens = []
    for i, word in enumerate(text.split()):
        token = MagicMock()
        token.text = word
        token.lower_ = word.lower()
        token.i = i
        token.pos_ = 'NOUN'
        tokens.append(token)

    doc = MagicMock()
    doc.__iter__ = lambda self: iter(tokens)
    doc.__len__ = lambda self: len(tokens)
    return doc


ITENS_IDS = _build_itens_ids()


class TestRemocoesScopeAware:
    """Testes para bugs de itens sendo capturados como remocoes."""

    def test_bug1_item_nao_vira_remocao(self):
        """ "sem cebola hamburguer" → remocoes=["cebola"], hamburguer = item."""
        doc = _mock_doc('sem cebola hamburguer')
        config = get_extrator_config()
        remocoes = capturar_remocoes_v2(doc, config, ITENS_IDS)
        textos = [r[0].lower() for r in remocoes]
        assert 'cebola' in textos
        assert 'hamburguer' not in textos

    def test_bug5_item_antes_do_sem(self):
        """ "batata sem sal" → remocoes=["sal"] apenas."""
        doc = _mock_doc('batata sem sal')
        config = get_extrator_config()
        remocoes = capturar_remocoes_v2(doc, config, ITENS_IDS)
        textos = [r[0].lower() for r in remocoes]
        assert textos == ['sal']
        assert 'batata' not in textos

    def test_multiplas_remocoes_com_e(self):
        """ "sem cebola e tomate" → remocoes=["cebola", "tomate"]."""
        doc = _mock_doc('sem cebola e tomate')
        config = get_extrator_config()
        remocoes = capturar_remocoes_v2(doc, config, ITENS_IDS)
        textos = [r[0].lower() for r in remocoes]
        assert 'cebola' in textos
        assert 'tomate' in textos

    def test_remocao_para_antes_de_novo_item(self):
        """ "sem cebola hamburguer e coca" → cebola = remocao, coca = item separado."""
        doc = _mock_doc('sem cebola hamburguer e coca')
        config = get_extrator_config()
        remocoes = capturar_remocoes_v2(doc, config, ITENS_IDS)
        textos = [r[0].lower() for r in remocoes]
        assert 'cebola' in textos
        assert 'hamburguer' not in textos
        assert 'coca' not in textos


class TestRemocoesFiltroStopWords:
    """Testes para garantir que stop words nao sao capturadas como remocoes."""

    def test_remocao_nao_captura_favor(self):
        """ "coca sem gelo por favor" → remocoes=["gelo"] apenas, nao "favor"."""
        doc = _mock_doc('coca sem gelo por favor')
        config = get_extrator_config()
        remocoes = capturar_remocoes_v2(doc, config, ITENS_IDS)
        textos = [r[0].lower() for r in remocoes]
        assert textos == ['gelo']
        assert 'favor' not in textos
        assert 'por' not in textos

    def test_remocao_nao_captura_stop_words(self):
        """ "xis sem nada além do básico" → remocoes=[] (nada, além, básico sao filtro)."""
        doc = _mock_doc('xis sem nada além do básico')
        config = get_extrator_config()
        remocoes = capturar_remocoes_v2(doc, config, ITENS_IDS)
        textos = [r[0].lower() for r in remocoes]
        assert textos == []

    def test_remocao_nao_captura_tambem(self):
        """ "x-tudo sem queijo e também sem alface" → remocoes=["queijo", "alface"]."""
        doc = _mock_doc('x-tudo sem queijo e também sem alface')
        config = get_extrator_config()
        remocoes = capturar_remocoes_v2(doc, config, ITENS_IDS)
        textos = [r[0].lower() for r in remocoes]
        assert 'queijo' in textos
        assert 'alface' in textos
        assert 'também' not in textos
