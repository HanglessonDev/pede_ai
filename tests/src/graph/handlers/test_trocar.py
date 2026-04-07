"""Testes para handler de troca de variantes do carrinho."""

import pytest
from unittest.mock import patch

from src.graph.handlers.troca_handler import processar_troca, ResultadoTrocar


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def carrinho_vazio():
    """Carrinho vazio."""
    return []


@pytest.fixture
def carrinho_um_item():
    """Carrinho com 1 hamburguer simples."""
    return [
        {
            'item_id': 'lanche_001',
            'quantidade': 1,
            'preco': 1500,
            'variante': 'simples',
        },
    ]


@pytest.fixture
def carrinho_multiplos():
    """Carrinho com hamburguer + coca-cola."""
    return [
        {
            'item_id': 'lanche_001',
            'quantidade': 1,
            'preco': 1500,
            'variante': 'simples',
        },
        {
            'item_id': 'bebida_001',
            'quantidade': 1,
            'preco': 500,
            'variante': 'lata',
        },
    ]


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE CARRINHO VAZIO
# ══════════════════════════════════════════════════════════════════════════════


class TestCarrinhoVazio:
    """Testes para troca com carrinho vazio."""

    def test_trocar_carrinho_vazio(self, carrinho_vazio):
        """Carrinho vazio deve retornar mensagem de erro."""
        result = processar_troca(carrinho_vazio, 'muda pra duplo')
        assert result.resposta == 'Não há pedido para trocar.'
        assert result.modo == 'ocioso'
        assert result.carrinho == []


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE CASO VAZIO (sem informacao util)
# ══════════════════════════════════════════════════════════════════════════════


class TestCasoVazio:
    """Testes para mensagens sem informacao extraivel."""

    def test_trocar_sem_informacao_util(self, carrinho_um_item):
        """Mensagem sem entidades deve retornar 'Nao entendi'."""
        with patch(
            'src.graph.handlers.troca_handler.extrair_itens_troca',
            return_value={
                'caso': 'vazio',
                'item_original': None,
                'variante_nova': None,
            },
        ):
            result = processar_troca(carrinho_um_item, 'nao sei la')
            assert 'Não entendi' in result.resposta
            assert result.carrinho == carrinho_um_item


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE CASO A (2+ ITEMs — troca item por item)
# ══════════════════════════════════════════════════════════════════════════════


class TestCasoA:
    """Testes para caso A: 2+ ITEMs (troca item por item — nao suportado no MVP)."""

    def test_trocar_caso_a_erro_informativo(self, carrinho_multiplos):
        """2+ ITEMs na mensagem deve retornar erro informativo (MVP)."""
        with patch(
            'src.graph.handlers.troca_handler.extrair_itens_troca',
            return_value={
                'caso': 'A',
                'item_original': None,
                'variante_nova': None,
            },
        ):
            result = processar_troca(carrinho_multiplos, 'troca coca por hamburguer')
            assert 'só consigo trocar variantes' in result.resposta
            assert len(result.carrinho) == 2


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE CASO B (1 ITEM + variante)
# ══════════════════════════════════════════════════════════════════════════════


class TestCasoB:
    """Testes para caso B: 1 ITEM + variante."""

    def test_item_com_variante_sucesso(self, carrinho_um_item):
        """Item no carrinho com variante nova deve trocar."""
        with patch(
            'src.graph.handlers.troca_handler.extrair_itens_troca',
            return_value={
                'caso': 'B',
                'item_original': {
                    'item_id': 'lanche_001',
                    'nome': 'Hamburguer',
                    'indices': [0],
                },
                'variante_nova': 'duplo',
            },
        ):
            result = processar_troca(carrinho_um_item, 'muda o hamburguer pra duplo')
            assert result.carrinho[0]['variante'] == 'duplo'
            assert result.carrinho[0]['preco'] > 0
            assert result.modo == 'coletando'

    def test_item_nao_encontrado(self, carrinho_um_item):
        """Item mencionado nao esta no carrinho deve retornar erro."""
        with patch(
            'src.graph.handlers.troca_handler.extrair_itens_troca',
            return_value={
                'caso': 'B',
                'item_original': None,
                'variante_nova': 'lata',
            },
        ):
            result = processar_troca(carrinho_um_item, 'muda a coca pra lata')
            assert 'não está no seu carrinho' in result.resposta
            assert result.carrinho == carrinho_um_item

    def test_sem_variante_especificada(self, carrinho_um_item):
        """Item sem variante deve pedir esclarecimento."""
        with patch(
            'src.graph.handlers.troca_handler.extrair_itens_troca',
            return_value={
                'caso': 'B',
                'item_original': {
                    'item_id': 'lanche_001',
                    'nome': 'Hamburguer',
                    'indices': [0],
                },
                'variante_nova': None,
            },
        ):
            result = processar_troca(carrinho_um_item, 'muda o hamburguer')
            assert 'o quê' in result.resposta
            assert result.carrinho == carrinho_um_item

    def test_variante_inexistente(self, carrinho_um_item):
        """Variante que nao existe para o item deve retornar erro."""
        with patch(
            'src.graph.handlers.troca_handler.extrair_itens_troca',
            return_value={
                'caso': 'B',
                'item_original': {
                    'item_id': 'lanche_001',
                    'nome': 'Hamburguer',
                    'indices': [0],
                },
                'variante_nova': 'gigante',
            },
        ):
            result = processar_troca(carrinho_um_item, 'muda pra gigante')
            assert 'não tem opção' in result.resposta
            assert result.carrinho == carrinho_um_item

    def test_preserva_dados_item(self):
        """Item deve manter dados apos troca."""
        carrinho = [
            {
                'item_id': 'lanche_001',
                'quantidade': 1,
                'preco': 1500,
                'variante': 'simples',
            },
        ]
        with patch(
            'src.graph.handlers.troca_handler.extrair_itens_troca',
            return_value={
                'caso': 'B',
                'item_original': {
                    'item_id': 'lanche_001',
                    'nome': 'Hamburguer',
                    'indices': [0],
                },
                'variante_nova': 'duplo',
            },
        ):
            result = processar_troca(carrinho, 'muda pra duplo')
            assert result.carrinho[0]['variante'] == 'duplo'
            assert result.carrinho[0]['quantidade'] == 1
            assert result.modo == 'coletando'


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE CASO C (variante isolada sem item)
# ══════════════════════════════════════════════════════════════════════════════


class TestCasoC:
    """Testes para caso C: variante isolada sem item especificado."""

    def test_variante_isolada_um_compativel(self, carrinho_multiplos):
        """Variante que so 1 item aceita deve trocar direto."""
        with patch(
            'src.graph.handlers.troca_handler.extrair_itens_troca',
            return_value={
                'caso': 'C',
                'item_original': None,
                'variante_nova': 'triplo',
            },
        ):
            result = processar_troca(carrinho_multiplos, 'muda pra triplo')
            assert result.carrinho[0]['variante'] == 'triplo'
            assert result.carrinho[1]['variante'] == 'lata'
            assert result.modo == 'coletando'

    def test_variante_isolada_ambiguidade(self):
        """Variante que 2+ itens aceitam deve pedir esclarecimento."""
        carrinho_2_bebidas = [
            {
                'item_id': 'bebida_001',
                'quantidade': 1,
                'preco': 500,
                'variante': 'lata',
            },
            {
                'item_id': 'bebida_002',
                'quantidade': 1,
                'preco': 350,
                'variante': 'lata',
            },
        ]
        with patch(
            'src.graph.handlers.troca_handler.extrair_itens_troca',
            return_value={
                'caso': 'C',
                'item_original': None,
                'variante_nova': 'lata',
            },
        ):
            result = processar_troca(carrinho_2_bebidas, 'muda pra lata')
            assert 'Qual item' in result.resposta
            assert result.modo == 'clarificando'
            assert result.carrinho == carrinho_2_bebidas

    def test_caso_c_itens_duplicados_troca_todos(self):
        """2+ itens com mesmo item_id e mesma variante válida — troca todos."""
        carrinho_2_iguais = [
            {
                'item_id': 'lanche_001',
                'quantidade': 1,
                'preco': 1500,
                'variante': 'simples',
            },
            {
                'item_id': 'lanche_001',
                'quantidade': 1,
                'preco': 1500,
                'variante': 'simples',
            },
        ]
        with patch(
            'src.graph.handlers.troca_handler.extrair_itens_troca',
            return_value={
                'caso': 'C',
                'item_original': None,
                'variante_nova': 'duplo',
            },
        ):
            result = processar_troca(carrinho_2_iguais, 'muda pra duplo')
            # Trocou em ambos
            assert result.carrinho[0]['variante'] == 'duplo'
            assert result.carrinho[1]['variante'] == 'duplo'
            assert result.carrinho[0]['preco'] == 2000
            assert result.carrinho[1]['preco'] == 2000
            assert result.modo == 'coletando'

    def test_caso_c_itens_diferentes_mesma_variante_valida(self):
        """2 itens diferentes que aceitam a variante — deve clarificar."""
        # acomp_001 (Batata) e acomp_001 repetido com mesmo item_id
        # Para itens DIFERENTES, preciso 2 item_ids que aceitam a mesma variante
        # lanche_001 aceita duplo, acomp_001 NÃO aceita duplo
        # Uso 2 bebidas que aceitam 'lata' — mas são item_ids diferentes
        carrinho_2_itens_diferentes = [
            {
                'item_id': 'bebida_001',
                'quantidade': 1,
                'preco': 500,
                'variante': 'lata',
            },
            {
                'item_id': 'bebida_002',
                'quantidade': 1,
                'preco': 350,
                'variante': 'lata',
            },
        ]
        with patch(
            'src.graph.handlers.troca_handler.extrair_itens_troca',
            return_value={
                'caso': 'C',
                'item_original': None,
                'variante_nova': 'lata',
            },
        ):
            result = processar_troca(carrinho_2_itens_diferentes, 'muda pra lata')
            assert 'Qual item' in result.resposta
            assert result.modo == 'clarificando'
            assert result.carrinho == carrinho_2_itens_diferentes

    def test_variante_isolada_fallback_um_item(self, carrinho_um_item):
        """Fallback: 1 item no carrinho que aceita variante."""
        with patch(
            'src.graph.handlers.troca_handler.extrair_itens_troca',
            return_value={
                'caso': 'C',
                'item_original': None,
                'variante_nova': 'duplo',
            },
        ):
            result = processar_troca(carrinho_um_item, 'muda pra duplo')
            assert result.carrinho[0]['variante'] == 'duplo'
            assert result.carrinho[0]['preco'] == 2000
            assert result.modo == 'coletando'

    def test_variante_isolada_sem_compatibilidade_multiplos(self, carrinho_multiplos):
        """Nenhum item aceita a variante deve retornar erro."""
        with patch(
            'src.graph.handlers.troca_handler.extrair_itens_troca',
            return_value={
                'caso': 'C',
                'item_original': None,
                'variante_nova': 'gigante',
            },
        ):
            result = processar_troca(carrinho_multiplos, 'muda pra gigante')
            assert 'Nenhum item no seu carrinho aceita' in result.resposta
            assert result.carrinho == carrinho_multiplos

    def test_variante_isolada_um_item_nao_aceita(self, carrinho_um_item):
        """Variante que o unico item nao aceita deve retornar erro."""
        with patch(
            'src.graph.handlers.troca_handler.extrair_itens_troca',
            return_value={
                'caso': 'C',
                'item_original': None,
                'variante_nova': 'lata',
            },
        ):
            result = processar_troca(carrinho_um_item, 'muda pra lata')
            assert 'não tem opção' in result.resposta
            assert result.carrinho == carrinho_um_item


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE ResultadoTrocar
# ══════════════════════════════════════════════════════════════════════════════


class TestResultadoTrocar:
    """Testes para o dataclass ResultadoTrocar."""

    def test_to_dict_contem_chaves(self):
        """to_dict deve conter todas as chaves esperadas."""
        result = ResultadoTrocar(
            carrinho=[{'item_id': 'lanche_001', 'preco': 1500}],
            resposta='1x Hamburguer — R$ 15.00',
            modo='coletando',
        )
        d = result.to_dict()
        assert 'carrinho' in d
        assert 'resposta' in d
        assert 'modo' in d

    def test_to_dict_valores_corretos(self):
        """to_dict deve mapear valores corretamente."""
        carrinho = [{'item_id': 'lanche_001', 'preco': 1500}]
        result = ResultadoTrocar(
            carrinho=carrinho,
            resposta='1x Hamburguer — R$ 15.00',
            modo='coletando',
        )
        d = result.to_dict()
        assert d['carrinho'] == carrinho
        assert d['resposta'] == '1x Hamburguer — R$ 15.00'
        assert d['modo'] == 'coletando'
