"""Testes para modelos de dados — ItemExtraido com novos campos."""

from dataclasses import asdict


from src.extratores.modelos import ItemExtraido


class TestItemExtraidoNovosCampos:
    """ItemExtraido deve suportar quantidade float e novos campos com defaults."""

    def test_item_extraido_quantidade_float(self):
        """Criar ItemExtraido com quantidade=0.5 nao deve levantar TypeError."""
        item = ItemExtraido(
            item_id='lanche_001',
            quantidade=0.5,
            variante=None,
            remocoes=[],
        )
        assert item.quantidade == 0.5

    def test_item_extraido_campos_novos_com_defaults(self):
        """Criar sem passar complementos, observacoes, confianca, fonte — defaults corretos."""
        item = ItemExtraido(
            item_id='lanche_001',
            quantidade=1,
            variante=None,
            remocoes=[],
        )
        assert item.complementos == []
        assert item.observacoes == []
        assert item.confianca == 1.0
        assert item.fonte == 'ruler'

    def test_item_extraido_asdict_inclui_novos_campos(self):
        """asdict(item) deve ter chaves complementos, observacoes, confianca, fonte."""
        item = ItemExtraido(
            item_id='lanche_001',
            quantidade=1,
            variante=None,
            remocoes=[],
        )
        d = asdict(item)
        assert 'complementos' in d
        assert 'observacoes' in d
        assert 'confianca' in d
        assert 'fonte' in d
        assert d['complementos'] == []
        assert d['observacoes'] == []
        assert d['confianca'] == 1.0
        assert d['fonte'] == 'ruler'

    def test_compatibilidade_retroativa(self):
        """Consumidor usando item.get('complementos', []) nao levanta excecao."""
        item = ItemExtraido(
            item_id='lanche_001',
            quantidade=1,
            variante=None,
            remocoes=[],
        )
        d = asdict(item)
        # Simula consumidor antigo que acessa via dict.get com default
        complementos = d.get('complementos', [])
        assert complementos == []
        observacoes = d.get('observacoes', [])
        assert observacoes == []
