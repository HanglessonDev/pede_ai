"""Testes para desambiguacao QTD vs VARIANTE — Fase 2.1.

Cada bug foi identificado no EXTRATOR_DESIGN.md e deve ser testado
ANTES de qualquer alteracao no _extrair_spacy().
"""


from src.extratores import extrair


class TestDesambiguacaoQtdVariante:
    """Desambiguacao contextual de NUM_PENDING em _extrair_spacy()."""

    def test_bug2_qtd_antes_de_item_com_variante_numerica(self):
        """'2 coca 600ml' — qtd=2, variante='600ml'.

        O numero '2' antes do item deve ser quantidade.
        '600ml' deve ser variante, nao quantidade.
        """
        result = extrair('2 coca 600ml')
        assert len(result) == 1
        assert result[0]['quantidade'] == 2
        assert result[0]['variante'] == '600ml'

    def test_bug3_qtd_antes_de_item_com_variante_textual(self):
        """'2 hamburguer duplo' — qtd=2, variante='duplo'.

        O numero '2' antes do item deve ser quantidade.
        'duplo' deve ser variante do hamburguer.
        """
        result = extrair('2 hamburguer duplo')
        assert len(result) == 1
        assert result[0]['quantidade'] == 2
        assert result[0]['variante'] == 'duplo'

    def test_bug4_meio_hamburguer(self):
        """'meio hamburguer' — qtd=0.5.

        'meio' deve ser interpretado como fracao 0.5, nao como quantidade 1.
        """
        result = extrair('meio hamburguer')
        assert len(result) == 1
        assert result[0]['quantidade'] == 0.5

    def test_qtd_depois_do_item_sem_unidade(self):
        """'hamburguer 2' — qtd=2 associado ao hamburguer.

        Numero apos o item deve atualizar a quantidade do item atual,
        nao ficar pendente para o proximo item.
        """
        result = extrair('hamburguer 2')
        assert len(result) == 1
        assert result[0]['quantidade'] == 2

    def test_qtd_nao_vaza_entre_itens(self):
        """'2 hamburguer e coca dupla' — hamburguer qtd=2, coca qtd=1.

        A quantidade pendente deve ser consumida pelo primeiro item
        e resetada para 1, nao vazando para itens seguintes.
        """
        result = extrair('2 hamburguer e coca dupla')
        assert len(result) == 2
        # Primeiro item: hamburguer com qtd=2
        assert result[0]['quantidade'] == 2
        # Segundo item: coca com qtd=1 (default, nao 2)
        assert result[1]['quantidade'] == 1

    def test_variante_ml_sem_espaco(self):
        """Variante extraida deve ser '600ml', nao '600 ml'.

        Quando um numero e seguido de 'ml' ou 'litro', a variante
        deve ser concatenada sem espaco.
        """
        result = extrair('coca 600ml')
        assert len(result) == 1
        assert result[0]['variante'] == '600ml'

    def test_tres_hamburguer(self):
        """'tres hamburguer' — qtd=3.

        Numero por extenso antes do item deve ser quantidade.
        """
        result = extrair('tres hamburguer')
        assert len(result) == 1
        assert result[0]['quantidade'] == 3
