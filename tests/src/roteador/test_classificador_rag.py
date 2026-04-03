"""Testes para o classificador RAG com confidence."""

from unittest.mock import patch


class TestClassificarIntencaoComConfidence:
    """Testes para _classificar_intencao."""

    def test_sem_embeddings_retorna_fallback(self):
        """Se não houver embeddings, usa fallback."""
        from src.roteador import classificador_intencoes
        from src.roteador.classificador_intencoes import (
            _classificar_intencao,
        )

        original_embeddings = classificador_intencoes.EMBEDDINGS
        classificador_intencoes.EMBEDDINGS = []

        try:
            with patch.object(
                classificador_intencoes,
                'classificar_com_llm',
                return_value='saudacao',
            ):
                result = _classificar_intencao('oi')
        finally:
            classificador_intencoes.EMBEDDINGS = original_embeddings

        assert result['intent'] == 'saudacao'
        assert result['confidence'] == 1.0

    def test_sem_similares_retorna_fallback(self):
        """Se não encontrar similares, usa fallback."""
        from src.roteador import classificador_intencoes
        from src.roteador.classificador_intencoes import (
            _classificar_intencao,
        )

        with (
            patch.object(classificador_intencoes, 'buscar_similares', return_value=[]),
            patch.object(
                classificador_intencoes,
                'classificar_com_llm',
                return_value='pedir',
            ),
        ):
            result = _classificar_intencao('mensagem qualquer')

        assert result['intent'] == 'pedir'
        assert result['confidence'] == 1.0

    def test_rag_forte_skip_llm(self):
        """RAG com confidence >= 0.95 deve retornar direto, sem chamar LLM."""
        from src.roteador import classificador_intencoes
        from src.roteador.classificador_intencoes import (
            _classificar_intencao,
        )

        similares = [
            {'texto': 'cancela tudo', 'intencao': 'cancelar', 'similaridade': 0.98},
        ]

        with (
            patch.object(
                classificador_intencoes, 'buscar_similares', return_value=similares
            ),
            patch.object(
                classificador_intencoes, 'calcular_votacao', return_value='cancelar'
            ),
            patch.object(classificador_intencoes, 'validar_com_llm') as mock_llm,
        ):
            result = _classificar_intencao('cancela tudo')

        # LLM NÃO deve ser chamado
        mock_llm.assert_not_called()

        # Deve retornar decisão do RAG
        assert result['intent'] == 'cancelar'
        assert result['confidence'] == 0.98

    def test_rag_medio_chama_llm(self):
        """RAG com confidence 0.50-0.95 deve chamar LLM para validar."""
        from src.roteador import classificador_intencoes
        from src.roteador.classificador_intencoes import (
            _classificar_intencao,
        )

        similares = [
            {'texto': 'quero um xbacon', 'intencao': 'pedir', 'similaridade': 0.75},
        ]

        with (
            patch.object(
                classificador_intencoes, 'buscar_similares', return_value=similares
            ),
            patch.object(
                classificador_intencoes, 'calcular_votacao', return_value='pedir'
            ),
            patch.object(
                classificador_intencoes, 'montar_prompt_rag', return_value='prompt'
            ),
            patch.object(
                classificador_intencoes, 'validar_com_llm', return_value=('pedir', 1.0)
            ),
        ):
            result = _classificar_intencao('quero um lanche')

        # LLM deve ser chamado
        assert result['intent'] == 'pedir'

    def test_rag_fraco_fallback(self):
        """RAG com confidence < 0.50 deve usar fallback (prompt fixo)."""
        from src.roteador import classificador_intencoes
        from src.roteador.classificador_intencoes import (
            _classificar_intencao,
        )

        similares = [
            {'texto': 'abc', 'intencao': 'desconhecido', 'similaridade': 0.40},
        ]

        with (
            patch.object(
                classificador_intencoes, 'buscar_similares', return_value=similares
            ),
            patch.object(
                classificador_intencoes, 'calcular_votacao', return_value='desconhecido'
            ),
            patch.object(
                classificador_intencoes,
                'classificar_com_llm',
                return_value='duvida',
            ),
        ):
            result = _classificar_intencao('mensagem estranha')

        # Intent vem do fallback, mas confidence preserva a do RAG
        assert result['intent'] == 'duvida'
        assert result['confidence'] == 0.40
        assert result['caminho'] == 'llm_rag'


class TestClassificarIntencao:
    """Testes para classificar_intencao (API compatível)."""

    def test_retorna_string_nao_tupla(self):
        """classificar_intencao deve retornar string, não tupla."""
        with patch(
            'src.roteador.classificador_intencoes._classificar_intencao',
            return_value={'intent': 'pedir', 'confidence': 0.85, 'caminho': 'llm_rag', 'top1_texto': '', 'top1_intencao': '', 'mensagem_norm': ''},
        ):
            from src.roteador.classificador_intencoes import classificar_intencao

            result = classificar_intencao('quero xbacon')

        assert isinstance(result, str)
        assert result == 'pedir'


class TestRAGForTeThreshold:
    """Testes específicos para o threshold RAG_FORTE_THRESHOLD."""

    def test_threshold_constante_existe(self):
        """Constante RAG_FORTE_THRESHOLD deve existir."""
        from src.roteador.classificador_intencoes import RAG_FORTE_THRESHOLD

        assert RAG_FORTE_THRESHOLD == 0.95

    def test_threshold_na_fronteira_095(self):
        """Confidence exatamente 0.95 deve skipar LLM."""
        from src.roteador import classificador_intencoes
        from src.roteador.classificador_intencoes import (
            _classificar_intencao,
        )

        similares_095 = [
            {'texto': 'exato', 'intencao': 'confirmar', 'similaridade': 0.95},
        ]

        with (
            patch.object(
                classificador_intencoes, 'buscar_similares', return_value=similares_095
            ),
            patch.object(
                classificador_intencoes, 'calcular_votacao', return_value='confirmar'
            ),
            patch.object(classificador_intencoes, 'validar_com_llm') as mock_llm,
        ):
            result = _classificar_intencao('exato')

        mock_llm.assert_not_called()
        assert result['intent'] == 'confirmar'

    def test_threshold_abaixo_094_chama_llm(self):
        """Confidence 0.94 deve chamar LLM."""
        from src.roteador import classificador_intencoes
        from src.roteador.classificador_intencoes import (
            _classificar_intencao,
        )

        similares_094 = [
            {'texto': 'quase', 'intencao': 'confirmar', 'similaridade': 0.94},
        ]

        with (
            patch.object(
                classificador_intencoes, 'buscar_similares', return_value=similares_094
            ),
            patch.object(
                classificador_intencoes, 'calcular_votacao', return_value='confirmar'
            ),
            patch.object(
                classificador_intencoes, 'montar_prompt_rag', return_value='prompt'
            ),
            patch.object(
                classificador_intencoes,
                'validar_com_llm',
                return_value=('confirmar', 1.0),
            ),
        ):
            result = _classificar_intencao('quase')

        # LLM deve ser chamado
        assert result['intent'] == 'confirmar'
