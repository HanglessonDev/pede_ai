"""Testes para extracao de quantidade via regex posicional."""

import pytest

from src.extratores.qtd_regex import extrair_qtd_regex


def test_qtd_regex_digito():
    """Extrai quantidade numerica do inicio do segmento."""
    qtd, resto = extrair_qtd_regex("2 hamburguer")
    assert qtd == 2
    assert resto == "hamburguer"


def test_qtd_regex_meio():
    """Extrai 'meio' como 0.5."""
    qtd, resto = extrair_qtd_regex("meio hamburguer")
    assert qtd == 0.5
    assert resto == "hamburguer"


def test_qtd_regex_meia():
    """Extrai 'meia' como 0.5."""
    qtd, resto = extrair_qtd_regex("meia porcao")
    assert qtd == 0.5
    assert resto == "porcao"


def test_qtd_regex_sem_qtd():
    """Retorna None quando nao ha quantidade no inicio."""
    qtd, resto = extrair_qtd_regex("hamburguer duplo")
    assert qtd is None
    assert resto == "hamburguer duplo"


def test_qtd_regex_nao_case_sensitive():
    """Extracao nao diferencia maiusculas/minusculas."""
    qtd, resto = extrair_qtd_regex("DOIS hamburguer")
    assert qtd == 2
    assert resto == "hamburguer"
