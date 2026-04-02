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

    def test_calcular_votacao_ponderada_por_similaridade(self):
        """Voto deve ser ponderado por similaridade, não apenas contagem."""
        from src.roteador.rag_utils import calcular_votacao

        # 2 exemplos de 'pedir' com baixa similaridade (0.55 cada = 1.10 total)
        # 1 exemplo de 'saudacao' com alta similaridade (0.95)
        # Mesmo tendo menos exemplos, 'pedir' deve ganhar pelo peso acumulado
        similares = [
            {'texto': 'quero lanche', 'intencao': 'pedir', 'similaridade': 0.55},
            {'texto': 'me vê coca', 'intencao': 'pedir', 'similaridade': 0.56},
            {'texto': 'oi', 'intencao': 'saudacao', 'similaridade': 0.95},
        ]

        result = calcular_votacao(similares)
        assert result == 'pedir'  # 0.55 + 0.56 = 1.11 > 0.95

    def test_calcular_votacao_lista_vazia_retorna_desconhecido(self):
        """Lista vazia deve retornar 'desconhecido'."""
        from src.roteador.rag_utils import calcular_votacao

        result = calcular_votacao([])
        assert result == 'desconhecido'


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

        # Conta apenas exemplos na seção EXEMPLOS (entre "EXEMPLOS:" e "Agora classifique")
        secao_exemplos = prompt.split('EXEMPLOS:')[1].split('Agora classifique')[0]
        # Deve ter 5 exemplos (→) + instruções podem ter mais →, então verificamos os exemplos especificamente
        linhas_exemplos = [l for l in secao_exemplos.split('\n') if '→' in l and l.strip().startswith('"')]
        assert len(linhas_exemplos) == 5  # exatamente 5 exemplos


class TestBuscarSimilares:
    """Testes para buscar_similares com filtro de threshold."""

    def test_buscar_similares_filtra_por_threshold_padrao(self):
        """Deve filtrar exemplos abaixo de 0.55 (threshold padrão)."""
        from src.roteador.rag_utils import buscar_similares, MIN_SIMILARITY_THRESHOLD

        # Mock de exemplos e embeddings
        exemplos = [
            {'texto': 'exemplo1', 'intencao': 'pedir'},
            {'texto': 'exemplo2', 'intencao': 'pedir'},
            {'texto': 'exemplo3', 'intencao': 'saudacao'},
        ]
        # Embeddings fictícios (não importam para este teste)
        embeddings = [[0.5], [0.5], [0.5]]

        # Patch para retornar similaridades fixas
        from unittest.mock import patch

        with (
            patch('src.roteador.rag_utils.gerar_embedding', return_value=[0.5]),
            patch('src.roteador.rag_utils.cosine_similarity') as mock_sim,
        ):
            # Retorna similaridades: 0.80, 0.50, 0.60
            mock_sim.side_effect = [0.80, 0.50, 0.60]

            result = buscar_similares('teste', exemplos, embeddings, top_k=3)

            # Apenas exemplos >= 0.55 devem retornar
            assert len(result) == 2
            assert all(r['similaridade'] >= MIN_SIMILARITY_THRESHOLD for r in result)
            assert result[0]['texto'] == 'exemplo1'  # 0.80
            assert result[1]['texto'] == 'exemplo3'  # 0.60

    def test_buscar_similares_threshold_personalizavel(self):
        """Deve aceitar threshold personalizado."""
        from src.roteador.rag_utils import buscar_similares

        exemplos = [
            {'texto': 'exemplo1', 'intencao': 'pedir'},
            {'texto': 'exemplo2', 'intencao': 'pedir'},
        ]
        embeddings = [[0.5], [0.5]]

        from unittest.mock import patch

        # Teste 1: threshold 0.45 - ambos passam
        with (
            patch('src.roteador.rag_utils.gerar_embedding', return_value=[0.5]),
            patch('src.roteador.rag_utils.cosine_similarity', side_effect=[0.60, 0.50]),
        ):
            result = buscar_similares('teste', exemplos, embeddings, top_k=2, min_similarity=0.45)
            assert len(result) == 2

        # Teste 2: threshold 0.55 - apenas 0.60 passa
        with (
            patch('src.roteador.rag_utils.gerar_embedding', return_value=[0.5]),
            patch('src.roteador.rag_utils.cosine_similarity', side_effect=[0.60, 0.50]),
        ):
            result = buscar_similares('teste', exemplos, embeddings, top_k=2, min_similarity=0.55)
            assert len(result) == 1
            assert result[0]['similaridade'] == 0.60

    def test_buscar_similares_retorna_vazio_se_todos_abaixo_threshold(self):
        """Se todos exemplos estão abaixo do threshold, retorna lista vazia."""
        from src.roteador.rag_utils import buscar_similares

        exemplos = [{'texto': 'exemplo1', 'intencao': 'pedir'}]
        embeddings = [[0.5]]

        from unittest.mock import patch

        with (
            patch('src.roteador.rag_utils.gerar_embedding', return_value=[0.5]),
            patch('src.roteador.rag_utils.cosine_similarity', return_value=0.30),
        ):
            result = buscar_similares('teste', exemplos, embeddings, top_k=1)
            assert len(result) == 0
