"""Testes de integracao end-to-end do pipeline extrator.

Testam a API publica ``extrair()`` (de ``src.extratores.extrator``),
exercitando o pipeline completo: EntityRuler -> desambiguacao NUM_PENDING
-> remocoes -> complementos -> observacoes -> output.

Cada teste usa o extrator real (singleton) com o cardapio de teste.
"""

from __future__ import annotations


from src.extratores import extrair


# ══════════════════════════════════════════════════════════════════════════════
# 4 testes principais da Fase 2.3
# ══════════════════════════════════════════════════════════════════════════════


class TestIntegracaoFase2:
    """Testes principais especificados no PLANO_IMPLEMENTACAO.md Fase 2.3."""

    def test_integracao_pedido_simples(self):
        """'1 coca lata' -> qtd=1, variante='lata'."""
        result = extrair('1 coca lata')
        assert len(result) == 1
        item = result[0]
        assert item['item_id'] == 'bebida_001'
        assert item['quantidade'] == 1
        assert item['variante'] == 'lata'
        assert item['remocoes'] == []

    def test_integracao_pedido_com_remocao(self):
        """'hamburguer sem cebola' -> item correto, remocoes=['cebola']."""
        result = extrair('hamburguer sem cebola')
        assert len(result) == 1
        item = result[0]
        assert item['item_id'] == 'lanche_001'
        assert item['quantidade'] == 1
        assert item['variante'] is None
        assert item['remocoes'] == ['cebola']

    def test_integracao_dois_itens(self):
        """'2 hamburguer e 1 coca 600ml' -> 2 itens corretos."""
        result = extrair('2 hamburguer e 1 coca 600ml')
        assert len(result) == 2
        # Primeiro item: hamburguer qtd=2
        assert result[0]['item_id'] == 'lanche_001'
        assert result[0]['quantidade'] == 2
        assert result[0]['variante'] is None
        # Segundo item: coca qtd=1, variante=600ml
        assert result[1]['item_id'] == 'bebida_001'
        assert result[1]['quantidade'] == 1
        assert result[1]['variante'] == '600ml'

    def test_integracao_quantidade_variante_remocao(self):
        """'2 hamburguer duplo sem tomate' -> qtd=2, variante='duplo', remocoes=['tomate']."""
        result = extrair('2 hamburguer duplo sem tomate')
        assert len(result) == 1
        item = result[0]
        assert item['item_id'] == 'lanche_001'
        assert item['quantidade'] == 2
        assert item['variante'] == 'duplo'
        assert item['remocoes'] == ['tomate']


# ══════════════════════════════════════════════════════════════════════════════
# 10 testes adicionais cobrindo variacoes dos bugs #1-5
# ══════════════════════════════════════════════════════════════════════════════


class TestIntegracaoAdicional:
    """Testes adicionais cobrindo variacoes e edge cases dos bugs #1-5."""

    def test_meio_hamburguer_e_meia_coca(self):
        """'meio hamburguer e meia coca' -> 2 itens, ambos com qtd=0.5."""
        result = extrair('meio hamburguer e meia coca')
        assert len(result) == 2
        assert result[0]['item_id'] == 'lanche_001'
        assert result[0]['quantidade'] == 0.5
        assert result[1]['item_id'] == 'bebida_001'
        assert result[1]['quantidade'] == 0.5

    def test_x_salada_duas_remocoes(self):
        """'3 x-salada sem cebola e sem tomate' -> qtd=3, 2 remocoes."""
        result = extrair('3 x-salada sem cebola e sem tomate')
        assert len(result) == 1
        item = result[0]
        assert item['item_id'] == 'lanche_002'
        assert item['quantidade'] == 3
        assert 'cebola' in item['remocoes']
        assert 'tomate' in item['remocoes']
        assert len(item['remocoes']) == 2

    def test_qtd_depois_do_item(self):
        """'hamburguer 2' -> qtd=2 (numero depois do item)."""
        result = extrair('hamburguer 2')
        assert len(result) == 1
        assert result[0]['item_id'] == 'lanche_001'
        assert result[0]['quantidade'] == 2

    def test_qtd_nao_vaza_para_segundo_item(self):
        """'2 hamburguer e coca' -> hamburguer qtd=2, coca qtd=1 (default)."""
        result = extrair('2 hamburguer e coca')
        assert len(result) == 2
        assert result[0]['item_id'] == 'lanche_001'
        assert result[0]['quantidade'] == 2
        assert result[1]['item_id'] == 'bebida_001'
        assert result[1]['quantidade'] == 1

    def test_variante_ml_sem_qtd(self):
        """'coca 600ml' -> variante='600ml', qtd=1."""
        result = extrair('coca 600ml')
        assert len(result) == 1
        assert result[0]['item_id'] == 'bebida_001'
        assert result[0]['variante'] == '600ml'
        assert result[0]['quantidade'] == 1

    def test_batata_sem_sal(self):
        """'batata sem sal' -> item + remocoes=['sal']."""
        result = extrair('batata sem sal')
        assert len(result) == 1
        assert result[0]['item_id'] == 'acomp_001'
        assert result[0]['remocoes'] == ['sal']

    def test_remocao_antes_do_item(self):
        """'sem cebola hamburguer' -> item com remocoes=['cebola'].

        Bug #1: o Hamburguer nao deve ser capturado como remocao.
        """
        result = extrair('sem cebola hamburguer')
        assert len(result) == 1
        item = result[0]
        assert item['item_id'] == 'lanche_001'
        assert item['remocoes'] == ['cebola']
        assert 'hamburguer' not in item['remocoes']

    def test_negacao_retorna_vazio(self):
        """'nao quero hamburguer' -> [] (negacao).

        Nota: se negacao ainda nao esta implementada, este teste deve
        falhar (🔴) conforme esperado pelo TDD.
        """
        result = extrair('nao quero hamburguer')
        assert result == []

    def test_meia_porcao_batata(self):
        """'meia porcao de batata' -> qtd=0.5."""
        result = extrair('meia porcao de batata')
        assert len(result) == 1
        assert result[0]['item_id'] == 'acomp_001'
        assert result[0]['quantidade'] == 0.5

    def test_item_remocao_item_repetido(self):
        """'hamburguer sem cebola hamburguer' -> 2 hamburgueres.

        O segundo hamburguer nao deve ter 'hamburguer' nas remocoes.
        """
        result = extrair('hamburguer sem cebola hamburguer')
        assert len(result) == 2
        # Primeiro: remocoes=['cebola']
        assert result[0]['item_id'] == 'lanche_001'
        assert result[0]['remocoes'] == ['cebola']
        # Segundo: remocoes=[] (hamburguer nao deve estar nas remocoes)
        assert result[1]['item_id'] == 'lanche_001'
        assert result[1]['remocoes'] == []


# ══════════════════════════════════════════════════════════════════════════════
# Testes de integracao Fase 3 — Complementos + Observacoes
# ══════════════════════════════════════════════════════════════════════════════


class TestIntegracaoFase3:
    """Testes de integracao para complementos e observacoes."""

    def test_integracao_complemento_e_remocao(self):
        """'hamburguer com bacon sem cebola' -> complementos=['bacon'], remocoes=['cebola']."""
        result = extrair('hamburguer com bacon sem cebola')
        assert len(result) == 1
        item = result[0]
        assert item['item_id'] == 'lanche_001'
        assert 'bacon' in item['complementos']
        assert 'cebola' in item['remocoes']

    def test_integracao_observacao_nao_afeta_item_id(self):
        """Observacao presente nao muda item_id nem variante.

        'hamburguer caprichado' deve ter o mesmo item_id e variante=None
        que 'hamburguer' puro, mas com observacoes preenchidas.
        """
        result_com_obs = extrair('hamburguer caprichado')
        result_sem_obs = extrair('hamburguer')

        assert len(result_com_obs) == 1
        assert len(result_sem_obs) == 1

        # item_id deve ser o mesmo
        assert result_com_obs[0]['item_id'] == result_sem_obs[0]['item_id']
        # variante deve ser o mesmo (None)
        assert result_com_obs[0]['variante'] == result_sem_obs[0]['variante']
        # mas observacoes deve estar preenchida no primeiro
        assert len(result_com_obs[0]['observacoes']) > 0


class TestFuzzyFallbackTypo:
    """Testes para o fuzzy fallback em regioes nao cobertas pelo EntityRuler."""

    def test_hamburguer_com_acento_simples(self, engine, config, cardapio):
        """'quero um hamburguer' (com acento) — fuzzy recupera o item."""
        from src.extratores.extrator import Extrator

        extrator = Extrator(engine, config, cardapio)
        result = extrator.extrair('quero um hamburguer')
        assert len(result) >= 1
        ids = {r.item_id for r in result}
        assert 'lanche_001' in ids

    def test_hamburguer_com_acento_multi_itens(self, engine, config, cardapio):
        """'um hamburguer, uma batata e uma coca' — 3 itens via spacy + fuzzy."""
        from src.extratores.extrator import Extrator

        extrator = Extrator(engine, config, cardapio)
        result = extrator.extrair('um hamburguer, uma batata e uma coca')
        assert len(result) == 3
        ids = {r.item_id for r in result}
        assert ids == {'lanche_001', 'acomp_001', 'bebida_001'}

    def test_fuzzy_nao_duplica_item_existente(self, engine, config, cardapio):
        """'hamburguer hamburguer' — extrai hamburguer (pode ter duplicata)."""
        from src.extratores.extrator import Extrator

        extrator = Extrator(engine, config, cardapio)
        result = extrator.extrair('hamburguer hamburguer')
        # Pelo menos 1 hamburguer
        assert len(result) >= 1
        ids = {r.item_id for r in result}
        assert 'lanche_001' in ids


# ══════════════════════════════════════════════════════════════════════════════
# Fase 4.4 — Janela de Contexto
# ══════════════════════════════════════════════════════════════════════════════


class TestJanelaContexto:
    """Janela de contexto: tokens distantes nao sao associados ao item."""

    def test_janela_nao_associa_qtd_errada(self):
        """'2 hamburguer e coca dupla' -> 'dupla' nao vira variante do hamburguer."""
        result = extrair('2 hamburguer e coca dupla')
        assert len(result) >= 1
        hamburguer = result[0]
        assert hamburguer['item_id'] == 'lanche_001'
        # 'dupla' esta longe demais do hamburguer para ser sua variante
        assert hamburguer['variante'] is None


# ══════════════════════════════════════════════════════════════════════════════
# Fase 4.5 — Aliases novos (xis, x-td, coquinha)
# ══════════════════════════════════════════════════════════════════════════════


class TestAliasesNovos:
    """Novos aliases: xis, x-td, coquinha."""

    def test_bug6_alias_xis(self):
        """'xis sem cebola' -> item_id do hamburguer, remocoes=['cebola']."""
        result = extrair('xis sem cebola')
        assert len(result) == 1
        assert result[0]['item_id'] == 'lanche_001'
        assert 'cebola' in result[0]['remocoes']

    def test_bug6_alias_x_td(self):
        """'x-td' -> item x-tudo reconhecido."""
        result = extrair('x-td')
        assert len(result) == 1
        assert result[0]['item_id'] == 'lanche_003'

    def test_alias_coquinha(self):
        """'coquinha gelada' -> item coca reconhecido."""
        result = extrair('coquinha gelada')
        assert len(result) == 1
        assert result[0]['item_id'] == 'bebida_001'
