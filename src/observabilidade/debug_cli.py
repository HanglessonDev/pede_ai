"""CLI de debug para analisar logs do Pede AI."""

# ruff: noqa: S608  # CLI interna de debug, queries usam paths fixos do projeto

from pathlib import Path

import duckdb
import typer
from rich.console import Console
from rich.table import Table

from src.extratores import extrair

app = typer.Typer(help='Debug CLI para Pede AI')
console = Console()

LOG_DIR = Path('logs')


@app.command()
def ultima_sessao(thread_id: str | None = None) -> None:
    """Mostra a linha do tempo da ultima sessao ou de uma especifica."""
    if not LOG_DIR.exists():
        console.print('[red]Diretorio logs/ nao encontrado[/red]')
        raise typer.Exit(1)

    funil_csv = LOG_DIR / 'funil.csv'
    if not funil_csv.exists():
        console.print('[yellow]Nenhum log de funil encontrado[/yellow]')
        return

    conn = duckdb.connect()
    if thread_id:
        rows = conn.execute(
            f"SELECT * FROM '{funil_csv}' WHERE thread_id = '{thread_id}' ORDER BY timestamp"
        ).fetchall()
    else:
        rows = conn.execute(
            f"SELECT * FROM '{funil_csv}' ORDER BY timestamp DESC LIMIT 20"
        ).fetchall()

    cols = [
        desc[0]
        for desc in conn.execute(f"SELECT * FROM '{funil_csv}' LIMIT 1").description
    ]

    table = Table(title='Funil de Pedidos')
    for col in cols:
        table.add_column(col)
    for row in rows:
        table.add_row(*[str(v) for v in row])
    console.print(table)
    conn.close()


@app.command()
def extracoes_falhas() -> None:
    """Mostra mensagens onde nenhum item foi extraido."""
    extracao_csv = LOG_DIR / 'extracoes.csv'
    if not extracao_csv.exists():
        console.print('[yellow]Nenhum log de extracao encontrado[/yellow]')
        return

    conn = duckdb.connect()
    rows = conn.execute(
        f"SELECT mensagem, tempo_ms FROM '{extracao_csv}' WHERE itens_encontrados = 0 ORDER BY timestamp DESC LIMIT 20"
    ).fetchall()

    table = Table(title='Extracoes sem Resultados')
    table.add_column('Mensagem')
    table.add_column('Tempo (ms)')
    for row in rows:
        table.add_row(row[0], f'{row[1]:.2f}')
    console.print(table)
    conn.close()


@app.command()
def erros_handlers() -> None:
    """Mostra erros em handlers."""
    handler_csv = LOG_DIR / 'handlers.csv'
    if not handler_csv.exists():
        console.print('[yellow]Nenhum log de handler encontrado[/yellow]')
        return

    conn = duckdb.connect()
    rows = conn.execute(
        f"SELECT handler, intent, erro, tempo_ms FROM '{handler_csv}' WHERE erro != '' ORDER BY timestamp DESC LIMIT 20"
    ).fetchall()

    table = Table(title='Erros em Handlers')
    table.add_column('Handler')
    table.add_column('Intent')
    table.add_column('Erro')
    table.add_column('Tempo (ms)')
    for row in rows:
        table.add_row(row[0], row[1], row[2], f'{row[3]:.2f}')
    console.print(table)
    conn.close()


@app.command()
def classificar(mensagem: str) -> None:
    """Testa classificacao de uma mensagem sem executar o grafo.

    Nota: requer classificador configurado via main.py.
    Use 'python main.py' para teste interativo completo.
    """
    console.print('[yellow]Classificacao CLI desabilitada na refatoracao.[/yellow]')
    console.print(
        '[dim]Use o main.py para teste interativo com Groq + Transformers.[/dim]'
    )


@app.command()
def extrair_teste(mensagem: str) -> None:
    """Testa extracao de itens de uma mensagem."""
    itens = extrair(mensagem)
    if not itens:
        console.print(f'[red]Nenhum item extraido de "{mensagem}"[/red]')
        return

    table = Table(title=f'Extracao: "{mensagem}"')
    table.add_column('item_id')
    table.add_column('quantidade')
    table.add_column('variante')
    table.add_column('remocoes')
    for item in itens:
        table.add_row(
            item['item_id'],
            str(item['quantidade']),
            str(item.get('variante')),
            ', '.join(item.get('remocoes', [])),
        )
    console.print(table)


if __name__ == '__main__':
    app()
