"""Testes para deteco de complementos (Camada 6).

Testam detectar_complementos() do modulo src.extratores.complementos.
"""

from __future__ import annotations


from src.extratores.complementos import detectar_complementos
from src.extratores.config import get_extrator_config
from src.config import get_cardapio


def _processar(texto: str):
    """Processa texto com o NLP engine real."""
    from src.extratores.nlp_engine import NlpEngine

    config = get_extrator_config()
    cardapio = get_cardapio()
    engine = NlpEngine(config, cardapio)
    return engine.processar(texto)


class TestDetectarComplementos:
    """Testes para detectar_complementos()."""

    def test_complemento_com_direto(self):
        """'hamburguer com bacon' -> complementos=['bacon']."""
        doc = _processar('hamburguer com bacon')
        config = get_extrator_config()
        cardapio = get_cardapio()
        result = detectar_complementos(doc, 'lanche_001', cardapio, config)
        assert 'bacon' in result
        assert len(result) == 1

    def test_complemento_com_artigo(self):
        """'hamburguer com o bacon' -> complementos=['bacon'] (artigo nao bloqueia)."""
        doc = _processar('hamburguer com o bacon')
        config = get_extrator_config()
        cardapio = get_cardapio()
        result = detectar_complementos(doc, 'lanche_001', cardapio, config)
        assert 'bacon' in result

    def test_complemento_padrao_inverso(self):
        """'hamburguer bacon extra' -> complementos=['bacon']."""
        doc = _processar('hamburguer bacon extra')
        config = get_extrator_config()
        cardapio = get_cardapio()
        result = detectar_complementos(doc, 'lanche_001', cardapio, config)
        assert 'bacon' in result

    def test_complemento_invalido_ignorado(self):
        """Complemento nao esta no cardapio -> complementos=[]."""
        doc = _processar('hamburguer com presunto')
        config = get_extrator_config()
        cardapio = get_cardapio()
        result = detectar_complementos(doc, 'lanche_001', cardapio, config)
        assert result == []

    def test_complemento_break_dentro_do_if(self):
        """'hamburguer com alface bacon' onde alface nao e complemento mas bacon e.

        Deve capturar bacon mesmo que alface (que nao e complemento valido)
        apareca primeiro. O break so deve acontecer quando encontrar uma
        palavra de parada, nao quando o token nao for complemento valido.
        """
        doc = _processar('hamburguer com alface bacon')
        config = get_extrator_config()
        cardapio = get_cardapio()
        result = detectar_complementos(doc, 'lanche_001', cardapio, config)
        assert 'bacon' in result
        assert 'alface' not in result

    def test_complemento_adicional_de(self):
        """'x-salada adicional de queijo' -> complementos=['queijo']."""
        doc = _processar('x-salada adicional de queijo')
        config = get_extrator_config()
        cardapio = get_cardapio()
        result = detectar_complementos(doc, 'lanche_002', cardapio, config)
        assert 'queijo' in result
        assert len(result) == 1

    def test_complemento_com_longe(self):
        """'hamburguer com uma dose de bacon' -> complementos=['bacon']."""
        doc = _processar('hamburguer com uma dose de bacon')
        config = get_extrator_config()
        cardapio = get_cardapio()
        result = detectar_complementos(doc, 'lanche_001', cardapio, config)
        assert 'bacon' in result

    def test_complemento_nao_para_em_conectivo(self):
        """'hamburguer com bacon e ovo' -> complementos=['bacon', 'ovo']."""
        doc = _processar('hamburguer com bacon e ovo')
        config = get_extrator_config()
        cardapio = get_cardapio()
        result = detectar_complementos(doc, 'lanche_001', cardapio, config)
        assert 'bacon' in result
        assert 'ovo' in result
