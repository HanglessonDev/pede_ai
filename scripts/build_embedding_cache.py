"""Script para gerar embeddings e salvar no cache (geração incremental).

Suporta geração incremental (só novos embeddings) e geração completa.
Cria backup automático antes de sobrescrever o cache.
"""

import json
import time
from pathlib import Path

import ollama
import typer

app = typer.Typer(help='Gera embeddings para exemplos de classificação de intenções.')

CACHE_PATH = Path(__file__).parent.parent / 'src' / 'roteador' / 'embedding_cache.json'

MODELOS = {
    'mini': 'mini-embed',
    'nomic': 'nomic-embed-text',
}

DEFAULT_MODEL = 'mini'


def _carregar_cache() -> dict:
    """Carrega o cache de embeddings existente.

    Returns:
        Dicionário com dados do cache (exemplos, embeddings, model).

    Raises:
        typer.Exit: Se o arquivo de cache não existir.
    """
    if not CACHE_PATH.exists():
        print(f'❌ Cache não encontrado: {CACHE_PATH}')
        raise typer.Exit(1)
    with open(CACHE_PATH, encoding='utf-8') as f:
        return json.load(f)


def _gerar_embedding(
    modelo: str, texto: str, tentativas: int = 3
) -> list[float] | None:
    """Gera embedding para um texto com retry em caso de erro.

    Args:
        modelo: Nome do modelo de embedding (ex: 'mini-embed').
        texto: Texto para gerar embedding.
        tentativas: Número máximo de tentativas antes de desistir.

    Returns:
        Lista de floats representando o embedding, ou None se falhar.
    """
    for tentativa in range(tentativas):
        try:
            response = ollama.embed(model=modelo, input=texto)
            return response['embeddings'][0]
        except Exception as e:
            if tentativa < tentativas - 1:
                time.sleep(1)
            else:
                print(f'\n❌ Erro ao gerar embedding para "{texto}": {e}')
                return None


def _back_cache(cache: dict) -> None:
    """Cria backup do cache antes de sobrescrever.

    Args:
        cache: Dados atuais do cache para backup.
    """
    backup = CACHE_PATH.with_suffix('.json.bak')
    with open(backup, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    print(f'💾 Backup criado: {backup}')


@app.command()
def build(  # noqa: PLR0915
    modelo: str = typer.Option(
        DEFAULT_MODEL, '--model', '-m', help='Modelo de embedding'
    ),
    incremental: bool = typer.Option(
        True,
        '--incremental/--full',
        '-i/-f',
        help='Geração incremental (só novos embeddings)',
    ),
):
    """Gera embeddings para exemplos no cache."""
    modelo_nome = MODELOS.get(modelo, modelo)

    cache = _carregar_cache()
    exemplos = cache.get('exemplos', [])
    embeddings_existentes = cache.get('embeddings', [])

    if not exemplos:
        print('❌ Nenhum exemplo encontrado no cache.')
        raise typer.Exit(1)

    total = len(exemplos)
    existentes = len(embeddings_existentes)

    # Validação: verifica se embeddings existentes têm dimensão correta
    if existentes > 0 and incremental:
        dim_esperada = len(embeddings_existentes[0])
        # Valida dimensão do primeiro embedding do modelo atual
        teste = _gerar_embedding(modelo_nome, 'teste')
        dim_modelo = len(teste) if teste else 0
        if dim_esperada != dim_modelo:
            print(
                f'⚠️  Dimensão incompatível: cache={dim_esperada}, modelo={dim_modelo}'
            )
            print('🔄 Gerando todos os embeddings do zero...')
            incremental = False
            embeddings_existentes = []

    if incremental and existentes == total:
        print(f'✅ Cache já está completo ({total} embeddings). Nada a fazer.')
        return

    # Geração incremental
    if incremental and existentes > 0:
        print(f'📋 Cache: {existentes}/{total} embeddings existentes')
        print(f'🔄 Gerando {total - existentes} embeddings novos...')
        embeddings = list(embeddings_existentes)
        start_idx = existentes
    else:
        print(f'📋 Gerando {total} embeddings do zero...')
        embeddings = []
        start_idx = 0

    # Backup antes de sobrescrever
    _back_cache(cache)

    # Gera embeddings
    erros = 0
    for i in range(start_idx, total):
        ex = exemplos[i]
        try:
            emb = _gerar_embedding(modelo_nome, ex['texto'])
            embeddings.append(emb)
            progresso = (i + 1) / total * 100
            print(f'  [{i + 1}/{total}] ({progresso:.0f}%) {ex["texto"]}')
        except Exception:
            erros += 1
            fallback = _gerar_embedding(modelo_nome, 'fallback')
            embeddings.append([0.0] * len(fallback) if fallback else [0.0] * 384)
            print(f'  ⚠️  ERRO: {ex["texto"]} (placeholder)')

    # Atualiza cache
    cache['embeddings'] = embeddings
    cache['model'] = modelo
    cache['total'] = total

    with open(CACHE_PATH, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

    # Resumo
    print()
    print('=' * 60)
    print('📊 RESUMO')
    print('=' * 60)
    print(f'   Modelo: {modelo_nome}')
    print(f'   Exemplos: {total}')
    print(f'   Embeddings gerados: {total - start_idx}')
    print(f'   Embeddings preservados: {start_idx}')
    print(f'   Dimensão: {len(embeddings[0]) if embeddings else "N/A"}')
    print(f'   Erros: {erros}')
    print(f'   Cache: {CACHE_PATH}')
    if erros > 0:
        print(f'   ⚠️  {erros} embeddings com placeholder (zeros)')
    print()


@app.command()
def status():
    """Mostra status atual do cache."""
    cache = _carregar_cache()
    exemplos = cache.get('exemplos', [])
    embeddings = cache.get('embeddings', [])

    print('=' * 60)
    print('📋 STATUS DO CACHE')
    print('=' * 60)
    print(f'   Arquivo: {CACHE_PATH}')
    print(f'   Modelo: {cache.get("model", "desconhecido")}')
    print(f'   Exemplos: {len(exemplos)}')
    print(f'   Embeddings: {len(embeddings)}')
    if embeddings:
        print(f'   Dimensão: {len(embeddings[0])}')
    print(f'   Completo: {"✅ Sim" if len(embeddings) == len(exemplos) else "❌ Não"}')
    print()


@app.command()
def listar_exemplos():
    """Lista exemplos e seus embeddings."""
    cache = _carregar_cache()
    exemplos = cache.get('exemplos', [])
    embeddings = cache.get('embeddings', [])

    print('=' * 60)
    print('📋 EXEMPLOS NO CACHE')
    print('=' * 60)
    for i, ex in enumerate(exemplos):
        tem_emb = i < len(embeddings) and embeddings[i][0] != 0.0
        status = '✅' if tem_emb else '❌'
        print(f'   {status} [{i + 1}] {ex["texto"]!r} → {ex["intencao"]}')
    print()


if __name__ == '__main__':
    app()
