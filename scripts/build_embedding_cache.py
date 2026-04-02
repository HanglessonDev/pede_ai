"""Script para gerar embeddings e salvar no cache."""

import json
from pathlib import Path

import ollama

CACHE_PATH = Path(__file__).parent.parent / 'src' / 'roteador' / 'embedding_cache.json'
MODEL = 'mini-embed'


def main():
    with open(CACHE_PATH, encoding='utf-8') as f:
        cache = json.load(f)

    exemplos = cache['exemplos']
    embeddings = []

    print(f'Gerando embeddings para {len(exemplos)} exemplos...')

    for i, ex in enumerate(exemplos):
        response = ollama.embeddings(model=MODEL, prompt=ex['texto'])
        embeddings.append(response['embedding'])
        print(f'  [{i + 1}/{len(exemplos)}] {ex["texto"]}')

    cache['embeddings'] = embeddings

    with open(CACHE_PATH, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

    print(f'Cache atualizado com {len(embeddings)} embeddings')


if __name__ == '__main__':
    main()
