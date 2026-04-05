"""Script para gerar embeddings e salvar no cache (geração incremental).

Usa o EmbeddingService já implementado em src/roteador/.
O provedor de embeddings e os caminhos vêm da config em roteador.yml.

Exemplos de uso:
    uv run python scripts/build_embedding_cache.py status
    uv run python scripts/build_embedding_cache.py listar-exemplos
    uv run python scripts/build_embedding_cache.py build --full
"""

import contextlib
import io
import json
import logging
import os
import sys
import warnings
from pathlib import Path

# Garante que o root do projeto esteja no path para imports de src/
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Suprime warnings do HF Hub antes de importar qualquer coisa relacionada
os.environ.setdefault('HF_HUB_DISABLE_TELEMETRY', '1')
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', module='huggingface_hub')
warnings.filterwarnings('ignore', module='sentence_transformers')
logging.getLogger('huggingface_hub').setLevel(logging.ERROR)
logging.getLogger('sentence_transformers').setLevel(logging.ERROR)
logging.getLogger('torch').setLevel(logging.ERROR)

import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from src.config.roteador_config import get_roteador_config
from src.infra.embedding_providers import SentenceTransformerEmbeddings
from src.roteador.embedding_service import EmbeddingService, _hash_texto

app = typer.Typer(
    help='Gera embeddings para exemplos de classificação de intenções.',
    rich_markup_mode='rich',
)
console = Console()


def _criar_provider() -> SentenceTransformerEmbeddings:
    """Cria provider suprimindo output ruidoso do sentence-transformers."""
    with (
        contextlib.redirect_stderr(io.StringIO()),
        contextlib.redirect_stdout(io.StringIO()),
    ):
        return SentenceTransformerEmbeddings()


@app.command()
def build(
    full: bool = typer.Option(
        False,
        '--full',
        '-f',
        help='Regenerar todos os embeddings do zero',
    ),
):
    """Gera embeddings faltantes para exemplos de classificação."""
    config = get_roteador_config()
    provider = _criar_provider()
    service = EmbeddingService(
        provider=provider,
        exemplos_path=config.exemplos_path,
        cache_path=config.embedding_cache_path,
    )

    existentes = len(service._embeddings)
    total = len(service.exemplos)

    if not full and existentes >= total:
        console.print(
            f'\n[green]✅[/green] Cache já está completo ({total} embeddings).'
        )
        return

    if full:
        console.print(
            '[yellow]🔄[/yellow] Regenerando [bold]{total}[/bold] embeddings do zero...'
        )
        service._embeddings_dict = {}
        service._embeddings = []

    console.print(f'[blue]📋[/blue] Gerando [bold]{total}[/bold] embeddings...')

    with Progress(
        TextColumn('[progress.description]{task.description}'),
        BarColumn(complete_style='blue', finished_style='green'),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task('Gerando embeddings', total=total)

        # Gera todos do zero (full) ou só faltantes (incremental)
        if full:
            textos_gerar = [ex.texto for ex in service.exemplos]
        else:
            textos_gerar = []
            for ex in service.exemplos:
                h = _hash_texto(ex.texto)
                if h not in service._embeddings_dict:
                    textos_gerar.append(ex.texto)
            progress.update(task, advance=existentes)

        # Gera em batches
        novos = provider.embed_batch(textos_gerar)
        progress.update(task, advance=len(novos))

        # Salva
        for texto, emb in zip(textos_gerar, novos, strict=True):
            h = _hash_texto(texto)
            service._embeddings_dict[h] = emb

        service._embeddings, service._exemplo_indices = service._montar_lista_alinhada()
        service._cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(service._cache_path, 'w', encoding='utf-8') as f:
            json.dump({'format': 2, 'embeddings': service._embeddings_dict}, f)

    table = Table(title='Resumo', show_header=False, box=None)
    table.add_column('Campo', style='cyan')
    table.add_column('Valor', style='white')
    primeiro = next(iter(service._embeddings_dict.values()), None)
    table.add_row('Exemplos', str(total))
    table.add_row('Embeddings', str(len(service._embeddings)))
    table.add_row('Dimensão', str(len(primeiro)) if primeiro else 'N/A')
    table.add_row('Cache', str(config.embedding_cache_path))
    console.print(table)


@app.command()
def status():
    """Mostra status atual do cache."""
    config = get_roteador_config()
    provider = _criar_provider()
    service = EmbeddingService(
        provider=provider,
        exemplos_path=config.exemplos_path,
        cache_path=config.embedding_cache_path,
    )

    total = len(service.exemplos)
    existentes = len(service._embeddings)
    pct = existentes / total * 100 if total else 0

    completo = existentes >= total
    status_icon = '[green]✅[/green] Sim' if completo else '[red]❌[/red] Não'

    table = Table(title='Status do Cache')
    table.add_column('Campo', style='cyan', no_wrap=True)
    table.add_column('Valor', style='white')
    table.add_row('Arquivo', str(config.embedding_cache_path))
    table.add_row('Exemplos', str(total))
    table.add_row('Embeddings', f'{existentes}/{total}')
    table.add_row('Progresso', f'{pct:.0f}%')
    table.add_row('Completo', status_icon)
    console.print(table)


@app.command()
def listar_exemplos():
    """Lista exemplos e indica se possuem embedding."""
    config = get_roteador_config()
    provider = _criar_provider()
    service = EmbeddingService(
        provider=provider,
        exemplos_path=config.exemplos_path,
        cache_path=config.embedding_cache_path,
    )

    table = Table(title='Exemplos no Cache')
    table.add_column('#', style='dim', width=4)
    table.add_column('Status', width=4)
    table.add_column('Texto', style='white')
    table.add_column('Intenção', style='cyan')

    for i, ex in enumerate(service.exemplos, 1):
        h = _hash_texto(ex.texto)
        tem = h in service._embeddings_dict
        icon = '[green]✅[/green]' if tem else '[red]❌[/red]'
        table.add_row(str(i), icon, ex.texto, ex.intencao)

    console.print(table)
    console.print(
        f'Total: [bold]{len(service.exemplos)}[/bold] | '
        f'Com embedding: [bold]{len(service._embeddings)}[/bold]'
    )


if __name__ == '__main__':
    app()
