"""Script para gerar embeddings e salvar no cache (geração incremental).

Suporta geração incremental (só novos embeddings) e geração completa.
Cria backup automático antes de sobrescrever o cache.
Usa formato de cache com hashes SHA256 (formato 2).
"""

import json
import time
from pathlib import Path

import ollama
import typer

from src.roteador.embedding_service import _hash_texto

app = typer.Typer(help='Gera embeddings para exemplos de classificação de intenções.')

CACHE_PATH = Path(__file__).parent.parent / 'src' / 'roteador' / 'embedding_cache.json'

MODELOS = {
    'mini': 'mini-embed',
    'nomic': 'nomic-embed-text',
}

DEFAULT_MODEL = 'mini'


def _migrar_cache_antigo(
    dados: dict | list,
) -> dict[str, list[float]]:
    """Migra cache no formato antigo (lista) para formato 2 (dict com hashes).

    Args:
        dados: Dados carregados do cache no formato antigo.

    Returns:
        Dicionario com {hash: embedding}.
    """
    # Extrair lista de embeddings
    embeddings_lista: list[list[float]] | None = None
    if isinstance(dados, dict):
        emb = dados.get('embeddings')
        if isinstance(emb, list):
            embeddings_lista = emb
    elif isinstance(dados, list):
        embeddings_lista = dados

    if embeddings_lista is None:
        return {}

    # Obter textos dos exemplos
    exemplos: list[dict] = []
    if isinstance(dados, dict) and 'exemplos' in dados:
        exemplos = dados['exemplos']
    if not exemplos:
        cache_path = Path(__file__).parent.parent / 'data' / 'exemplos-classificacao.json'
        if cache_path.exists():
            with open(cache_path, encoding='utf-8') as f:
                exemplos = json.load(f)

    # Associar posicoes aos hashes
    embeddings_dict: dict[str, list[float]] = {}
    for i, emb in enumerate(embeddings_lista):
        if i < len(exemplos):
            h = _hash_texto(exemplos[i]['texto'])
            embeddings_dict[h] = emb

    return embeddings_dict


def _carregar_cache() -> dict:
    """Carrega o cache de embeddings existente, migrando se necessario.

    Detecta formato antigo (lista ou {"format": 1}) e migra para formato 2.
    Formato novo ({"format": 2, "embeddings": {hash: emb}}) carrega direto.

    Returns:
        Dicionario com dados do cache pronto para manipulacao, incluindo:
        - 'format': 2
        - 'embeddings': dict com {hash: embedding}
        - 'exemplos': lista de exemplos (se existir)
        - 'model': modelo usado (se existir)

    Raises:
        typer.Exit: Se o arquivo de cache nao existir.
    """
    if not CACHE_PATH.exists():
        print(f'❌ Cache não encontrado: {CACHE_PATH}')
        raise typer.Exit(1)
    with open(CACHE_PATH, encoding='utf-8') as f:
        dados: dict | list = json.load(f)

    # Formato 2: ja esta no formato correto
    if isinstance(dados, dict) and dados.get('format') == 2:
        return dados

    # Migrar formato antigo
    embeddings_dict = _migrar_cache_antigo(dados)
    if not embeddings_dict and not isinstance(dados, dict):
        return {'format': 2, 'embeddings': {}}

    # Montar dict migrado
    migrado: dict = {'format': 2, 'embeddings': embeddings_dict}
    if isinstance(dados, dict):
        for chave in ('exemplos', 'model', 'total'):
            if chave in dados:
                migrado[chave] = dados[chave]

    # Salvar no formato novo
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, 'w', encoding='utf-8') as f:
        json.dump(migrado, f, ensure_ascii=False, indent=2)

    return migrado


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
    embeddings_dict: dict[str, list[float]] = cache.get('embeddings', {})

    if not exemplos:
        print('❌ Nenhum exemplo encontrado no cache.')
        raise typer.Exit(1)

    total = len(exemplos)
    existentes = len(embeddings_dict)

    # Validação: verifica dimensão do modelo
    if existentes > 0 and incremental:
        dim_esperada = len(next(iter(embeddings_dict.values())))
        teste = _gerar_embedding(modelo_nome, 'teste')
        dim_modelo = len(teste) if teste else 0
        if dim_esperada != dim_modelo:
            print(
                f'⚠️  Dimensão incompatível: cache={dim_esperada}, modelo={dim_modelo}'
            )
            print('🔄 Gerando todos os embeddings do zero...')
            incremental = False
            embeddings_dict = {}

    if incremental and existentes == total:
        print(f'✅ Cache já está completo ({total} embeddings). Nada a fazer.')
        return

    # Determinar quais hashes faltam
    hashes_faltantes: list[tuple[int, str]] = []
    for i, ex in enumerate(exemplos):
        h = _hash_texto(ex['texto'])
        if h not in embeddings_dict:
            hashes_faltantes.append((i, h))

    if incremental and existentes > 0:
        print(f'📋 Cache: {existentes}/{total} embeddings existentes')
        print(f'🔄 Gerando {len(hashes_faltantes)} embeddings novos...')
    else:
        print(f'📋 Gerando {total} embeddings do zero...')
        embeddings_dict = {}

    # Backup antes de sobrescrever
    _back_cache(cache)

    # Gera embeddings faltantes
    erros = 0
    embedding_fallback: list[float] | None = None
    for idx, (i, h) in enumerate(hashes_faltantes):
        ex = exemplos[i]
        try:
            emb = _gerar_embedding(modelo_nome, ex['texto'])
            embeddings_dict[h] = emb
            embedding_fallback = emb
            progresso = (idx + 1) / len(hashes_faltantes) * 100
            print(f'  [{idx + 1}/{len(hashes_faltantes)}] ({progresso:.0f}%) {ex["texto"]}')
        except Exception:
            erros += 1
            if embedding_fallback is None:
                fb = _gerar_embedding(modelo_nome, 'fallback')
                embedding_fallback = fb if fb else [0.0] * 384
            embeddings_dict[h] = [0.0] * len(embedding_fallback)
            print(f'  ⚠️  ERRO: {ex["texto"]} (placeholder)')

    # Atualiza cache no formato 2
    cache['format'] = 2
    cache['embeddings'] = embeddings_dict
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
    print(f'   Embeddings gerados: {len(hashes_faltantes)}')
    print(f'   Embeddings preservados: {existentes}')
    primeiro_emb = next(iter(embeddings_dict.values()), None)
    print(f'   Dimensão: {len(primeiro_emb) if primeiro_emb else "N/A"}')
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
    embeddings_dict: dict[str, list[float]] = cache.get('embeddings', {})

    primeiro_emb = next(iter(embeddings_dict.values()), None)

    print('=' * 60)
    print('📋 STATUS DO CACHE')
    print('=' * 60)
    print(f'   Arquivo: {CACHE_PATH}')
    print(f'   Formato: {cache.get("format", "desconhecido")}')
    print(f'   Modelo: {cache.get("model", "desconhecido")}')
    print(f'   Exemplos: {len(exemplos)}')
    print(f'   Embeddings: {len(embeddings_dict)}')
    if primeiro_emb:
        print(f'   Dimensão: {len(primeiro_emb)}')
    print(f'   Completo: {"✅ Sim" if len(embeddings_dict) == len(exemplos) else "❌ Não"}')
    print()


@app.command()
def listar_exemplos():
    """Lista exemplos e indica se possuem embedding."""
    cache = _carregar_cache()
    exemplos = cache.get('exemplos', [])
    embeddings_dict: dict[str, list[float]] = cache.get('embeddings', {})

    print('=' * 60)
    print('📋 EXEMPLOS NO CACHE')
    print('=' * 60)
    for i, ex in enumerate(exemplos):
        h = _hash_texto(ex['texto'])
        tem_emb = h in embeddings_dict and embeddings_dict[h][0] != 0.0
        status = '✅' if tem_emb else '❌'
        print(f'   {status} [{i + 1}] {ex["texto"]!r} → {ex["intencao"]}')
    print()


if __name__ == '__main__':
    app()
