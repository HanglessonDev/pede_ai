"""Testes para os value objects do roteador."""

from copy import copy

import pytest

from src.roteador.modelos import (
    ExemploClassificacao,
    ExemploSimilar,
    ResultadoClassificacao,
)


# ══════════════════════════════════════════════════════════════════════════════
# RESULTADO CLASSIFICACAO
# ══════════════════════════════════════════════════════════════════════════════


class TestResultadoClassificacao:
    """Testes para ResultadoClassificacao."""

    def test_criacao_completa(self):
        """Deve criar com todos os campos."""
        resultado = ResultadoClassificacao(
            intent='pedir',
            confidence=0.95,
            caminho='rag_forte',
            top1_texto='quero um xbacon',
            top1_intencao='pedir',
            mensagem_norm='quero um xbacon',
        )

        assert resultado.intent == 'pedir'
        assert resultado.confidence == 0.95
        assert resultado.caminho == 'rag_forte'
        assert resultado.top1_texto == 'quero um xbacon'
        assert resultado.top1_intencao == 'pedir'
        assert resultado.mensagem_norm == 'quero um xbacon'

    def test_imutavel(self):
        """Deve ser imutavel (frozen)."""
        resultado = ResultadoClassificacao(
            intent='pedir',
            confidence=0.95,
            caminho='rag_forte',
            top1_texto='',
            top1_intencao='',
            mensagem_norm='',
        )

        with pytest.raises(AttributeError):
            resultado.intent = 'saudacao'  # type: ignore

    def test_equality(self):
        """Instancias com mesmos valores devem ser iguais."""
        a = ResultadoClassificacao(
            intent='pedir',
            confidence=0.95,
            caminho='rag_forte',
            top1_texto='',
            top1_intencao='',
            mensagem_norm='',
        )
        b = ResultadoClassificacao(
            intent='pedir',
            confidence=0.95,
            caminho='rag_forte',
            top1_texto='',
            top1_intencao='',
            mensagem_norm='',
        )

        assert a == b

    def test_inequality(self):
        """Instancias com valores diferentes nao devem ser iguais."""
        a = ResultadoClassificacao(
            intent='pedir',
            confidence=0.95,
            caminho='rag_forte',
            top1_texto='',
            top1_intencao='',
            mensagem_norm='',
        )
        b = ResultadoClassificacao(
            intent='saudacao',
            confidence=0.95,
            caminho='rag_forte',
            top1_texto='',
            top1_intencao='',
            mensagem_norm='',
        )

        assert a != b

    def test_hashable(self):
        """Deve ser hashable (frozen dataclass)."""
        resultado = ResultadoClassificacao(
            intent='pedir',
            confidence=0.95,
            caminho='rag_forte',
            top1_texto='',
            top1_intencao='',
            mensagem_norm='',
        )

        # Nao deve levantar excecao
        hash(resultado)

    def test_usavel_em_set(self):
        """Deve ser usavel como elemento de set."""
        a = ResultadoClassificacao(
            intent='pedir',
            confidence=0.95,
            caminho='rag_forte',
            top1_texto='',
            top1_intencao='',
            mensagem_norm='',
        )
        b = ResultadoClassificacao(
            intent='pedir',
            confidence=0.95,
            caminho='rag_forte',
            top1_texto='',
            top1_intencao='',
            mensagem_norm='',
        )

        conjunto = {a, b}
        assert len(conjunto) == 1

    def test_copy_retorna_igual(self):
        """Copy deve retornar instancia igual (mesmo que nao seja a mesma)."""
        resultado = ResultadoClassificacao(
            intent='pedir',
            confidence=0.95,
            caminho='rag_forte',
            top1_texto='',
            top1_intencao='',
            mensagem_norm='',
        )

        copia = copy(resultado)
        assert copia == resultado
        assert copia is not resultado

    @pytest.mark.parametrize(
        'caminho',
        ['lookup', 'rag_forte', 'llm_rag', 'llm_fixo'],
    )
    def test_caminhos_validos(self, caminho: str):
        """Todos os caminhos validos devem ser aceitos."""
        resultado = ResultadoClassificacao(
            intent='pedir',
            confidence=0.95,
            caminho=caminho,  # type: ignore
            top1_texto='',
            top1_intencao='',
            mensagem_norm='',
        )

        assert resultado.caminho == caminho


# ══════════════════════════════════════════════════════════════════════════════
# EXEMPLO CLASSIFICACAO
# ══════════════════════════════════════════════════════════════════════════════


class TestExemploClassificacao:
    """Testes para ExemploClassificacao."""

    def test_criacao(self):
        """Deve criar com texto e intencao."""
        exemplo = ExemploClassificacao(texto='oi', intencao='saudacao')

        assert exemplo.texto == 'oi'
        assert exemplo.intencao == 'saudacao'

    def test_imutavel(self):
        """Deve ser imutavel."""
        exemplo = ExemploClassificacao(texto='oi', intencao='saudacao')

        with pytest.raises(AttributeError):
            exemplo.texto = 'ola'  # type: ignore

    def test_equality(self):
        """Instancias iguais devem ser iguais."""
        a = ExemploClassificacao(texto='oi', intencao='saudacao')
        b = ExemploClassificacao(texto='oi', intencao='saudacao')

        assert a == b


# ══════════════════════════════════════════════════════════════════════════════
# EXEMPLO SIMILAR
# ══════════════════════════════════════════════════════════════════════════════


class TestExemploSimilar:
    """Testes para ExemploSimilar."""

    def test_criacao(self):
        """Deve criar com todos os campos."""
        exemplo = ExemploSimilar(
            texto='oi',
            intencao='saudacao',
            similaridade=0.95,
        )

        assert exemplo.texto == 'oi'
        assert exemplo.intencao == 'saudacao'
        assert exemplo.similaridade == 0.95

    def test_imutavel(self):
        """Deve ser imutavel."""
        exemplo = ExemploSimilar(
            texto='oi',
            intencao='saudacao',
            similaridade=0.95,
        )

        with pytest.raises(AttributeError):
            exemplo.similaridade = 1.0  # type: ignore

    def test_equality(self):
        """Instancias iguais devem ser iguais."""
        a = ExemploSimilar(texto='oi', intencao='saudacao', similaridade=0.95)
        b = ExemploSimilar(texto='oi', intencao='saudacao', similaridade=0.95)

        assert a == b

    def test_inequality_diferente_similaridade(self):
        """Similaridade diferente deve resultar em desigualdade."""
        a = ExemploSimilar(texto='oi', intencao='saudacao', similaridade=0.95)
        b = ExemploSimilar(texto='oi', intencao='saudacao', similaridade=0.80)

        assert a != b
