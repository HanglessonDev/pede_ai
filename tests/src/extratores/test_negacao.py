"""Testes para detectar_negacao — deteção de negacao/cancelamento.

TDD: testes escritos ANTES da implementacao.
Cobre falsos positivos (condicionais, descricoes) e casos verdadeiros.
"""

from __future__ import annotations

import pytest

from src.extratores.negacao import detectar_negacao


# ══════════════════════════════════════════════════════════════════════════════
# False positives — NAO sao negacoes
# ══════════════════════════════════════════════════════════════════════════════


class TestFalsosPositivos:
    """Casos onde 'nao/nao' aparece mas NAO e' negacao de pedido."""

    def test_negacao_falso_positivo_condicional(self):
        """'se nao for incomodo' → False (condicional, nao negacao)."""
        assert detectar_negacao('oito x-salada, se nao for incomodo') is False

    def test_negacao_falso_positivo_descricao(self):
        """'nao pode murcha' → False (descricao de preferencia, nao negacao)."""
        assert detectar_negacao('batata frita crocante, por favor, nao pode murcha') is False

    def test_negacao_falso_positivo_se_nao(self):
        """'se nao tiver, manda sem' → False (condicional)."""
        assert detectar_negacao('se nao tiver, manda sem') is False

    def test_negacao_falso_positivo_nao_quero_que(self):
        """'quero que nao venha cebola' → False (e' remocao, nao negacao do pedido)."""
        assert detectar_negacao('hamburguer, quero que nao venha cebola') is False


# ══════════════════════════════════════════════════════════════════════════════
# True positives — SAO negacoes
# ══════════════════════════════════════════════════════════════════════════════


class TestVerdadeirosPositivos:
    """Casos onde o usuario esta negando/cancelando o pedido."""

    def test_nao_quero(self):
        """'nao quero hamburguer' → True."""
        assert detectar_negacao('nao quero hamburguer') is True

    def test_nao_quero_acento(self):
        """'nao quero hamburguer' → True."""
        assert detectar_negacao('nao quero hamburguer') is True

    def test_quero_nao(self):
        """'hamburguer quero nao' → True."""
        assert detectar_negacao('hamburguer quero nao') is True

    def test_esquece(self):
        """'esquece' → True (cancelamento direto)."""
        assert detectar_negacao('esquece') is True

    def test_esqueca(self):
        """'esqueca' → True (cancelamento direto)."""
        assert detectar_negacao('esqueca') is True

    def test_cancela(self):
        """'cancela' → True (cancelamento direto)."""
        assert detectar_negacao('cancela') is True

    def test_desisto(self):
        """'desisto' → True (cancelamento direto)."""
        assert detectar_negacao('desisto') is True

    def test_deixa_pra_la(self):
        """'deixa pra la' → True."""
        assert detectar_negacao('deixa pra la') is True

    def test_deixa_para_la(self):
        """'deixa para la' → True."""
        assert detectar_negacao('deixa para la') is True

    def test_muda_de_ideia(self):
        """'muda de ideia' → True."""
        assert detectar_negacao('muda de ideia') is True

    def test_melhor_nao(self):
        """'melhor nao' → True (rejeicao suave)."""
        assert detectar_negacao('melhor nao') is True

    def test_melhor_nao_acento(self):
        """'melhor nao' → True (rejeicao suave)."""
        assert detectar_negacao('melhor nao') is True


# ══════════════════════════════════════════════════════════════════════════════
# Neutros — sem negacao
# ══════════════════════════════════════════════════════════════════════════════


class TestSemNegacao:
    """Frases de pedido validas sem nenhuma negacao."""

    def test_pedido_simples(self):
        """'quero um hamburguer' → False."""
        assert detectar_negacao('quero um hamburguer') is False

    def test_pedido_com_remocao(self):
        """'hamburguer sem cebola' → False (sem e' remocao, nao negacao)."""
        assert detectar_negacao('hamburguer sem cebola') is False

    def test_pedido_com_variante(self):
        """'uma coca lata' → False."""
        assert detectar_negacao('uma coca lata') is False

    def test_pedido_multiplo(self):
        """'dois hamburguer e uma coca' → False."""
        assert detectar_negacao('dois hamburguer e uma coca') is False

    def test_texto_vazio(self):
        """'' → False."""
        assert detectar_negacao('') is False

    def test_so_espaco(self):
        """'   ' → False."""
        assert detectar_negacao('   ') is False


# ══════════════════════════════════════════════════════════════════════════════
# Edge cases
# ══════════════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Casos de borda para robustez."""

    def test_nem_quero(self):
        """'nem quero' → True (nem + verbo de desejo)."""
        assert detectar_negacao('nem quero') is True

    def test_quer_nao(self):
        """'ele quer nao' → True (verbo de desejo + nao)."""
        assert detectar_negacao('ele quer nao') is True

    def test_nao_quer(self):
        """'ele nao quer nada' → True (nao + verbo de desejo)."""
        assert detectar_negacao('ele nao quer nada') is True
