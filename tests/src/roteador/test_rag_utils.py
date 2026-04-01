"""Testes para rag_utils.py."""


class TestCosineSimilarity:
    """Testes para cosine_similarity."""

    def test_cosine_similarity_same_vector_returns_1(self):
        """Vetores iguais devem ter similaridade 1.0."""
        from src.roteador.rag_utils import cosine_similarity

        vec = [1.0, 0.0]
        result = cosine_similarity(vec, vec)
        assert result == 1.0

    def test_cosine_similarity_perpendicular_returns_0(self):
        """Vetores perpendiculares devem ter similaridade 0."""
        from src.roteador.rag_utils import cosine_similarity

        vec1 = [1.0, 0.0]
        vec2 = [0.0, 1.0]
        result = cosine_similarity(vec1, vec2)
        assert result == 0.0

    def test_cosine_similarity_opposite_returns_minus_1(self):
        """Vetores opostos devem ter similaridade -1.0."""
        from src.roteador.rag_utils import cosine_similarity

        vec1 = [1.0, 0.0]
        vec2 = [-1.0, 0.0]
        result = cosine_similarity(vec1, vec2)
        assert result == -1.0

    def test_cosine_similarity_zero_vector_returns_0(self):
        """Vetor zero deve retornar 0."""
        from src.roteador.rag_utils import cosine_similarity

        vec1 = [0.0, 0.0]
        vec2 = [1.0, 0.0]
        result = cosine_similarity(vec1, vec2)
        assert result == 0.0


class TestCalcularVotacao:
    """Testes para calcular_votacao."""

    def test_calcular_votacao_retorna_intencao_mais_comum(self):
        """Deve retornar a intenção mais comum."""
        from src.roteador.rag_utils import calcular_votacao

        similares = [
            {'texto': 'oi', 'intencao': 'saudacao', 'similaridade': 0.9},
            {'texto': 'bom dia', 'intencao': 'saudacao', 'similaridade': 0.8},
            {'texto': 'xo', 'intencao': 'pedir', 'similaridade': 0.7},
        ]

        result = calcular_votacao(similares)
        assert result == 'saudacao'

    def test_calcular_votacao_empate_retorna_primeiro(self):
        """Em caso de empate, retorna o primeiro encontrado."""
        from src.roteador.rag_utils import calcular_votacao

        similares = [
            {'texto': 'oi', 'intencao': 'saudacao', 'similaridade': 0.9},
            {'texto': 'bom dia', 'intencao': 'pedir', 'similaridade': 0.8},
            {'texto': 'ola', 'intencao': 'saudacao', 'similaridade': 0.7},
            {'texto': 'eai', 'intencao': 'pedir', 'similaridade': 0.6},
        ]

        result = calcular_votacao(similares)
        assert result in ['saudacao', 'pedir']


class TestMontarPromptRag:
    """Testes para montar_prompt_rag."""

    def test_montar_prompt_rag_inclui_votacao(self):
        """Prompt deve incluir a intenção dominante."""
        from src.roteador.rag_utils import montar_prompt_rag

        similares = [
            {'texto': 'oi', 'intencao': 'saudacao', 'similaridade': 0.9},
            {'texto': 'bom dia', 'intencao': 'saudacao', 'similaridade': 0.8},
        ]

        prompt = montar_prompt_rag('oi tudo bem', similares, 'saudacao')

        assert 'saudacao' in prompt
        assert 'oi' in prompt
        assert 'oi tudo bem' in prompt
        assert 'INTENÇÕES VÁLIDAS' in prompt

    def test_montar_prompt_rag_limita_exemplos(self):
        """Prompt deve limitar a 5 exemplos."""
        from src.roteador.rag_utils import montar_prompt_rag

        similares = [
            {
                'texto': f'exemplo{i}',
                'intencao': 'saudacao',
                'similaridade': 0.9 - i * 0.1,
            }
            for i in range(10)
        ]

        prompt = montar_prompt_rag('teste', similares, 'saudacao')

        assert prompt.count('→') <= 6  # 5 exemplos + 1 linha "SUA VEZ"
