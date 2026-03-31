"""
Testes de alta qualidade para o módulo src/config/prompts.py.

Características:
- Parametrização para evitar código repetitivo
- Cobertura completa de happy path e edge cases
- Testes de integridade e comportamento de cache
- Verificação de re-exports do pacote
"""

import pytest

from src.config import (
    get_cardapio,
    get_intencoes_validas,
    get_tenant_id,
    get_tenant_info,
    get_tenant_nome,
    get_prompt,
)


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def prompt_nome_validos():
    """Nomes de prompts válidos."""
    return ['classificador_intencoes']


@pytest.fixture
def intencoes_esperadas():
    """Intenções válidas esperadas."""
    return [
        'saudacao',
        'pedir',
        'remover',
        'trocar',
        'carrinho',
        'duvida',
        'confirmar',
        'negar',
        'cancelar',
    ]


# ══════════════════════════════════════════════════════════════════════════════
# TESTES PARAMETRIZADOS - PROMPTS
# ══════════════════════════════════════════════════════════════════════════════

class TestGetPrompt:
    """Testes para get_prompt()."""

    @pytest.mark.parametrize('prompt_name', [
        'classificador_intencoes',
    ])
    def test_prompt_existente_retorna_string_nao_vazia(self, prompt_name):
        """Prompt existente deve retornar string não vazia."""
        result = get_prompt(prompt_name)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_prompt_contem_instrucoes(self):
        """Prompt deve conter instruções de classificação."""
        result = get_prompt('classificador_intencoes')
        assert 'INTENÇÕES POSSÍVEIS' in result
        assert 'Classifique' in result

    def test_prompt_inexistente_lanca_key_error(self):
        """Prompt inexistente deve lançar KeyError."""
        with pytest.raises(KeyError):
            get_prompt('prompt_inexistente_123')

    def test_cache_retorna_mesma_instancia(self):
        """Cache deve retornar a mesma referência."""
        result1 = get_prompt('classificador_intencoes')
        result2 = get_prompt('classificador_intencoes')
        assert result1 is result2


class TestGetIntencoesValidas:
    """Testes para get_intencoes_validas()."""

    @pytest.mark.parametrize('intencao', [
        'saudacao',
        'pedir',
        'remover',
        'trocar',
        'carrinho',
        'duvida',
        'confirmar',
        'negar',
        'cancelar',
    ])
    def test_todas_intencoes_estao_presentes(self, intencao):
        """Todas as intenções principais devem estar presentes."""
        result = get_intencoes_validas()
        assert intencao in result

    def test_retorna_lista_de_strings(self):
        """Deve retornar lista de strings."""
        result = get_intencoes_validas()
        assert isinstance(result, list)
        assert all(isinstance(item, str) for item in result)

    def test_lista_nao_vazia(self):
        """Deve conter intenções."""
        result = get_intencoes_validas()
        assert len(result) > 0

    def test_cache_retorna_mesma_instancia(self):
        """Cache deve retornar a mesma referência."""
        result1 = get_intencoes_validas()
        result2 = get_intencoes_validas()
        assert result1 is result2


# ══════════════════════════════════════════════════════════════════════════════
# TESTES PARAMETRIZADOS - TENANT
# ══════════════════════════════════════════════════════════════════════════════

class TestGetTenantInfo:
    """Testes para get_tenant_info()."""

    def test_retorna_dicionario(self):
        """Deve retornar dicionário."""
        result = get_tenant_info()
        assert isinstance(result, dict)

    @pytest.mark.parametrize('key', ['tenant_id', 'tenant_nome'])
    def test_contem_chaves_esperadas(self, key):
        """Deve conter tenant_id e tenant_nome."""
        result = get_tenant_info()
        assert key in result

    def test_valores_nao_vazios(self):
        """Valores não devem ser vazios."""
        result = get_tenant_info()
        assert len(result['tenant_id']) > 0
        assert len(result['tenant_nome']) > 0


class TestGetTenantId:
    """Testes para get_tenant_id()."""

    def test_retorna_string(self):
        """Deve retornar string."""
        result = get_tenant_id()
        assert isinstance(result, str)

    def test_valor_esperado(self):
        """Deve retornar o tenant_id correto."""
        result = get_tenant_id()
        assert result == 'restaurante_teste'

    def test_consistente_com_get_tenant_info(self):
        """Deve ser consistente com get_tenant_info()."""
        info = get_tenant_info()
        tid = get_tenant_id()
        assert tid == info['tenant_id']


class TestGetTenantNome:
    """Testes para get_tenant_nome()."""

    def test_retorna_string(self):
        """Deve retornar string."""
        result = get_tenant_nome()
        assert isinstance(result, str)

    def test_valor_esperado(self):
        """Deve retornar o nome correto."""
        result = get_tenant_nome()
        assert result == 'Lanchonete do Zé'

    def test_consistente_com_get_tenant_info(self):
        """Deve ser consistente com get_tenant_info()."""
        info = get_tenant_info()
        nome = get_tenant_nome()
        assert nome == info['tenant_nome']


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE CONSISTÊNCIA E INTEGRIDADE
# ══════════════════════════════════════════════════════════════════════════════

class TestConsistencia:
    """Testes de consistência entre funções."""

    def test_prompt_contem_todas_intencoes(self):
        """Prompt deve mencionar todas as intenções."""
        prompt = get_prompt('classificador_intencoes')
        intencoes = get_intencoes_validas()
        for intencao in intencoes:
            assert intencao in prompt, f"Intenção '{intencao}' não encontrada no prompt"

    def test_tenant_info_equals_cardapio_data(self):
        """Tenant info deve vir do cardápio."""
        cardapio = get_cardapio()
        tenant_info = get_tenant_info()
        assert tenant_info['tenant_id'] == cardapio['tenant_id']
        assert tenant_info['tenant_nome'] == cardapio['tenant_nome']

    def test_tenant_id_equals_cardapio_tenant_id(self):
        """get_tenant_id deve ser consistente com get_cardapio."""
        cardapio = get_cardapio()
        tid = get_tenant_id()
        assert tid == cardapio['tenant_id']

    def test_tenant_nome_equals_cardapio_tenant_nome(self):
        """get_tenant_nome deve ser consistente com get_cardapio."""
        cardapio = get_cardapio()
        nome = get_tenant_nome()
        assert nome == cardapio['tenant_nome']


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE CACHE
# ══════════════════════════════════════════════════════════════════════════════

class TestCache:
    """Testes de comportamento de cache."""

    def test_prompt_cache_singleton(self):
        """Prompt deve usar cache singleton."""
        result1 = get_prompt('classificador_intencoes')
        result2 = get_prompt('classificador_intencoes')
        assert result1 is result2

    def test_intencoes_cache_singleton(self):
        """Intenções devem usar cache singleton."""
        result1 = get_intencoes_validas()
        result2 = get_intencoes_validas()
        assert result1 is result2


# ══════════════════════════════════════════════════════════════════════════════
# TESTES DE EDGE CASES
# ══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Testes de casos de borda."""

    def test_get_prompt_com_parametro_vazio(self):
        """Prompt vazio deve lançar erro."""
        with pytest.raises(KeyError):
            get_prompt('')

    def test_get_intencoes_nao_e_vazio(self):
        """Intenções devem ter no mínimo uma opção."""
        result = get_intencoes_validas()
        assert len(result) >= 1

    def test_tenant_info_nao_e_vazio(self):
        """Tenant info deve ter valores."""
        result = get_tenant_info()
        assert result['tenant_id']
        assert result['tenant_nome']
