"""
Testes de alta qualidade para handlers/clarificacao.py.

Cobertura:
- Variante válida → carrinho + avançar fila
- Variante inválida → re-prompt (até 3 tentativas)
- 3 tentativas falhas → remover item, continuar
- Fila vazia → voltar ao início
- Múltiplos itens na fila
"""

import pytest

from src.graph.handlers.clarificacao import (
    MAX_TENTATIVAS,
    ResultadoClarificacao,
    clarificar,
    _proxima_clarificacao,
)
from src.graph.handlers.carrinho import Carrinho


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def item_hamburguer():
    """Item de hambúrguer para fila de clarificação."""
    return {
        'item': {
            'item_id': 'lanche_001',
            'quantidade': 1,
            'variante': None,
            'remocoes': [],
        },
        'item_id': 'lanche_001',
        'nome': 'Hambúrguer',
        'campo': 'variante',
        'opcoes': ['simples', 'duplo', 'triplo'],
    }


@pytest.fixture
def item_batata():
    """Item de batata para fila de clarificação."""
    return {
        'item': {
            'item_id': 'acomp_001',
            'quantidade': 1,
            'variante': None,
            'remocoes': [],
        },
        'item_id': 'acomp_001',
        'nome': 'Batata Frita',
        'campo': 'variante',
        'opcoes': ['pequena', 'media', 'grande'],
    }


@pytest.fixture
def fila_vazia():
    """Fila de clarificação vazia."""
    return []


@pytest.fixture
def fila_um_item(item_hamburguer):
    """Fila com um item."""
    return [item_hamburguer]


@pytest.fixture
def fila_multiplos_itens(item_hamburguer, item_batata):
    """Fila com múltiplos itens."""
    return [item_hamburguer, item_batata]


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE CONSTANTES
# ══════════════════════════════════════════════════════════════════════════════


class TestConstantes:
    """Testes de constantes do módulo."""

    def test_max_tentativas_e_tres(self):
        """Máximo de tentativas deve ser 3."""
        assert MAX_TENTATIVAS == 3


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE FUNÇÕES AUXILIARES
# ══════════════════════════════════════════════════════════════════════════════


class TestProximaClarificacao:
    """Testes para _proxima_clarificacao()."""

    def test_gera_prompt_com_nome_e_opcoes(self, item_hamburguer):
        """Deve gerar prompt com nome e opções."""
        fila = [item_hamburguer]
        result = _proxima_clarificacao(fila)
        assert 'Hambúrguer' in result
        assert 'simples' in result
        assert 'duplo' in result
        assert 'triplo' in result

    def test_opcoes_separadas_por_virgula(self, item_batata):
        """Opções devem estar separadas por vírgula."""
        fila = [item_batata]
        result = _proxima_clarificacao(fila)
        assert 'pequena, media, grande' in result


class TestFormatarCarrinho:
    """Testes para Carrinho.formatar()."""

    def test_formata_itens_com_preco(self):
        """Deve formatar itens com quantidade, nome e preco."""
        carrinho = Carrinho.from_state_dicts([
            {'item_id': 'lanche_001', 'quantidade': 2, 'preco': 3000, 'variante': None},
        ])
        result = carrinho.formatar()
        assert '2x' in result
        assert '60.00' in result

    def test_multiplos_itens(self):
        """Deve formatar multiplos itens em linhas separadas."""
        carrinho = Carrinho.from_state_dicts([
            {'item_id': 'lanche_001', 'quantidade': 1, 'preco': 1500, 'variante': None},
            {'item_id': 'acomp_001', 'quantidade': 2, 'preco': 2000, 'variante': None},
        ])
        result = carrinho.formatar()
        linhas = result.split('\n')
        # Inclui linha de Total
        assert len(linhas) >= 2

    def test_carrinho_vazio_retorna_mensagem(self):
        """Carrinho vazio deve retornar mensagem."""
        carrinho = Carrinho()
        result = carrinho.formatar()
        assert 'vazio' in result.lower()


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE clarificar() - FILA VAZIA
# ══════════════════════════════════════════════════════════════════════════════


class TestClarificarFilaVazia:
    """Testes para clarificar() com fila vazia."""

    def test_fila_vazia_retorna_inicio(self, fila_vazia):
        """Fila vazia deve retornar etapa inicio."""
        result = clarificar(fila_vazia, '', 0)
        assert result.etapa == 'inicio'
        assert result.resposta == ''


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE clarificar() - VARIANTE VÁLIDA
# ══════════════════════════════════════════════════════════════════════════════


class TestClarificarVarianteValida:
    """Testes para clarificar() com variante válida."""

    def test_adiciona_ao_carrinho(self, fila_um_item):
        """Variante válida deve adicionar item ao carrinho."""
        result = clarificar(fila_um_item, 'duplo', 0)
        assert result.tipo == 'sucesso'
        assert len(result.carrinho) == 1
        assert result.carrinho[0]['preco'] > 0

    def test_remove_item_da_fila(self, fila_um_item):
        """Item processado deve ser removido da fila."""
        result = clarificar(fila_um_item, 'duplo', 0)
        assert len(result.fila) == 0

    def reseta_tentativas(self, fila_um_item):
        """Tentativas devem ser resetadas após sucesso."""
        result = clarificar(fila_um_item, 'duplo', 2)
        assert result.tentativas == 0

    def test_avanca_para_proximo_item(self, fila_multiplos_itens):
        """Com múltiplos itens, deve avançar para o próximo."""
        result = clarificar(fila_multiplos_itens, 'duplo', 0)
        assert len(result.fila) == 1
        assert result.fila[0]['item_id'] == 'acomp_001'
        assert result.etapa == 'clarificando_variante'
        assert 'Batata Frita' in result.resposta

    def test_volta_inicio_se_fila_vazia(self, fila_um_item):
        """Se fila fica vazia, deve voltar ao início."""
        result = clarificar(fila_um_item, 'simples', 0)
        assert result.etapa == 'inicio'

    def test_resposta_contem_carrinho(self, fila_um_item):
        """Quando fila esvazia, resposta deve conter itens do carrinho."""
        result = clarificar(fila_um_item, 'simples', 0)
        assert '1x' in result.resposta


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE clarificar() - VARIANTE INVÁLIDA
# ══════════════════════════════════════════════════════════════════════════════


class TestClarificarVarianteInvalida:
    """Testes para clarificar() com variante inválida."""

    def test_incrementa_tentativas(self, fila_um_item):
        """Variante inválida deve incrementar tentativas."""
        result = clarificar(fila_um_item, 'quadruplo', 0)
        assert result.tentativas == 1

    def test_mantem_item_na_fila(self, fila_um_item):
        """Item deve permanecer na fila."""
        result = clarificar(fila_um_item, 'quadruplo', 0)
        assert len(result.fila) == 1
        assert result.fila[0]['item_id'] == 'lanche_001'

    def test_mantem_etapa_clarificando(self, fila_um_item):
        """Etapa deve permanecer clarificando_variante."""
        result = clarificar(fila_um_item, 'quadruplo', 0)
        assert result.etapa == 'clarificando_variante'

    def test_re_prompt_com_opcoes(self, fila_um_item):
        """Resposta deve conter re-prompt com opções."""
        result = clarificar(fila_um_item, 'quadruplo', 0)
        assert 'disponível' in result.resposta.lower()
        assert 'simples' in result.resposta
        assert 'duplo' in result.resposta

    def test_mensagem_erro_inclui_nome_item(self, fila_um_item):
        """Mensagem de erro deve incluir nome do item."""
        result = clarificar(fila_um_item, 'quadruplo', 0)
        assert 'Hambúrguer' in result.resposta


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE clarificar() - 3 TENTATIVAS FALHAS
# ══════════════════════════════════════════════════════════════════════════════


class TestClarificarTresTentativasFalhas:
    """Testes para clarificar() após 3 tentativas falhas."""

    def test_remove_item_da_fila(self, fila_um_item):
        """Após 3 tentativas, item deve ser removido."""
        result = clarificar(fila_um_item, 'pizza', 2)
        assert len(result.fila) == 0

    def test_reseta_tentativas(self, fila_um_item):
        """Tentativas devem ser resetadas após desistência."""
        result = clarificar(fila_um_item, 'pizza', 2)
        assert result.tentativas == 0

    def test_volta_inicio_se_fila_vazia(self, fila_um_item):
        """Se fila fica vazia, deve voltar ao início."""
        result = clarificar(fila_um_item, 'pizza', 2)
        assert result.etapa == 'inicio'

    def test_avanca_para_proximo_item(self, fila_multiplos_itens):
        """Com múltiplos itens, deve avançar para o próximo."""
        result = clarificar(fila_multiplos_itens, 'pizza', 2)
        assert len(result.fila) == 1
        assert result.fila[0]['item_id'] == 'acomp_001'
        assert result.etapa == 'clarificando_variante'

    def test_resposta_contem_proximo_item(self, fila_multiplos_itens):
        """Resposta deve conter prompt para próximo item."""
        result = clarificar(fila_multiplos_itens, 'pizza', 2)
        assert 'Batata Frita' in result.resposta

    def test_mensagem_fallback_sem_itens(self, fila_um_item):
        """Sem mais itens, deve exibir mensagem de fallback."""
        result = clarificar(fila_um_item, 'pizza', 2)
        assert (
            'consegui' in result.resposta.lower()
            or 'entendi' in result.resposta.lower()
        )


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE EDGE CASES
# ══════════════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Testes de casos de borda."""

    def test_mensagem_vazia_conta_como_invalida(self, fila_um_item):
        """Mensagem vazia deve ser tratada como inválida."""
        result = clarificar(fila_um_item, '', 0)
        assert result.tipo == 'invalida'

    def test_mensagem_somente_espacos_conta_como_invalida(self, fila_um_item):
        """Mensagem com apenas espaços deve ser inválida."""
        result = clarificar(fila_um_item, '   ', 0)
        assert result.tipo == 'invalida'

    def test_segunda_tentativa_invalida(self, fila_um_item):
        """Segunda tentativa inválida deve ter tentativas=2."""
        result = clarificar(fila_um_item, 'xyz', 1)
        assert result.tentativas == 2
        assert result.tipo == 'invalida'

    def test_item_sem_variantes_no_cardapio(self):
        """Item sem variantes deve ser tratado como inválido (extrator retorna None)."""
        item = {
            'item': {
                'item_id': 'lanche_002',
                'quantidade': 1,
                'variante': None,
                'remocoes': [],
            },
            'item_id': 'lanche_002',
            'nome': 'X-Salada',
            'campo': 'variante',
            'opcoes': [],
        }
        result = clarificar([item], 'simples', 0)
        assert result.tipo == 'invalida'

    def test_item_inexistente(self):
        """Item inexistente deve retornar erro."""
        item = {
            'item': {
                'item_id': 'inexistente',
                'quantidade': 1,
                'variante': None,
                'remocoes': [],
            },
            'item_id': 'inexistente',
            'nome': 'Item Fantasma',
            'campo': 'variante',
            'opcoes': ['a', 'b'],
        }
        result = clarificar([item], 'a', 0)
        # Fuzzy matching encontra 'a', mas item não existe → erro
        assert result.tipo == 'erro'


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE ResultadoClarificacao
# ══════════════════════════════════════════════════════════════════════════════


class TestResultadoClarificacao:
    """Testes para o dataclass ResultadoClarificacao."""

    def test_tipo_sucesso(self):
        """Resultado de sucesso deve ter tipo correto."""
        result = ResultadoClarificacao(
            tipo='sucesso',
            resposta='ok',
            etapa='inicio',
            carrinho=[],
            fila=[],
            tentativas=0,
        )
        assert result.tipo == 'sucesso'

    def test_tipo_invalida(self):
        """Resultado inválido deve ter tipo correto."""
        result = ResultadoClarificacao(
            tipo='invalida',
            resposta='erro',
            etapa='clarificando_variante',
            carrinho=[],
            fila=[],
            tentativas=1,
        )
        assert result.tipo == 'invalida'

    def test_tipo_erro(self):
        """Resultado de erro deve ter tipo correto."""
        result = ResultadoClarificacao(
            tipo='erro',
            resposta='erro interno',
            etapa='inicio',
            carrinho=[],
            fila=[],
            tentativas=0,
        )
        assert result.tipo == 'erro'


class TestObservabilidadeClarificacao:
    """Testes para verificação de log de clarificação."""

    @pytest.fixture
    def fila_hamburguer(self, item_hamburguer):
        """Fila com um hambúrguer pendente."""
        return [item_hamburguer]

    def test_log_sucesso(self, fila_hamburguer, tmp_path):
        """Deve logar clarificação com sucesso."""
        from src.observabilidade.clarificacao_logger import ClarificacaoLogger
        from src.observabilidade.registry import set_clarificacao_logger

        csv_path = tmp_path / 'clarificacoes.csv'
        set_clarificacao_logger(ClarificacaoLogger(csv_path))

        from src.graph.handlers.clarificacao import clarificar

        result = clarificar(fila_hamburguer, 'duplo', 0, thread_id='sessao-1')

        assert result.tipo == 'sucesso'
        with open(csv_path, encoding='utf-8') as f:
            import csv

            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]['thread_id'] == 'sessao-1'
            assert rows[0]['resultado'] == 'sucesso'
            assert rows[0]['variante_escolhida'] == 'duplo'

        set_clarificacao_logger(None)

    def test_sem_logger_nao_falha(self, fila_hamburguer):
        """Se logger não está configurado, não deve falhar."""
        from src.observabilidade.registry import set_clarificacao_logger

        set_clarificacao_logger(None)

        from src.graph.handlers.clarificacao import clarificar

        result = clarificar(fila_hamburguer, 'duplo', 0, thread_id='sessao-1')
        assert result.tipo == 'sucesso'
