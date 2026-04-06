"""Testes para o modulo unificado de quantidade.

TDD: estes testes foram escritos ANTES da implementacao.
Cobrem resolver_quantidade e extrair_quantidade_do_texto.
"""


from src.extratores.config import ExtratorConfig
from src.extratores.quantidade import extrair_quantidade_do_texto, resolver_quantidade

CONFIG = ExtratorConfig()


# ── TestResolverQuantidade ────────────────────────────────────────────────


class TestResolverQuantidade:
    """Testes para resolver_quantidade()."""

    def test_digito(self):
        """'2' -> 2"""
        assert resolver_quantidade('2', CONFIG) == 2

    def test_numero_extenso(self):
        """'quatro' -> 4"""
        assert resolver_quantidade('quatro', CONFIG) == 4

    def test_fracionario(self):
        """'meio' -> 0.5"""
        assert resolver_quantidade('meio', CONFIG) == 0.5

    def test_desconhecido(self):
        """'xyz' -> None"""
        assert resolver_quantidade('xyz', CONFIG) is None

    def test_case_insensitive(self):
        """'QUATRO' -> 4"""
        assert resolver_quantidade('QUATRO', CONFIG) == 4

    def test_acento(self):
        """'tres' (sem acento) -> 3"""
        assert resolver_quantidade('tres', CONFIG) == 3


# ── TestExtrairQuantidadeDoTexto ──────────────────────────────────────────


class TestExtrairQuantidadeDoTexto:
    """Testes para extrair_quantidade_do_texto()."""

    def test_digito_no_inicio(self):
        """'2 hamburguer' -> (2, 'hamburguer')"""
        qtd, resto = extrair_quantidade_do_texto('2 hamburguer', CONFIG)
        assert qtd == 2
        assert resto == 'hamburguer'

    def test_numero_extenso_no_inicio(self):
        """'quatro sucos' -> (4, 'sucos')"""
        qtd, resto = extrair_quantidade_do_texto('quatro sucos', CONFIG)
        assert qtd == 4
        assert resto == 'sucos'

    def test_sem_quantidade(self):
        """'hamburguer duplo' -> (None, 'hamburguer duplo')"""
        qtd, resto = extrair_quantidade_do_texto('hamburguer duplo', CONFIG)
        assert qtd is None
        assert resto == 'hamburguer duplo'

    def test_fracionario_no_inicio(self):
        """'meio hamburguer' -> (0.5, 'hamburguer')"""
        qtd, resto = extrair_quantidade_do_texto('meio hamburguer', CONFIG)
        assert qtd == 0.5
        assert resto == 'hamburguer'
