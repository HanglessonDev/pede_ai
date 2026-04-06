"""Testes para detecção de negação — Fase 4.1.

Cobrem os 7 cenarios do PLANO_IMPLEMENTACAO.md:
- Bug #7: "nao quero hamburguer" deve retornar []
- Negação com acento
- Expressoes coloquiais (esquece, cancela, deixa pra la, melhor nao)
- "sem" e remocao, NAO negacao
"""

from __future__ import annotations


from src.extratores import extrair
from src.extratores.config import get_extrator_config
from src.extratores.negacao import detectar_negacao


# ══════════════════════════════════════════════════════════════════════════════
# Testes unitarios — detectar_negacao()
# ══════════════════════════════════════════════════════════════════════════════


class TestDetectarNegacaoUnit:
    """Testes diretos da funcao detectar_negacao()."""

    def setup_method(self):
        """Carrega config antes de cada teste."""
        self.config = get_extrator_config()

    def test_bug7_nao_quero_hamburguer(self):
        """ "nao quero hamburguer" -> True (negacao detectada)."""
        assert detectar_negacao('nao quero hamburguer', self.config) is True

    def test_negacao_com_acento(self):
        """ "não quero nada" -> True (acento contabilizado)."""
        assert detectar_negacao('não quero nada', self.config) is True

    def test_negacao_coloquial_esquece(self):
        """ "esquece o hamburguer" -> True."""
        assert detectar_negacao('esquece o hamburguer', self.config) is True

    def test_negacao_coloquial_cancela(self):
        """ "cancela a coca" -> True."""
        assert detectar_negacao('cancela a coca', self.config) is True

    def test_negacao_coloquial_deixa(self):
        """ "deixa pra lá" -> True."""
        assert detectar_negacao('deixa pra lá', self.config) is True

    def test_negacao_melhor_nao(self):
        """ "melhor não" -> True."""
        assert detectar_negacao('melhor não', self.config) is True

    def test_sem_nao_e_negacao(self):
        """ "hamburguer sem cebola" -> False ("sem" e remocao, nao negacao)."""
        assert detectar_negacao('hamburguer sem cebola', self.config) is False


# ══════════════════════════════════════════════════════════════════════════════
# Testes de integracao — extrair() com negacao
# ══════════════════════════════════════════════════════════════════════════════


class TestNegacaoIntegracao:
    """Testes via API publica extrair() — confirma que negacao retorna []."""

    def test_bug7_nao_quero_hamburguer_extrair(self):
        """ "nao quero hamburguer" -> [] (pipeline retorna vazio)."""
        result = extrair('nao quero hamburguer')
        assert result == []

    def test_negacao_com_acento_extrair(self):
        """ "não quero nada" -> []."""
        result = extrair('não quero nada')
        assert result == []

    def test_negacao_coloquial_esquece_extrair(self):
        """ "esquece o hamburguer" -> []."""
        result = extrair('esquece o hamburguer')
        assert result == []

    def test_negacao_coloquial_cancela_extrair(self):
        """ "cancela a coca" -> []."""
        result = extrair('cancela a coca')
        assert result == []

    def test_negacao_coloquial_deixa_extrair(self):
        """ "deixa pra lá" -> []."""
        result = extrair('deixa pra lá')
        assert result == []

    def test_negacao_melhor_nao_extrair(self):
        """ "melhor não" -> []."""
        result = extrair('melhor não')
        assert result == []

    def test_sem_nao_e_remocao_nao_negacao_extrair(self):
        """ "hamburguer sem cebola" -> extrai item com remocoes=['cebola']."""
        result = extrair('hamburguer sem cebola')
        assert len(result) == 1
        assert result[0]['item_id'] == 'lanche_001'
        assert result[0]['remocoes'] == ['cebola']
