"""Testes do slot_fill — validacao cruzada entre extrator e cardapio.

TDD: testes escritos antes da implementacao.
"""

from __future__ import annotations

import pytest

from src.config import get_cardapio
from src.extratores.slot_fill import slot_fill_menu_first


@pytest.fixture
def cardapio():
    return get_cardapio()


class TestSlotFillMenuFirst:
    """slot_fill_menu_first: encontra itens do cardapio na mensagem."""

    def test_slot_fill_encontra_item_por_nome(self, cardapio):
        """'quero um hamburguer' -> ['lanche_001']."""
        result = slot_fill_menu_first('quero um hamburguer', cardapio)
        assert 'lanche_001' in result

    def test_slot_fill_encontra_item_por_alias(self, cardapio):
        """'quero uma coquinha' -> ['bebida_001']."""
        result = slot_fill_menu_first('quero uma coquinha', cardapio)
        assert 'bebida_001' in result

    def test_slot_fill_sem_item(self, cardapio):
        """'boa tarde' -> []."""
        result = slot_fill_menu_first('boa tarde', cardapio)
        assert result == []

    def test_slot_fill_multiplos_itens(self, cardapio):
        """'hamburguer e coca' -> ambos os itens."""
        result = slot_fill_menu_first('hamburguer e coca', cardapio)
        assert 'lanche_001' in result
        assert 'bebida_001' in result

    def test_slot_fill_encontra_por_xis(self, cardapio):
        """'xis sem cebola' -> reconhece hamburguer via alias 'xis'."""
        result = slot_fill_menu_first('xis sem cebola', cardapio)
        assert 'lanche_001' in result


class TestSlotFillValidacaoCruzada:
    """Integracao: validacao cruzada reduz confianca quando diverge."""

    def test_slot_fill_reduz_confianca_quando_diverge(self):
        """Pipeline extrai item que slot fill nao confirma -> confianca < 1.0."""
        from src.extratores.extrator import extrair

        # Mensagem onde o extrator pode extrair algo espurio
        # mas o slot fill nao encontra nenhum item do cardapio
        result = extrair('boa tarde')
        # Se extrair retornou algo, deve ter confianca reduzida
        # ou retornar vazio (ambos sao aceitaveis)
        if result:
            for item in result:
                assert item.get('confianca', 1.0) < 1.0
        else:
            # Retornar vazio tambem e comportamento correto
            assert result == []
