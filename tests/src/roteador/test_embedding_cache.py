"""Testes para embedding cache."""

import json
from pathlib import Path


def test_embedding_cache_carrega_exemplos():
    """Cache deve carregar exemplos."""
    cache_path = (
        Path(__file__).parent.parent.parent.parent
        / 'src'
        / 'roteador'
        / 'embedding_cache.json'
    )
    with open(cache_path, encoding='utf-8') as f:
        cache = json.load(f)

    assert cache['total'] == len(cache['exemplos'])
    assert cache['model'] == 'mini-embed'


def test_embedding_cache_tem_exemplos_por_intencao():
    """Cache deve ter exemplos para todas as intensões."""
    cache_path = (
        Path(__file__).parent.parent.parent.parent
        / 'src'
        / 'roteador'
        / 'embedding_cache.json'
    )
    with open(cache_path, encoding='utf-8') as f:
        cache = json.load(f)

    intencoes = {}
    for ex in cache['exemplos']:
        intent = ex['intencao']
        intencoes[intent] = intencoes.get(intent, 0) + 1

    esperado = {
        'saudacao',
        'pedir',
        'remover',
        'trocar',
        'carrinho',
        'duvida',
        'confirmar',
        'negar',
        'cancelar',
    }
    assert set(intencoes.keys()) == esperado


def test_embedding_cache_embeddings_preenchidos():
    """_embeddings deve estar preenchidos após build."""
    cache_path = (
        Path(__file__).parent.parent.parent.parent
        / 'src'
        / 'roteador'
        / 'embedding_cache.json'
    )
    with open(cache_path, encoding='utf-8') as f:
        cache = json.load(f)

    # Threshold: pelo menos 60 exemplos (pode ter mais após adições)
    assert len(cache['embeddings']) >= 60
    assert len(cache['embeddings']) == len(cache['exemplos'])
    assert len(cache['embeddings'][0]) > 0
