"""
Modulo de extratores do Pede AI.

Fornece ferramentas de processamento de linguagem natural (NLP)
para extrair informacoes de mensagens do usuario.

Example:
    ```python
    from src.extratores import extrair, extrair_variante, extrair_item_carrinho

    resultado = extrair('um x-salada sem tomate')
    extrair_variante('duplo', 'lanche_001')
    'duplo'
    ```
"""

from src.extratores.carrinho_extrator import CarrinhoExtrator
from src.extratores.extrator import extrair, extrair_variante
from src.extratores.fuzzy_extrator import (
    extrair_tokens_significativos,
    fuzzy_match_item,
    fuzzy_match_variante,
    match_variante_numerica,
)
from src.extratores.modelos import ExtracaoTroca, ItemExtraido, MatchCarrinho
from src.extratores.nlp_engine import NlpEngine
from src.extratores.normalizador import normalizar_para_busca, normalizar_para_fuzzy
from src.observabilidade.loggers import ObservabilidadeLoggers

# Compatibilidade com codigo legado que importa normalizar()
normalizar = normalizar_para_busca
from src.extratores.troca_extrator import TrocaExtrator

__all__ = [
    'CarrinhoExtrator',
    'ExtracaoTroca',
    'ItemExtraido',
    'MatchCarrinho',
    'NlpEngine',
    'TrocaExtrator',
    'extrair',
    'extrair_item_carrinho',
    'extrair_itens_troca',
    'extrair_tokens_significativos',
    'extrair_variante',
    'fuzzy_match_item',
    'fuzzy_match_variante',
    'match_variante_numerica',
    'normalizar',
    'normalizar_para_busca',
    'normalizar_para_fuzzy',
]


# ── API compativel com versao procedural ───────────────────────────────────


def extrair_item_carrinho(mensagem: str, carrinho: list) -> list[dict]:
    """Extrai itens do carrinho para remocao.

    API compativel com a versao procedural — retorna list[dict].

    Args:
        mensagem: Texto da mensagem do usuario.
        carrinho: Lista de itens no carrinho atual.

    Returns:
        Lista de dicionarios com item_id, variante, indices.
    """
    from dataclasses import asdict  # noqa: PLC0415

    from src.config import get_cardapio  # noqa: PLC0415
    from src.extratores.carrinho_extrator import CarrinhoExtrator  # noqa: PLC0415
    from src.extratores.config import get_extrator_config  # noqa: PLC0415
    from src.extratores.nlp_engine import NlpEngine  # noqa: PLC0415

    config = get_extrator_config()
    cardapio = get_cardapio()
    engine = NlpEngine(config, cardapio)
    extrator = CarrinhoExtrator(engine, config)
    matches = extrator.extrair(mensagem, carrinho)
    return [asdict(m) for m in matches]


def extrair_itens_troca(
    mensagem: str,
    carrinho: list[dict],
    loggers: ObservabilidadeLoggers | None = None,
    thread_id: str = '',
    turn_id: str = '',
) -> dict:
    """Extrai informacoes de troca da mensagem.

    API compativel com a versao procedural — retorna dict.

    Args:
        mensagem: Mensagem do usuario.
        carrinho: Carrinho atual.
        loggers: Container de loggers para decision tracing.
        thread_id: ID da sessao.
        turn_id: ID do turno.

    Returns:
        Dict com 'caso', 'item_original' e 'variante_nova'.
    """
    from dataclasses import asdict  # noqa: PLC0415

    from src.config import get_cardapio  # noqa: PLC0415
    from src.extratores.config import get_extrator_config  # noqa: PLC0415
    from src.extratores.nlp_engine import NlpEngine  # noqa: PLC0415
    from src.extratores.troca_extrator import TrocaExtrator  # noqa: PLC0415

    config = get_extrator_config()
    cardapio = get_cardapio()
    engine = NlpEngine(config, cardapio)
    extrator = TrocaExtrator(engine, config)
    resultado = extrator.extrair(
        mensagem, carrinho, loggers=loggers, thread_id=thread_id, turn_id=turn_id
    )

    return {
        'caso': resultado.caso,
        'item_original': (
            asdict(resultado.item_original) if resultado.item_original else None
        ),
        'variante_nova': resultado.variante_nova,
    }
