"""Testes para segmentacao de itens multiplos.

Fase 4.2 — Camada 2: Segmentacao de Itens Multiplos.

Abordagem adotada: Entity-Anchor (2A)
- noun_chunks (2B) falhou nos 3 casos com pt_core_news_sm:
  * "2 hamburguer e 1 coca" → gerou 1 chunk (esperado 2)
  * "hamburguer sem cebola e tomate" → gerou 2 chunks (esperado 1)
  * "hamburguer, batata e coca" → gerou 1 chunk (esperado 3)
- Entity-Anchor passou em todos os 3 casos.

A funcao segmentar_itens_noun_chunks permanece disponivel para futuros
experimentes com modelos maiores (pt_core_news_md/lg), mas nao e usada
no pipeline principal.
"""

import pytest

from src.extratores.segmentacao import (
    Segmento,
    segmentar_itens_entity_anchor,
)
from src.extratores.nlp_engine import NlpEngine
from src.extratores.config import get_extrator_config
from src.config import get_cardapio


@pytest.fixture
def cardapio():
    """Cardapio para testes."""
    return get_cardapio()


@pytest.fixture
def engine(cardapio):
    """NlpEngine inicializado para testes."""
    return NlpEngine(get_extrator_config(), cardapio)


def _get_itens(doc):
    """Retorna entidades marcadas como ITEM."""
    return [ent for ent in doc.ents if ent.label_ == 'ITEM']


class TestSegmentacaoDoisItens:
    """Teste: '2 hamburguer e 1 coca' → 2 segmentos."""

    def test_segmentacao_dois_itens(self, engine):
        """Entity-Anchor: '2 hamburguer e 1 coca' → 2 segmentos."""
        doc = engine.processar('2 hamburguer e 1 coca')
        itens = _get_itens(doc)
        segmentos = segmentar_itens_entity_anchor(doc, itens)
        assert len(segmentos) == 2


class TestSegmentacaoNaoParteRemocao:
    """Teste: 'hamburguer sem cebola e tomate' → 1 segmento.

    O 'e' aqui conecta dois ingredientes de remocao, nao dois itens.
    A segmentacao nao deve separar neste caso.
    """

    def test_segmentacao_nao_parte_remocao(self, engine):
        """Entity-Anchor: remocao com 'e' → 1 segmento."""
        doc = engine.processar('hamburguer sem cebola e tomate')
        itens = _get_itens(doc)
        segmentos = segmentar_itens_entity_anchor(doc, itens)
        assert len(segmentos) == 1


class TestSegmentacaoTresItens:
    """Teste: 'hamburguer, batata e coca' → 3 segmentos."""

    def test_segmentacao_tres_itens(self, engine):
        """Entity-Anchor: 3 ITEMs → 3 segmentos."""
        doc = engine.processar('hamburguer, batata e coca')
        itens = _get_itens(doc)
        segmentos = segmentar_itens_entity_anchor(doc, itens)
        assert len(segmentos) == 3


class TestSegmentoBasico:
    """Testes basicos do tipo Segmento."""

    def test_segmento_tem_texto_start_end(self):
        """Segmento deve ter texto, start e end."""
        seg = Segmento(texto='hamburguer e coca', start=0, end=3)
        assert seg.texto == 'hamburguer e coca'
        assert seg.start == 0
        assert seg.end == 3

    def test_segmento_eh_imutavel(self):
        """Segmento deve ser frozen (imutavel)."""
        seg = Segmento(texto='teste', start=0, end=1)
        try:
            seg.start = 5  # type: ignore[misc]
            raise AssertionError('Deveria levantar erro de imutabilidade')
        except (AttributeError, TypeError):
            pass  # Comportamento esperado para dataclass frozen

    def test_segmento_um_item_retorna_doc_inteiro(self, engine):
        """Com 1 ITEM, deve retornar 1 segmento cobrindo tudo."""
        doc = engine.processar('hamburguer duplo')
        itens = _get_itens(doc)
        segmentos = segmentar_itens_entity_anchor(doc, itens)
        assert len(segmentos) == 1
        assert segmentos[0].start == 0
        assert segmentos[0].end == len(doc)


class TestNounChunksLimitacao:
    """Documenta limitacoes conhecidas do noun_chunks para pt_core_news_sm.

    Estes testes documentam por que noun_chunks nao foi adotado.
    Podem ser reavaliados com modelos maiores (md/lg).
    """

    def test_noun_chunks_gera_poucos_chunks_dois_itens(self, engine):
        """pt_core_news_sm gera apenas 1 chunk para '2 hamburguer e 1 coca'."""
        doc = engine.processar('2 hamburguer e 1 coca')
        chunks = list(doc.noun_chunks)
        # Documenta limitacao: deveria ser 2, mas o modelo gera 1 ou menos
        assert len(chunks) < 2  # Limitacao conhecida

    def test_noun_chunks_gera_chunks_extras_remocao(self, engine):
        """pt_core_news_sm separa 'cebola' e 'tomate' em chunks distintos."""
        doc = engine.processar('hamburguer sem cebola e tomate')
        chunks = list(doc.noun_chunks)
        # Documenta limitacao: separa quando nao deveria
        assert len(chunks) > 1  # Gera chunks extras indevidos
