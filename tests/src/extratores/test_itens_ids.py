"""Testes para build_itens_ids."""

from __future__ import annotations

import pytest  # noqa: F401 — disponivel para testes futuros

from src.extratores.itens_ids import build_itens_ids


def test_build_itens_ids_inclui_nomes() -> None:
    """Nomes de itens devem estar no resultado."""
    cardapio = {
        'itens': [
            {'id': 'lanche_001', 'nome': 'Hamburguer', 'aliases': []},
        ],
    }
    resultado = build_itens_ids(cardapio)
    assert 'hamburguer' in resultado


def test_build_itens_ids_inclui_aliases() -> None:
    """Aliases devem estar no resultado."""
    cardapio = {
        'itens': [
            {'id': 'lanche_001', 'nome': 'Hamburguer', 'aliases': ['xis']},
        ],
    }
    resultado = build_itens_ids(cardapio)
    assert 'xis' in resultado


def test_build_itens_ids_normaliza() -> None:
    """Nomes com hifen e caracteres especiais devem ser normalizados."""
    cardapio = {
        'itens': [
            {'id': 'lanche_002', 'nome': 'X-Tudo', 'aliases': []},
        ],
    }
    resultado = build_itens_ids(cardapio)
    assert 'xtudo' in resultado


def test_build_itens_ids_retorna_frozenset() -> None:
    """O retorno deve ser um frozenset."""
    cardapio = {
        'itens': [
            {'id': 'lanche_001', 'nome': 'Hamburguer', 'aliases': []},
        ],
    }
    resultado = build_itens_ids(cardapio)
    assert isinstance(resultado, frozenset)
