"""Geracao de patterns para o EntityRuler do spaCy.

Funcoes puras — nao dependem de estado global.

Example:
    ```python
    from src.extratores.patterns import gerar_patterns
    from src.extratores.normalizador import normalizar_para_busca

    patterns = gerar_patterns(cardapio, normalizar_para_busca)
    ```
"""

from __future__ import annotations

from collections.abc import Callable

from src.extratores.config import get_extrator_config


def _adicionar_pattern(
    lista_patterns: list[dict],
    vistos: set,
    label: str,
    texto_bruto: str,
    item_id: str,
    normalizar: Callable[[str], str],
) -> None:
    """Adiciona pattern evitando duplicatas.

    Gera multiplas representacoes do mesmo texto (tokenizado,
    com hifen, etc.) para melhorar o matching.

    Args:
        lista_patterns: Lista de patterns para adicionar.
        vistos: Conjunto de patterns ja adicionados.
        label: Rotulo da entidade (ITEM, VARIANTE, etc.).
        texto_bruto: Texto original do item/variante.
        item_id: ID do item no cardapio.
        normalizar: Funcao de normalizacao.
    """
    texto = normalizar(texto_bruto)
    chave = (label, texto)
    if chave not in vistos:
        vistos.add(chave)
        tokens = texto.split()
        if len(tokens) == 1:
            lista_patterns.append(dict(label=label, pattern=texto, id=item_id))
        else:
            # Token pattern: matcha "x tudo" (tokenizados separados)
            lista_patterns.append(
                dict(label=label, pattern=[{'LOWER': t} for t in tokens], id=item_id)
            )
            # String pattern: matcha "x-tudo" (token unico com hifen)
            unico = texto.replace(' ', '-')
            if unico not in vistos:
                vistos.add((label, unico))
                lista_patterns.append(dict(label=label, pattern=unico, id=item_id))


def gerar_patterns(
    cardapio: dict,
    normalizar: Callable[[str], str],
) -> list[dict]:
    """Gera patterns de entidade para o EntityRuler.

    Cria patterns para todos os itens, aliases, variantes do cardapio
    e numeros escritos por extenso.

    Args:
        cardapio: Dicionario com dados do cardapio.
        normalizar: Funcao de normalizacao (ex: normalizar_para_busca).

    Returns:
        Lista de patterns no formato spaCy EntityRuler.
    """
    config = get_extrator_config()
    patterns: list[dict] = []
    vistos: set = set()

    itens = cardapio.get('itens', [])
    for item in itens:
        _adicionar_pattern(
            patterns, vistos, 'ITEM', item.get('nome'), item.get('id'), normalizar
        )

        for alias in item.get('aliases') or []:
            _adicionar_pattern(
                patterns, vistos, 'ITEM', alias, item.get('id'), normalizar
            )

        for variante in item.get('variantes') or []:
            opcao = variante.get('opcao', '')
            # Pattern completo: "limao 300ml"
            _adicionar_pattern(
                patterns, vistos, 'VARIANTE', opcao, item.get('id'), normalizar
            )
            # Patterns parciais para matching flexivel
            # Ex: "limao 300ml" -> "limao" e "laranja 500ml" -> "laranja"
            # Digitos nao geram partial patterns — NUM_PENDING cuida disso
            if ' ' in opcao:
                palavra_chave = opcao.split()[0]
                if palavra_chave.lower() not in {'ml'} and not palavra_chave.isdigit():
                    _adicionar_pattern(
                        patterns,
                        vistos,
                        'VARIANTE',
                        palavra_chave,
                        item.get('id'),
                        normalizar,
                    )

    patterns.extend(
        [
            {'label': 'NUM_PENDING', 'pattern': [{'LOWER': palavra}]}
            for palavra in config.numeros_escritos
        ]
    )

    return patterns
