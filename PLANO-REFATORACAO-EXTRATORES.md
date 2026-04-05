# Plano de Refatoração — Módulo `src/extratores/`

> **Objetivo:** Transformar `src/extratores/` de código procedural com side effects no import em um módulo OO com lazy initialization, models tipados e configuração externalizada.
>
> **Data:** 04/04/2026 · **Status:** Em planejamento

---

## Contexto

O módulo `src/extratores/` extrai itens do cardápio de mensagens de usuários usando **spaCy EntityRuler** como fonte primária e **rapidfuzz** como fallback. Identifica itens, quantidades, variantes e remoções.

**Problema central:** Código procedural com side effects no import (spaCy model load), estado global mutável, 6+ dict schemas sem tipo, duas funções `normalizar()` com semântica diferente, e `extrair_itens_troca()` com zero cobertura de testes.

---

## Princípios

1. **Zero side effects no import** — modelo spaCy só carrega sob demanda
2. **Single Responsibility** — cada função/classe faz uma coisa
3. **Models tipados** — dataclasses frozen para todos os schemas de retorno
4. **Configuração externalizada** — thresholds, stopwords, números em dataclass
5. **Sem globals mutáveis** — injeção de dependência via `NlpEngine`
6. **Compatibilidade retroativa** — `extrair()` retorna dicts durante transição
7. **TDD** — testes antes da implementação, especialmente para `extrair_itens_troca()`

---

## Estado Atual

```
src/extratores/
├── spacy_extrator.py     # 774 linhas — side effects, globals, 6 dict schemas
├── fuzzy_extrator.py     # 264 linhas — normalizar() duplicado, cutoffs hardcoded
└── __init__.py           # 39 linhas — re-export
```

## Estado Desejado

```
src/extratores/
├── __init__.py              # Re-export da API pública
├── modelos.py               # ItemExtraido, ExtracaoTroca, MatchCarrinho, etc.
├── config.py                # ExtratorConfig (thresholds, stopwords, numeros)
├── normalizador.py          # normalizar_para_busca(), normalizar_para_fuzzy()
├── nlp_engine.py            # NlpEngine — wrapper spaCy com lazy init
├── patterns.py              # Geração e cache de patterns do EntityRuler
├── remocoes.py              # capturar_remocoes() — lógica isolada
├── extrator.py              # extrair(), extrair_variante() — API principal
├── troca_extrator.py        # extrair_itens_troca() — lógica isolada
├── carrinho_extrator.py     # extrair_item_carrinho() — lógica isolada
└── fuzzy_extrator.py        # Mantido — fuzzy match (refatorado, sem duplicação)
```

---

## Arquivos que Somem / São Refatorados

| Arquivo Atual | Destino | Motivo |
|---|---|---|
| `spacy_extrator.py` (774 linhas) | Dividido em 6 arquivos | Responsabilidades misturadas |
| `fuzzy_extrator.py` (264 linhas) | Refatorado no lugar | Manter, mas unificar `normalizar()` |

---

## Inventário de Dict Schemas

| # | Schema | Chaves | Função que Retorna | Consumido Por |
|---|--------|--------|-------------------|---------------|
| 1 | `ItemExtraido` | `item_id`, `quantidade`, `variante`, `remocoes` | `extrair()` | `nodes.py`, `debug_cli.py` |
| 2 | `ExtracaoTroca` | `caso`, `item_original`, `variante_nova` | `extrair_itens_troca()` | `trocar.py` |
| 3 | `ItemOriginal` | `item_id`, `nome`, `indices` | Sub-schema de `ExtracaoTroca` | `trocar.py` |
| 4 | `MatchCarrinho` | `item_id`, `variante`, `indices` | `extrair_item_carrinho()` | `remover.py` |
| 5 | `ItemMencionado` | `texto`, `variante`, `ent_id` | Uso interno | `_buscar_matches_no_carrinho()` |
| 6 | `ItemCarrinhoRemocao` | `item_id`, `variante`, `indices` | `extrair_item_carrinho()` | `remover.py` |

---

## Models Propostos

```python
@dataclass(frozen=True)
class ItemExtraido:
    """Item extraído da mensagem do usuário."""
    item_id: str
    quantidade: int
    variante: str | None
    remocoes: list[str]

@dataclass(frozen=True)
class ExtracaoTroca:
    """Resultado da extração de troca."""
    caso: Literal['A', 'B', 'C', 'vazio']
    item_original: ItemOriginal | None
    variante_nova: str | None

@dataclass(frozen=True)
class ItemOriginal:
    """Item do carrinho identificado para troca."""
    item_id: str
    nome: str
    indices: list[int]

@dataclass(frozen=True)
class MatchCarrinho:
    """Match de item mencionado com item do carrinho."""
    item_id: str
    variante: str | None
    indices: list[int]

@dataclass(frozen=True)
class ItemMencionado:
    """Item mencionado na mensagem (uso interno)."""
    texto: str
    variante: str | None
    ent_id: str
```

---

## Camada 0 — Configuração

### Arquivo novo: `src/extratores/config.py`

```python
@dataclass(frozen=True)
class ExtratorConfig:
    fuzzy_item_cutoff: int = 75
    fuzzy_variante_cutoff: int = 75
    ambiguidade_limite: int = 5
    palavras_remocao: frozenset[str]
    palavras_parada: frozenset[str]
    conectivos: frozenset[str]
    pos_ignoraveis: frozenset[str]
    numeros_escritos: Mapping[str, int]
    stop_words: frozenset[str]
    spacy_model: str = 'pt_core_news_sm'
```

**Funções:**
- `get_extrator_config() -> ExtratorConfig` — lazy singleton

---

## Camada 1 — Models

### Arquivo novo: `src/extratores/modelos.py`

5 dataclasses frozen listadas acima.

**Por que `frozen=True`:** São valores de extração, não entidades. Imutabilidade evita bugs de estado compartilhado e permite uso em sets/dicts.

---

## Camada 2 — Normalizador Unificado

### Arquivo novo: `src/extratores/normalizador.py`

Duas funções nomeadas (sem flag):

```python
def normalizar_para_busca(texto: str) -> str:
    """Normaliza para busca no EntityRuler.
    
    Lowercase + unicode + remove pontuação + troca hífen por espaço.
    Ex: 'X-Tudo!' → 'xtudo'
    """

def normalizar_para_fuzzy(texto: str) -> str:
    """Normaliza para fuzzy matching.
    
    Lowercase + unicode + strip. Preserva pontuação interna.
    Ex: 'Hambúrguer!' → 'hamburguer!'
    """
```

**Decisão:** Duas funções nomeadas em vez de uma com flag. Mais explícito, sem comportamento condicional escondido.

---

## Camada 3 — NLP Engine

### Arquivo novo: `src/extratores/nlp_engine.py`

```python
class NlpEngine:
    """Wrapper do spaCy com lazy initialization.
    
    Elimina side effects no import. O modelo só é carregado
    na primeira chamada de processar().
    """

    def __init__(self, config: ExtratorConfig, cardapio: dict) -> None:
        self._config = config
        self._cardapio = cardapio
        self._nlp: spacy.language.Language | None = None
        self._ruler: EntityRuler | None = None

    def _inicializar(self) -> None:
        """Carrega modelo e configura EntityRuler (lazy)."""

    def processar(self, mensagem: str) -> spacy.tokens.Doc:
        """Processa mensagem com o pipeline NLP."""

    @property
    def inicializado(self) -> bool:
        """Retorna True se o modelo já foi carregado."""
```

**Decisão:** Lazy no `processar()` — quem instancia não paga o custo até usar. Compatível com testes que mockam o engine.

---

## Camada 4 — Patterns

### Arquivo novo: `src/extratores/patterns.py`

```python
def gerar_patterns(cardapio: dict, normalizar: Callable) -> list[dict]:
    """Gera patterns de entidade para o EntityRuler."""

def _adicionar_pattern(
    patterns: list[dict],
    vistos: set,
    label: str,
    texto_bruto: str,
    item_id: str,
) -> None:
    """Adiciona pattern evitando duplicatas."""
```

**Mudança:** Recebe função `normalizar` como parâmetro em vez de importar. Puro, testável.

---

## Camada 5 — Remoções

### Arquivo novo: `src/extratores/remocoes.py`

```python
def capturar_remocoes(doc: spacy.tokens.Doc, config: ExtratorConfig) -> list[tuple[str, int]]:
    """Captura itens a remover após sinais como 'sem', 'tira', etc."""
```

**Mudança:** Recebe `config` em vez de usar globals. Função pura.

---

## Camada 6 — Fuzzy (refatorado)

### Arquivo: `src/extratores/fuzzy_extrator.py` (modificado)

- Usa `normalizar_para_fuzzy()` do normalizador unificado
- Remove duplicação de `normalizar()`
- Recebe cutoffs como parâmetros (já faz isso)
- Mantém todas as 5 funções públicas

---

## Camada 7 — Extrator Principal

### Arquivo novo: `src/extratores/extrator.py`

```python
class Extrator:
    """Extrator de itens do cardápio via spaCy + fuzzy fallback."""

    def __init__(self, engine: NlpEngine, config: ExtratorConfig) -> None: ...

    def extrair(self, mensagem: str) -> list[ItemExtraido]: ...
    def extrair_variante(self, mensagem: str, item_id: str) -> str | None: ...
```

**Compatibilidade retroativa:**
```python
# API legada — retorna dicts
def extrair(mensagem: str) -> list[dict]:
    return [asdict(item) for item in _extrator.extrair(mensagem)]
```

---

## Camada 8 — Troca Extrator

### Arquivo novo: `src/extratores/troca_extrator.py`

```python
class TrocaExtrator:
    """Extrai informações de troca da mensagem."""

    def __init__(
        self,
        engine: NlpEngine,
        config: ExtratorConfig,
    ) -> None: ...

    def extrair(self, mensagem: str, carrinho: list[dict]) -> ExtracaoTroca: ...
```

**Nota:** Esta função tem **zero cobertura de testes** hoje. Os testes serão escritos **antes** da implementação (TDD).

---

## Camada 9 — Carrinho Extrator

### Arquivo novo: `src/extratores/carrinho_extrator.py`

```python
class CarrinhoExtrator:
    """Extrai itens do carrinho para remoção."""

    def __init__(
        self,
        engine: NlpEngine,
        config: ExtratorConfig,
    ) -> None: ...

    def extrair(self, mensagem: str, carrinho: list[dict]) -> list[MatchCarrinho]: ...
```

---

## Camada 10 — Migração

### Arquivos que mudam

| Arquivo | Mudança |
|---|---|
| `src/graph/nodes.py` | Usa `Extrator` injetado em vez de `extrair()` global |
| `src/graph/handlers/trocar.py` | Remove import de `_nlp`, usa `TrocaExtrator` |
| `src/graph/handlers/remover.py` | Usa `CarrinhoExtrator` |
| `src/graph/handlers/clarificacao.py` | Usa `normalizar_para_busca()` unificado |
| `src/observabilidade/debug_cli.py` | Usa API pública |
| `src/extratores/__init__.py` | Re-export da API compatível |

---

## Camada 11 — Testes

### Estratégia

1. **TDD para `extrair_itens_troca()`** — escrever testes antes (zero cobertura hoje)
2. **Tests de models** — imutabilidade, construção, igualdade
3. **Tests de config** — valores default, imutabilidade
4. **Tests de normalizador** — ambas as funções com edge cases
5. **Tests de NlpEngine** — lazy init, mock do spaCy
6. **Tests de extrator** — com engine mockado
7. **Tests de troca_extrator** — casos A, B, C, vazio, fuzzy fallback
8. **Tests de carrinho_extrator** — match por nome, variante, "tira tudo"

### Arquivos de teste

```
tests/src/extratores/
├── test_modelos.py
├── test_config.py
├── test_normalizador.py
├── test_nlp_engine.py
├── test_patterns.py
├── test_remocoes.py
├── test_extrator.py
├── test_troca_extrator.py          # NOVO — zero cobertura hoje
├── test_carrinho_extrator.py
└── test_fuzzy_extrator.py          # Atualizado
```

---

## Decisões Pendentes

| Decisão | Opções | Recomendação |
|---|---|---|
| `normalizar()` unificado | Flag vs duas funções | **Duas funções nomeadas** |
| NLP Engine lazy | No init vs primeira chamada | **Lazy no `processar()`** |
| Submódulo `fuzzy/` | Separar vs manter | **Manter no lugar** |
| Compatibilidade API | `list[dict]` vs `list[ItemExtraido]` | **`list[dict]` com `asdict()`** |
| `ExtratorConfig` singleton | Lazy vs injetado | **Lazy `get_extrator_config()`** |

---

## Riscos e Mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| spaCy `pt_core_news_sm` demora para carregar | Startup lento | Lazy init — só carrega no primeiro uso |
| `extrair_itens_troca()` sem testes | Regressão silenciosa | TDD — testes antes da implementação |
| Duas `normalizar()` com semântica diferente | Bugs sutis de matching | Unificar em duas funções nomeadas claras |
| Mudança na API quebra handlers | Runtime error | Manter `extrair()` retornando dicts durante transição |
| `_nlp` usado por `trocar.py` | Acoplamento a privado | Expor `processar()` no `NlpEngine` como API pública |

---

## Critérios de Aceite

- [ ] Zero side effects no import de qualquer módulo do `extratores`
- [ ] Zero variáveis globais mutáveis no `extratores`
- [ ] Todos os dict schemas substituídos por dataclasses
- [ ] `NlpEngine` com lazy initialization
- [ ] `normalizar()` unificada em duas funções nomeadas
- [ ] `extrair_itens_troca()` com cobertura de testes (era zero)
- [ ] `trocar.py` não importa mais `_nlp`
- [ ] Todos os testes passam (pytest)
- [ ] `ruff check .` sem erros
- [ ] `pyright` sem erros
- [ ] API `extrair(str) -> list[dict]` funciona (compatibilidade)

---

## Estimativa

| Camada | Arquivos | Linhas | Risco |
|---|---|---|---|
| 0. Config | 1 novo | ~60 | Baixo |
| 1. Models | 1 novo | ~80 | Baixo |
| 2. Normalizador | 1 novo | ~40 | Baixo |
| 3. NLP Engine | 1 novo | ~80 | Alto |
| 4. Patterns | 1 novo | ~60 | Baixo |
| 5. Remoções | 1 novo | ~80 | Médio |
| 6. Fuzzy | 1 modificado | ~264 | Médio |
| 7. Extrator | 1 novo | ~120 | Alto |
| 8. Troca | 1 novo | ~150 | Alto |
| 9. Carrinho | 1 novo | ~100 | Médio |
| 10. Migração | 6 modificados | ~200 | Médio |
| 11. Testes | ~10 arquivos | ~500 | Médio |
| **Total** | **~25 arquivos** | **~1.700 linhas** | |

---

## Ordem de Execução

1. Config + Models + Normalizador (fundação, sem dependências)
2. NLP Engine + Patterns (infraestrutura NLP)
3. Remoções + Fuzzy (lógica auxiliar)
4. Extrator principal + Troca + Carrinho (lógica de negócio)
5. Migração (atualizar consumidores)
6. Testes (TDD para troca, atualizar existentes)
