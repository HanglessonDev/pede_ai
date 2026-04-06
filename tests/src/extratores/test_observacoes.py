"""Testes para deteco de observacoes (Camada 7).

Testam detectar_observacoes() do modulo src.extratores.observacoes.
"""

from __future__ import annotations


from src.extratores.observacoes import detectar_observacoes
from src.config import get_cardapio


def _processar(texto: str):
    """Processa texto com o NLP engine real."""
    from src.extratores.nlp_engine import NlpEngine
    from src.extratores.config import get_extrator_config

    config = get_extrator_config()
    cardapio = get_cardapio()
    engine = NlpEngine(config, cardapio)
    return engine.processar(texto)


class TestDetectarObservacoes:
    """Testes para detectar_observacoes()."""

    def test_observacao_lista_fixa(self):
        """'coca bem gelada' -> observacoes=['bem gelada']."""
        doc = _processar('coca bem gelada')
        result = detectar_observacoes(doc)
        assert (
            'bem gelada' in ' '.join(result).lower()
            or 'gelada' in ' '.join(result).lower()
        )

    def test_observacao_caprichado(self):
        """'hamburguer caprichado' -> observacoes=['caprichado']."""
        doc = _processar('hamburguer caprichado')
        result = detectar_observacoes(doc)
        assert any('caprichado' in obs.lower() for obs in result)

    def test_modificador_bem_passado(self):
        """'hamburguer bem passado' -> observacoes=['bem passado']."""
        doc = _processar('hamburguer bem passado')
        result = detectar_observacoes(doc)
        assert 'bem passado' in ' '.join(result).lower()

    def test_modificador_super(self):
        """'coca super gelada' -> observacoes=['super gelada']."""
        doc = _processar('coca super gelada')
        result = detectar_observacoes(doc)
        assert any('gelada' in obs.lower() for obs in result)

    def test_sem_observacao(self):
        """'hamburguer duplo' -> observacoes=[]."""
        doc = _processar('hamburguer duplo')
        result = detectar_observacoes(doc)
        assert result == []

    def test_observacao_nao_captura_trigger_complemento(self):
        """'batata com bastante cheddar' -> observacoes=[] (e complemento, nao observacao)."""
        doc = _processar('batata com bastante cheddar')
        result = detectar_observacoes(doc)
        assert result == []

    def test_observacao_ignora_frases_com_com(self):
        """'coca com bastante gelo' -> observacoes=[]."""
        doc = _processar('coca com bastante gelo')
        result = detectar_observacoes(doc)
        assert result == []


class TestDetectarModificadores:
    """Testes para detectar_modificadores()."""

    def test_modificador_bem_gelada(self):
        """'bem gelada' deve ser detectado."""
        doc = _processar('coca bem gelada')
        from src.extratores.observacoes import detectar_modificadores

        mods = detectar_modificadores(doc)
        assert any('bem' in m and 'gelada' in m for m in mods)

    def test_modificador_muito_quente(self):
        """'muito quente' deve ser detectado."""
        doc = _processar('cafe muito quente')
        from src.extratores.observacoes import detectar_modificadores

        mods = detectar_modificadores(doc)
        assert any('muito' in m and 'quente' in m for m in mods)

    def test_modificador_sem_intensificador(self):
        """Texto sem intensificador nao deve detectar modificadores."""
        doc = _processar('hamburguer simples')
        from src.extratores.observacoes import detectar_modificadores

        mods = detectar_modificadores(doc)
        assert len(mods) == 0

    def test_modificador_mega(self):
        """'mega gelado' deve ser detectado."""
        doc = _processar('suco mega gelado')
        from src.extratores.observacoes import detectar_modificadores

        mods = detectar_modificadores(doc)
        assert any('mega' in m for m in mods)
