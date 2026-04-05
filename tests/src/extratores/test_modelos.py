"""Testes para dataclasses em modelos.py."""

import pytest
import spacy

from src.extratores.modelos import Segmento


class TestSegmentoSliceTokens:
    """Testes para Segmento.slice_tokens."""

    @pytest.fixture(scope="class")
    def doc(self):
        """Documento spaCy processado para testes."""
        nlp = spacy.blank("pt")
        text = "Quero um x-burguer sem cebola e uma coca cola"
        return nlp(text)

    def test_segmento_slice_tokens(self, doc):
        """Segmento com start=0, end=2 deve retornar texto dos 2 primeiros tokens."""
        segmento = Segmento(texto=doc.text, start=0, end=2)
        resultado = segmento.slice_tokens(doc)
        # Os 2 primeiros tokens do texto sao "Quero" e "um"
        esperado = doc[0:2].text
        assert resultado == esperado

    def test_segmento_slice_tokens_meio(self, doc):
        """Segmento no meio do texto deve retornar fatia correta."""
        segmento = Segmento(texto=doc.text, start=2, end=5)
        resultado = segmento.slice_tokens(doc)
        esperado = doc[2:5].text
        assert resultado == esperado

    def test_segmento_indices_sao_tokens_nao_chars(self, doc):
        """start/end sao indices de token, nao de caractere.

        Isso e documentado via type hint (int) e pelo comportamento:
        slice_tokens usa doc[start:end] que e fatiamento por token no spaCy.
        """
        # Se start/end fossem caracteres, start=0, end=5 pegaria "Quero"
        # Mas como sao tokens, start=0, end=1 pega apenas o primeiro token
        segmento = Segmento(texto=doc.text, start=0, end=1)
        resultado = segmento.slice_tokens(doc)
        assert resultado == "Quero"
        # Confirmar que e um token inteiro, nao caracteres soltos
        assert " " not in resultado


class TestSegmentoTypeHints:
    """Testes para type hints e imutabilidade do Segmento."""

    @pytest.fixture(scope="class")
    def doc(self):
        """Documento spaCy processado para testes."""
        nlp = spacy.blank("pt")
        text = "Quero um x-burguer sem cebola e uma coca cola"
        return nlp(text)

    def test_segmento_eh_frozen(self, doc):
        """Segmento deve ser imutavel (frozen=True)."""
        segmento = Segmento(texto=doc.text, start=0, end=2)
        with pytest.raises(Exception):  # FrozenInstanceError
            segmento.start = 5
