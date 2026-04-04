# Expansão do Módulo de Observabilidade — Debug Completo

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expandir o módulo de observabilidade para capturar eventos de todas as etapas do fluxo de pedido, permitindo debug rápido de problemas como o bug do "suco".

**Architecture:** Adicionar loggers CSV em cada node/handler crítico do LangGraph, criar um script CLI de debug que agrega logs em tempo real, e estender as consultas DuckDB para análise de funil de pedidos.

**Tech Stack:** Python CSV logging, DuckDB SQL, Typer CLI, Rich para output formatado

---

## Problema Atual

Quando o usuário pede "suco", o bot quebra em algum ponto do fluxo. Sem observabilidade adequada, precisamos chutar onde está o erro:
- O roteador classifica como "pedir"?
- O extrator spaCy encontra "Suco Natural"?
- O handler de pedir calcula o preço corretamente?
- A clarificação de variante (300ml/500ml) funciona?

**Solução:** Instrumentar TODO o pipeline para capturar eventos em cada etapa.

## Arquivos a Criar/Modificar

### Criar:
- `src/observabilidade/extracao_logger.py` — Logger de extração de itens
- `src/observabilidade/handler_logger.py` — Logger genérico de handlers
- `src/observabilidade/funil_logger.py` — Logger de progressão de funil
- `src/observabilidade/debug_cli.py` — Script CLI para debug interativo
- `src/observabilidade/consultas.py` (expandir) — Novas consultas DuckDB
- `tests/src/observabilidade/test_extracao_logger.py`
- `tests/src/observabilidade/test_handler_logger.py`
- `tests/src/observabilidade/test_funil_logger.py`
- `tests/src/observabilidade/test_debug_cli.py`

### Modificar:
- `src/observabilidade/registry.py` — Adicionar novos setters/getters
- `src/observabilidade/__init__.py` — Exportar novos módulos
- `src/graph/nodes.py` — Adicionar logs nos nodes
- `src/graph/handlers/pedir.py` — Adicionar log de processamento
- `src/graph/handlers/trocar.py` — Adicionar log de trocas
- `src/graph/handlers/clarificacao.py` — Adicionar log de clarificações
- `main.py` — Inicializar novos loggers

---

## Task 1: Logger de Extração de Itens

**Files:**
- Create: `src/observabilidade/extracao_logger.py`
- Test: `tests/src/observabilidade/test_extracao_logger.py`

### Step 1: Write the failing test

```python
# tests/src/observabilidade/test_extracao_logger.py
import csv
from pathlib import Path
from src.observabilidade.extracao_logger import ExtracaoLogger, HEADERS

def test_registra_extracao_sucesso(tmp_path: Path) -> None:
    """Testa registro de extração bem-sucedida."""
    csv_path = tmp_path / 'extracoes.csv'
    logger = ExtracaoLogger(csv_path)
    
    logger.registrar(
        thread_id='sessao_1',
        mensagem='quero um suco de laranja',
        itens_extraidos=[{
            'item_id': 'bebida_004',
            'quantidade': 1,
            'variante': None,
            'remocoes': [],
        }],
        tempo_ms=45.2,
    )
    
    assert csv_path.exists()
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    assert len(rows) == 1
    assert rows[0]['thread_id'] == 'sessao_1'
    assert rows[0]['itens_encontrados'] == '1'
    assert rows[0]['tempo_ms'] == '45.2'
```

### Step 2: Run test to verify it fails

```bash
pytest tests/src/observabilidade/test_extracao_logger.py::test_registra_extracao_sucesso -v
```
Expected: FAIL with "ModuleNotFoundError: No module named 'src.observabilidade.extracao_logger'"

### Step 3: Write minimal implementation

```python
# src/observabilidade/extracao_logger.py
"""Logger para eventos de extração de itens."""

import csv
import threading
from datetime import UTC, datetime
from pathlib import Path

HEADERS = [
    'timestamp',
    'thread_id',
    'mensagem',
    'itens_encontrados',
    'itens_ids',
    'variantes_encontradas',
    'tempo_ms',
]


class ExtracaoLogger:
    """Logger thread-safe para registrar eventos de extração.
    
    Cada linha registra o resultado do extrator spaCy.
    """

    def __init__(self, csv_path: Path | str) -> None:
        self.csv_path = Path(csv_path)
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._inicializar_csv()

    def _inicializar_csv(self) -> None:
        with self._lock:
            if not self.csv_path.exists():
                with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(HEADERS)

    def registrar(
        self,
        thread_id: str,
        mensagem: str,
        itens_extraidos: list[dict],
        tempo_ms: float,
    ) -> None:
        with self._lock, open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now(UTC).isoformat(),
                thread_id,
                mensagem,
                len(itens_extraidos),
                '|'.join(i.get('item_id', '') for i in itens_extraidos),
                '|'.join(i.get('variante', '') or 'None' for i in itens_extraidos),
                f'{tempo_ms:.2f}',
            ])
```

### Step 4: Run test to verify it passes

```bash
pytest tests/src/observabilidade/test_extracao_logger.py -v
```

### Step 5: Commit

```bash
git add src/observabilidade/extracao_logger.py tests/src/observabilidade/test_extracao_logger.py
git commit -m "feat(observabilidade): :sparkles: adiciona logger de extração de itens"
```

---

## Task 2: Logger Genérico de Handlers

**Files:**
- Create: `src/observabilidade/handler_logger.py`
- Test: `tests/src/observabilidade/test_handler_logger.py`

### Step 1: Write the failing test

```python
# tests/src/observabilidade/test_handler_logger.py
import csv
from pathlib import Path
from src.observabilidade.handler_logger import HandlerLogger, HEADERS

def test_registra_execucao_handler(tmp_path: Path) -> None:
    """Testa registro de execução de handler."""
    csv_path = tmp_path / 'handlers.csv'
    logger = HandlerLogger(csv_path)
    
    logger.registrar(
        thread_id='sessao_1',
        handler='handler_pedir',
        intent='pedir',
        input_dados={'itens_extraidos': [{'item_id': 'bebida_004'}]},
        output_dados={'carrinho': [{'item_id': 'bebida_004', 'preco': 500}]},
        tempo_ms=12.5,
        erro=None,
    )
    
    assert csv_path.exists()
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    assert len(rows) == 1
    assert rows[0]['handler'] == 'handler_pedir'
    assert rows[0]['erro'] == ''
```

### Step 2: Run test to verify it fails

```bash
pytest tests/src/observabilidade/test_handler_logger.py::test_registra_execucao_handler -v
```

### Step 3: Write minimal implementation

```python
# src/observabilidade/handler_logger.py
"""Logger genérico para execução de handlers."""

import csv
import json
import threading
from datetime import UTC, datetime
from pathlib import Path

HEADERS = [
    'timestamp',
    'thread_id',
    'handler',
    'intent',
    'input_resumo',
    'output_resumo',
    'tempo_ms',
    'erro',
]


class HandlerLogger:
    """Logger thread-safe para registrar execuções de handlers."""

    def __init__(self, csv_path: Path | str) -> None:
        self.csv_path = Path(csv_path)
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._inicializar_csv()

    def _inicializar_csv(self) -> None:
        with self._lock:
            if not self.csv_path.exists():
                with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(HEADERS)

    def registrar(
        self,
        thread_id: str,
        handler: str,
        intent: str,
        input_dados: dict,
        output_dados: dict,
        tempo_ms: float,
        erro: str | None = None,
    ) -> None:
        with self._lock, open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now(UTC).isoformat(),
                thread_id,
                handler,
                intent,
                json.dumps(input_dados, ensure_ascii=False)[:200],
                json.dumps(output_dados, ensure_ascii=False)[:200],
                f'{tempo_ms:.2f}',
                erro or '',
            ])
```

### Step 4: Run test to verify it passes

```bash
pytest tests/src/observabilidade/test_handler_logger.py -v
```

### Step 5: Commit

```bash
git add src/observabilidade/handler_logger.py tests/src/observabilidade/test_handler_logger.py
git commit -m "feat(observabilidade): :sparkles: adiciona logger genérico de handlers"
```

---

## Task 3: Logger de Funil de Pedidos

**Files:**
- Create: `src/observabilidade/funil_logger.py`
- Test: `tests/src/observabilidade/test_funil_logger.py`

### Step 1: Write the failing test

```python
# tests/src/observabilidade/test_funil_logger.py
import csv
from pathlib import Path
from src.observabilidade.funil_logger import FunilLogger, HEADERS

def test_registra_transicao_funil(tmp_path: Path) -> None:
    """Testa registro de transição no funil."""
    csv_path = tmp_path / 'funil.csv'
    logger = FunilLogger(csv_path)
    
    logger.registrar(
        thread_id='sessao_1',
        etapa_anterior='inicio',
        etapa_atual='saudacao',
        intent='saudacao',
    )
    
    assert csv_path.exists()
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    assert len(rows) == 1
    assert rows[0]['etapa_anterior'] == 'inicio'
    assert rows[0]['etapa_atual'] == 'saudacao'
```

### Step 2: Run test to verify it fails

### Step 3: Write minimal implementation

```python
# src/observabilidade/funil_logger.py
"""Logger para progressão no funil de pedidos."""

import csv
import threading
from datetime import UTC, datetime
from pathlib import Path

HEADERS = [
    'timestamp',
    'thread_id',
    'etapa_anterior',
    'etapa_atual',
    'intent',
    'carrinho_size',
]


class FunilLogger:
    """Logger thread-safe para registrar transições no funil."""

    def __init__(self, csv_path: Path | str) -> None:
        self.csv_path = Path(csv_path)
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._inicializar_csv()

    def _inicializar_csv(self) -> None:
        with self._lock:
            if not self.csv_path.exists():
                with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(HEADERS)

    def registrar(
        self,
        thread_id: str,
        etapa_anterior: str,
        etapa_atual: str,
        intent: str,
        carrinho_size: int = 0,
    ) -> None:
        with self._lock, open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now(UTC).isoformat(),
                thread_id,
                etapa_anterior,
                etapa_atual,
                intent,
                carrinho_size,
            ])
```

### Step 4: Run test to verify it passes

### Step 5: Commit

```bash
git add src/observabilidade/funil_logger.py tests/src/observabilidade/test_funil_logger.py
git commit -m "feat(observabilidade): :sparkles: adiciona logger de funil de pedidos"
```

---

## Task 4: Expandir Registry e __init__

**Files:**
- Modify: `src/observabilidade/registry.py`
- Modify: `src/observabilidade/__init__.py`
- Test: `tests/src/observabilidade/test_registry.py` (expandir)

### Step 1: Add new loggers to registry

```python
# src/observabilidade/registry.py — adicionar após _clarificacao
_extracao: ExtracaoLogger | None = None
_handler: HandlerLogger | None = None
_funil: FunilLogger | None = None

# Adicionar getters/setters para cada novo logger
def get_extracao_logger() -> ExtracaoLogger | None:
    return _extracao

def set_extracao_logger(logger: ExtracaoLogger | None) -> None:
    global _extracao
    _extracao = logger

# Repetir padrão para handler e funil
```

### Step 2: Update __init__.py exports

```python
# src/observabilidade/__init__.py
from src.observabilidade.logger import ObservabilidadeLogger
from src.observabilidade.clarificacao_logger import ClarificacaoLogger
from src.observabilidade.extracao_logger import ExtracaoLogger
from src.observabilidade.handler_logger import HandlerLogger
from src.observabilidade.funil_logger import FunilLogger
from src.observabilidade.registry import (
    get_obs_logger, set_obs_logger,
    get_clarificacao_logger, set_clarificacao_logger,
    get_extracao_logger, set_extracao_logger,
    get_handler_logger, set_handler_logger,
    get_funil_logger, set_funil_logger,
)

__all__ = [
    'ObservabilidadeLogger',
    'ClarificacaoLogger',
    'ExtracaoLogger',
    'HandlerLogger',
    'FunilLogger',
    # ... getters/setters
]
```

### Step 3: Test and commit

```bash
pytest tests/src/observabilidade/test_registry.py -v
git add -A && git commit -m "feat(observabilidade): :sparkles: registra novos loggers no registry"
```

---

## Task 5: Instrumentar Nodes do Graph

**Files:**
- Modify: `src/graph/nodes.py`
- Test: `tests/src/graph/test_nodes.py` (verificar que logs são chamados)

### Step 1: Add timing and logging to node_router

```python
# src/graph/nodes.py — adicionar no topo do arquivo (NUNCA inline)
import time
from langgraph.config import get_config
from src.observabilidade.registry import get_funil_logger, get_handler_logger

def node_router(state: State) -> RetornoNode:
    inicio = time.monotonic()
    mensagem = state.get('mensagem_atual', '')
    thread_id = get_config().get('configurable', {}).get('thread_id', '')
    etapa_anterior = state.get('etapa', 'inicio')
    
    resultado = _classificar_intencao(mensagem, thread_id=thread_id)
    
    # ... log obs existente ...
    
    # Log de funil
    funil_logger = get_funil_logger()
    if funil_logger:
        funil_logger.registrar(
            thread_id=thread_id,
            etapa_anterior=etapa_anterior,
            etapa_atual='roteado',
            intent=resultado['intent'],
            carrinho_size=len(state.get('carrinho', [])),
        )
    
    tempo_ms = (time.monotonic() - inicio) * 1000
    
    # Log de handler
    handler_logger = get_handler_logger()
    if handler_logger:
        handler_logger.registrar(
            thread_id=thread_id,
            handler='node_router',
            intent=resultado['intent'],
            input_dados={'mensagem': mensagem},
            output_dados=resultado,
            tempo_ms=tempo_ms,
        )
    
    return {
        'intent': resultado['intent'],
        'confidence': resultado['confidence'],
    }
```

### Step 2: Instrument node_extrator

**Adicionar no topo do arquivo `nodes.py`:**

```python
# No topo do nodes.py (já deve existir)
import time
from langgraph.config import get_config
from src.observabilidade.registry import get_extracao_logger
```

**Modificar função existente:**

```python
def node_extrator(state: State) -> RetornoNode:
    inicio = time.monotonic()
    mensagem = state.get('mensagem_atual', '')
    thread_id = get_config().get('configurable', {}).get('thread_id', '')
    
    if state.get('intent') == 'pedir':
        itens = extrair(mensagem)
        tempo_ms = (time.monotonic() - inicio) * 1000
        
        # Log extração
        ext_logger = get_extracao_logger()
        if ext_logger:
            ext_logger.registrar(
                thread_id=thread_id,
                mensagem=mensagem,
                itens_extraidos=itens,
                tempo_ms=tempo_ms,
            )
        
        return {'itens_extraidos': itens}
    return {'itens_extraidos': []}
```

### Step 3: Test and commit

```bash
pytest tests/src/graph/test_nodes.py -v
git add src/graph/nodes.py && git commit -m "feat(graph): :sparkles: instrumenta nodes com logs de observabilidade"
```

---

## Task 6: Instrumentar Handler Pedir

**Files:**
- Modify: `src/graph/handlers/pedir.py`

### Step 1: Add logging to processar_pedido

```python
# src/graph/handlers/pedir.py — adicionar no topo
import time
from src.observabilidade.registry import get_handler_logger

def processar_pedido(
    itens_extraidos: list[dict],
    carrinho_existente: list[dict],
    thread_id: str = '',
) -> ResultadoPedir:
    inicio = time.monotonic()
    
    # ... código existente ...
    
    resultado = ResultadoPedir(carrinho=carrinho, fila=fila, resposta=resposta)
    
    # Log
    handler_logger = get_handler_logger()
    if handler_logger:
        tempo_ms = (time.monotonic() - inicio) * 1000
        handler_logger.registrar(
            thread_id=thread_id,
            handler='handler_pedir',
            intent='pedir',
            input_dados={'itens_extraidos': itens_extraidos},
            output_dados={
                'carrinho_size': len(carrinho),
                'fila_size': len(fila),
            },
            tempo_ms=tempo_ms,
        )
    
    return resultado
```

### Step 2: Update node_handler_pedir to pass thread_id

```python
def node_handler_pedir(state: State) -> RetornoNode:
    thread_id = get_config().get('configurable', {}).get('thread_id', '')
    itens_extraidos = state.get('itens_extraidos') or []
    carrinho = state.get('carrinho', [])
    resultado = processar_pedido(itens_extraidos, carrinho, thread_id=thread_id)
    return resultado.to_dict()
```

### Step 3: Test and commit

```bash
pytest tests/src/graph/handlers/test_pedir.py -v
git add -A && git commit -m "feat(handlers): :sparkles: instrumenta handler_pedir com logs"
```

---

## Task 7: Expandir Consultas DuckDB

**Files:**
- Modify: `src/observabilidade/consultas.py`
- Test: `tests/src/observabilidade/test_consultas.py` (expandir)

### Step 1: Add new queries

```python
# src/observabilidade/consultas.py — adicionar funções

def extracoes_sem_itens(csv_extracao: str, limit: int = 20) -> list[dict]:
    """Retorna mensagens onde extrator não encontrou itens.
    
    Útil para debug de itens que deveriam ser reconhecidos.
    """
    conn = duckdb.connect()
    query = f"""
        SELECT mensagem, itens_encontrados, tempo_ms
        FROM '{csv_extracao}'
        WHERE itens_encontrados = 0
        ORDER BY timestamp DESC
        LIMIT {limit}
    """
    rows = conn.execute(query).fetchall()
    cols = [desc[0] for desc in conn.execute(query).description]
    conn.close()
    return [dict(zip(cols, row, strict=True)) for row in rows]


def funil_com_abandono(csv_funil: str, thread_id: str | None = None) -> list[dict]:
    """Analisa sessões que pararam em etapas intermediárias."""
    where = f"WHERE thread_id = '{thread_id}'" if thread_id else ''
    conn = duckdb.connect()
    query = f"""
        SELECT thread_id, etapa_atual, intent, carrinho_size,
               timestamp
        FROM '{csv_funil}'
        {where}
        ORDER BY timestamp DESC
        LIMIT 50
    """
    rows = conn.execute(query).fetchall()
    cols = [desc[0] for desc in conn.execute(query).description]
    conn.close()
    return [dict(zip(cols, row, strict=True)) for row in rows]


def handlers_com_erro(csv_handler: str, limit: int = 20) -> list[dict]:
    """Retorna execuções de handlers com erro."""
    conn = duckdb.connect()
    query = f"""
        SELECT handler, intent, input_resumo, erro, tempo_ms
        FROM '{csv_handler}'
        WHERE erro != ''
        ORDER BY timestamp DESC
        LIMIT {limit}
    """
    rows = conn.execute(query).fetchall()
    cols = [desc[0] for desc in conn.execute(query).description]
    conn.close()
    return [dict(zip(cols, row, strict=True)) for row in rows]


def tempo_medio_handlers(csv_handler: str) -> list[dict]:
    """Retorna tempo médio por handler."""
    conn = duckdb.connect()
    query = f"""
        SELECT handler, 
               AVG(tempo_ms) as tempo_medio_ms,
               COUNT(*) as total_execucoes
        FROM '{csv_handler}'
        GROUP BY handler
        ORDER BY tempo_medio_ms DESC
    """
    rows = conn.execute(query).fetchall()
    cols = [desc[0] for desc in conn.execute(query).description]
    conn.close()
    return [dict(zip(cols, row, strict=True)) for row in rows]
```

### Step 2: Test and commit

```bash
pytest tests/src/observabilidade/test_consultas.py -v
git add -A && git commit -m "feat(observabilidade): :sparkles: adiciona consultas de debug ao DuckDB"
```

---

## Task 8: CLI de Debug Interativo

**Files:**
- Create: `src/observabilidade/debug_cli.py`
- Test: `tests/src/observabilidade/test_debug_cli.py`

### Step 1: Create debug CLI with Typer

```python
# src/observabilidade/debug_cli.py
"""CLI de debug para analisar logs do Pede AI."""

from pathlib import Path

import duckdb
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help='Debug CLI para Pede AI')
console = Console()

LOG_DIR = Path('logs')


@app.command()
def ultima_sessao(thread_id: str | None = None) -> None:
    """Mostra a linha do tempo da última sessão ou de uma específica."""
    if not LOG_DIR.exists():
        console.print('[red]Diretório logs/ não encontrado[/red]')
        raise typer.Exit(1)
    
    # Consulta funil
    funil_csv = LOG_DIR / 'funil.csv'
    if funil_csv.exists():
        conn = duckdb.connect()
        if thread_id:
            rows = conn.execute(
                f"SELECT * FROM '{funil_csv}' WHERE thread_id = '{thread_id}' ORDER BY timestamp"
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT * FROM '{funil_csv}' ORDER BY timestamp DESC LIMIT 20"
            ).fetchall()
        
        cols = [desc[0] for desc in conn.execute(
            f"SELECT * FROM '{funil_csv}' LIMIT 1"
        ).description]
        
        table = Table(title='Funil de Pedidos')
        for col in cols:
            table.add_column(col)
        for row in rows:
            table.add_row(*[str(v) for v in row])
        console.print(table)


@app.command()
def extracoes_falhas() -> None:
    """Mostra mensagens onde nenhum item foi extraído."""
    extracao_csv = LOG_DIR / 'extracoes.csv'
    if not extracao_csv.exists():
        console.print('[yellow]Nenhum log de extração encontrado[/yellow]')
        return
    
    conn = duckdb.connect()
    rows = conn.execute(
        f"SELECT mensagem, tempo_ms FROM '{extracao_csv}' WHERE itens_encontrados = 0 ORDER BY timestamp DESC LIMIT 20"
    ).fetchall()
    
    table = Table(title='Extrações sem Resultados')
    table.add_column('Mensagem')
    table.add_column('Tempo (ms)')
    for row in rows:
        table.add_row(row[0], f'{row[1]:.2f}')
    console.print(table)


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


@app.command()
classificar(mensagem: str) -> None:
    """Testa classificação de uma mensagem sem executar o grafo."""
    from src.roteador.classificador_intencoes import _classificar_intencao
    
    resultado = _classificar_intencao(mensagem)
    table = Table(title=f'Classificação: "{mensagem}"')
    table.add_column('Campo')
    table.add_column('Valor')
    for k, v in resultado.items():
        table.add_column(str(k))
        table.add_row(str(k), str(v))
    console.print(table)


@app.command()
def extrair_teste(mensagem: str) -> None:
    """Testa extração de itens de uma mensagem."""
    from src.extratores import extrair
    
    itens = extrair(mensagem)
    if not itens:
        console.print(f'[red]Nenhum item extraído de "{mensagem}"[/red]')
        return
    
    table = Table(title=f'Extração: "{mensagem}"')
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
```

### Step 2: Test the CLI manually

```bash
uv run python -m src.observabilidade.debug_cli extracoes-falhas
uv run python -m src.observabilidade.debug_cli classificar "quero um suco"
uv run python -m src.observabilidade.debug_cli extrair-teste "quero um suco de laranja"
```

### Step 3: Add automated tests

```python
# tests/src/observabilidade/test_debug_cli.py
from typer.testing import CliRunner
from src.observabilidade.debug_cli import app

runner = CliRunner()

def test_app_exists() -> None:
    """Testa que a CLI foi criada."""
    result = runner.invoke(app, ['--help'])
    assert result.exit_code == 0

def test_comando_classificar() -> None:
    """Testa comando de classificação."""
    result = runner.invoke(app, ['classificar', 'oi'])
    assert result.exit_code == 0
    assert 'saudacao' in result.text.lower() or 'intent' in result.text.lower()
```

### Step 4: Commit

```bash
git add -A && git commit -m "feat(observabilidade): :sparkles: adiciona CLI de debug interativo"
```

---

## Task 9: Atualizar main.py e Integrar

**Files:**
- Modify: `main.py`

### Step 1: Add new loggers to main.py

```python
# main.py — adicionar imports
from src.observabilidade.extracao_logger import ExtracaoLogger
from src.observabilidade.handler_logger import HandlerLogger
from src.observabilidade.funil_logger import FunilLogger
from src.observabilidade.registry import (
    set_extracao_logger,
    set_handler_logger,
    set_funil_logger,
)

# Após configuração existente
set_extracao_logger(ExtracaoLogger(LOG_DIR / 'extracoes.csv'))
set_handler_logger(HandlerLogger(LOG_DIR / 'handlers.csv'))
set_funil_logger(FunilLogger(LOG_DIR / 'funil.csv'))
```

### Step 2: Update print to show more debug info

```python
# No loop principal, adicionar mais info
print(f'Bot: {resultado.get("resposta", "???")}')
print(
    f'[etapa={resultado.get("etapa")} | intent={resultado.get("intent")} | '
    f'confidence={resultado.get("confidence", 0):.2f} | '
    f'carrinho={len(resultado.get("carrinho", []))} itens]'
)
```

### Step 3: Test full flow

```bash
uv run python main.py
# Testar: "oi" -> "quero suco de laranja" -> verificar logs
```

### Step 4: Commit

```bash
git add main.py && git commit -m "feat(main): :sparkles: integra novos loggers ao entry point"
```

---

## Task 10: Teste End-to-End do Debug

**Files:** Nenhum arquivo novo

### Step 1: Run full interactive test

```bash
uv run python main.py
```

Interagir:
1. "oi"
2. "quero um suco de laranja"
3. Verificar logs gerados em `logs/`

### Step 2: Analyze logs with CLI

```bash
uv run python -m src.observabilidade.debug_cli extracoes-falhas
uv run python -m src.observabilidade.debug_cli ultima-sessao
```

### Step 3: Run full test suite

```bash
pytest tests/src/observabilidade/ -v
ruff check .
pyright
```

### Step 4: Final commit

```bash
git add -A && git commit -m "feat(observabilidade): :tada: completa expansão do módulo de observabilidade"
```

---

## Próximos Passos (Fora do Escopo)

- Integração com dashboard web (Streamlit/Gradio)
- Alertas automáticos quando taxa de erro > threshold
- Logs de performance do LLM (tokens, tempo de resposta)
- Export de métricas para Prometheus/Grafana
- Trace distribuído (OpenTelemetry)
