"""Testes para a resolução de intent por contexto conversacional."""

from src.graph.contexto import node_resolver_contexto, RESOLUCOES, CATEGORIAS


def _state(mensagem: str, modo: str) -> dict:
    """Helper para criar estado mínimo para o resolver."""
    return {
        'mensagem_atual': mensagem,
        'modo': modo,
        'intent': '',
        'carrinho': [],
        'resposta': '',
    }


class TestResolucaoPorContexto:
    """Testes para node_resolver_contexto."""

    def test_sim_em_confirmando_resolve_finalizar(self):
        result = node_resolver_contexto(_state('sim', 'confirmando'))
        assert result['intent'] == 'finalizar_pedido'
        assert result['origem_intent'] == 'contexto'
        assert result['confidence'] == 1.0

    def test_nao_em_confirmando_resolve_modificar(self):
        result = node_resolver_contexto(_state('não', 'confirmando'))
        assert result['intent'] == 'modificar_pedido'

    def test_cancela_em_confirmando_resolve_cancelar(self):
        result = node_resolver_contexto(_state('cancela', 'confirmando'))
        assert result['intent'] == 'cancelar_pedido'

    def test_ok_em_coletando_resolve_finalizar(self):
        result = node_resolver_contexto(_state('ok', 'coletando'))
        assert result['intent'] == 'finalizar_pedido'

    def test_pode_em_confirmando_resolve_finalizar(self):
        result = node_resolver_contexto(_state('pode', 'confirmando'))
        assert result['intent'] == 'finalizar_pedido'

    def test_mensagem_complexa_em_confirmando_nao_resolve(self):
        """Mensagem não categorizada → contexto não resolve → intent vazio."""
        result = node_resolver_contexto(_state('quero mais um xbacon', 'confirmando'))
        assert result.get('intent', '') == ''

    def test_nao_em_ocioso_nao_resolve(self):
        """'não' em modo ocioso → contexto não tem regra → não resolve."""
        result = node_resolver_contexto(_state('não', 'ocioso'))
        assert result.get('intent', '') == ''

    def test_todas_as_linhas_da_tabela(self):
        """Cada entrada em RESOLUCOES deve resolver corretamente."""
        for (modo, categoria), intent_esperada in RESOLUCOES.items():
            # Pegar um token representativo da categoria
            token = next(iter(CATEGORIAS[categoria]))
            result = node_resolver_contexto(_state(token, modo))
            assert result['intent'] == intent_esperada, (
                f'Falhou para ({modo}, {categoria}): esperado {intent_esperada}, got {result.get("intent")}'
            )
