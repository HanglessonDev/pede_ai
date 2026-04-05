"""Testes para os classificadores de lookup."""

import pytest

from src.roteador.classificadores.lookup import ClassificadorLookup, TOKENS_UNICOS


# ══════════════════════════════════════════════════════════════════════════════
# CLASSIFICADOR LOOKUP
# ══════════════════════════════════════════════════════════════════════════════


class TestClassificadorLookup:
    """Testes para ClassificadorLookup."""

    def test_match_exato(self):
        """Deve classificar por match exato."""
        lookup = ClassificadorLookup({'oi': 'saudacao'})
        resultado = lookup.classificar('oi')

        assert resultado is not None
        assert resultado.intent == 'saudacao'
        assert resultado.confidence == 1.0
        assert resultado.caminho == 'lookup'

    def test_sem_match_retorna_none(self):
        """Sem match deve retornar None."""
        lookup = ClassificadorLookup({'oi': 'saudacao'})
        resultado = lookup.classificar('quero lanche')

        assert resultado is None

    def test_case_insensitive(self):
        """Deve ser case insensitive."""
        lookup = ClassificadorLookup({'oi': 'saudacao'})
        resultado = lookup.classificar('OI')

        assert resultado is not None
        assert resultado.intent == 'saudacao'

    def test_strip_espacos(self):
        """Deve ignorar espacos extras."""
        lookup = ClassificadorLookup({'oi': 'saudacao'})
        resultado = lookup.classificar('  oi  ')

        assert resultado is not None
        assert resultado.intent == 'saudacao'

    def test_tokens_unicos_padrao(self):
        """Deve usar TOKENS_UNICOS padrao se nenhum fornecido."""
        lookup = ClassificadorLookup()
        resultado = lookup.classificar('sim')

        assert resultado is not None
        assert resultado.intent == 'confirmar'

    @pytest.mark.parametrize(
        'token,intencao',
        [
            ('sim', 'confirmar'),
            ('não', 'negar'),
            ('nao', 'negar'),
            ('oi', 'saudacao'),
            ('ola', 'saudacao'),
            ('cancela', 'cancelar'),
            ('tira', 'remover'),
            ('troca', 'trocar'),
        ],
    )
    def test_todos_tokens_unicos(self, token: str, intencao: str):
        """Todos os tokens unicos devem classificar corretamente."""
        lookup = ClassificadorLookup(TOKENS_UNICOS)
        resultado = lookup.classificar(token)

        assert resultado is not None
        assert resultado.intent == intencao
        assert resultado.confidence == 1.0

    def test_resultado_contem_metadata(self):
        """Resultado deve conter metadata correta."""
        lookup = ClassificadorLookup({'oi': 'saudacao'})
        resultado = lookup.classificar('oi')

        assert resultado is not None
        assert resultado.top1_texto == 'oi'
        assert resultado.top1_intencao == 'saudacao'
        assert resultado.mensagem_norm == 'oi'
