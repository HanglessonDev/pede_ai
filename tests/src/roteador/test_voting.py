"""Testes para a estrategia de votacao consolidada."""


from src.roteador.modelos import ExemploSimilar
from src.roteador.voting import votar_com_prioridade


ALTA_PRIORIDADE = frozenset(
    {'pedir', 'remover', 'trocar', 'carrinho', 'confirmar', 'cancelar'}
)


# ══════════════════════════════════════════════════════════════════════════════
# VOTACAO COM PRIORIDADE
# ══════════════════════════════════════════════════════════════════════════════


class TestVotarComPrioridade:
    """Testes para votar_com_prioridade."""

    def test_lista_vazia_retorna_desconhecido(self):
        """Lista vazia deve retornar 'desconhecido'."""
        assert votar_com_prioridade([], ALTA_PRIORIDADE) == 'desconhecido'

    def test_top1_confianca_absoluta(self):
        """Top-1 >= 0.98 deve confiar direto."""
        exemplos = [
            ExemploSimilar('cancela tudo', 'cancelar', 0.99),
            ExemploSimilar('quero lanche', 'pedir', 0.70),
        ]

        resultado = votar_com_prioridade(exemplos, ALTA_PRIORIDADE)
        assert resultado == 'cancelar'

    def test_alta_prioridade_vence_saudacao(self):
        """Intent de alta prioridade deve vencer saudacao mesmo com menos exemplos."""
        exemplos = [
            ExemploSimilar('bom dia', 'saudacao', 0.92),
            ExemploSimilar('bom dia quero lanche', 'pedir', 0.78),
            ExemploSimilar('ola bom dia', 'saudacao', 0.75),
        ]

        resultado = votar_com_prioridade(exemplos, ALTA_PRIORIDADE)
        assert resultado == 'pedir'

    def test_alta_prioridade_abaixo_min_similarity(self):
        """Alta prioridade abaixo de min_similarity nao deve vencer."""
        exemplos = [
            ExemploSimilar('bom dia', 'saudacao', 0.92),
            ExemploSimilar('algo remoto', 'pedir', 0.40),
        ]

        resultado = votar_com_prioridade(exemplos, ALTA_PRIORIDADE, min_similarity=0.55)
        assert resultado == 'saudacao'

    def test_maioria_simples_sem_prioridade(self):
        """Sem prioridade no top-K, deve usar maioria simples."""
        exemplos = [
            ExemploSimilar('qual o preco', 'duvida', 0.85),
            ExemploSimilar('quanto custa', 'duvida', 0.80),
            ExemploSimilar('qual horario', 'duvida', 0.75),
        ]

        resultado = votar_com_prioridade(exemplos, ALTA_PRIORIDADE)
        assert resultado == 'duvida'

    def test_empate_maioria(self):
        """Empate deve retornar um dos empatados."""
        exemplos = [
            ExemploSimilar('oi', 'saudacao', 0.90),
            ExemploSimilar('quero lanche', 'pedir', 0.85),
        ]

        resultado = votar_com_prioridade(exemplos, ALTA_PRIORIDADE)
        assert resultado in ['saudacao', 'pedir']

    def test_melhor_prioridade_nao_e_top1(self):
        """Deve encontrar a melhor prioridade mesmo nao sendo top-1."""
        exemplos = [
            ExemploSimilar('bom dia', 'saudacao', 0.95),
            ExemploSimilar('quero xbacon', 'pedir', 0.80),
            ExemploSimilar('me ve coca', 'pedir', 0.70),
            ExemploSimilar('ola', 'saudacao', 0.65),
        ]

        resultado = votar_com_prioridade(exemplos, ALTA_PRIORIDADE)
        assert resultado == 'pedir'

    def test_multiplas_prioridades_melhor_sim(self):
        """Com multiplas prioridades, deve escolher a de maior similaridade."""
        exemplos = [
            ExemploSimilar('bom dia', 'saudacao', 0.90),
            ExemploSimilar('tira coca', 'remover', 0.75),
            ExemploSimilar('quero lanche', 'pedir', 0.60),
        ]

        resultado = votar_com_prioridade(exemplos, ALTA_PRIORIDADE)
        assert resultado == 'remover'

    def test_top1_exatamente_098(self):
        """Top-1 exatamente 0.98 deve confiar direto."""
        exemplos = [
            ExemploSimilar('exato', 'confirmar', 0.98),
        ]

        resultado = votar_com_prioridade(exemplos, ALTA_PRIORIDADE)
        assert resultado == 'confirmar'

    def test_top1_abaixo_098_com_prioridade(self):
        """Top-1 abaixo de 0.98 com prioridade no top-K deve usar prioridade."""
        exemplos = [
            ExemploSimilar('bom dia amigo', 'saudacao', 0.97),
            ExemploSimilar('quero xbacon', 'pedir', 0.80),
        ]

        resultado = votar_com_prioridade(exemplos, ALTA_PRIORIDADE)
        assert resultado == 'pedir'
