# Relatório de Estado Global — Pede AI

> "Code is clean if it can be read, and enhanced by a developer other than its original author."

**Data:** 04/04/2026 · **Versão:** 1.0

---

## Sumário Executivo

O Pede AI é um chatbot de pedidos com IA para lanchonetes, construído com **LangGraph**, **spaCy** e **Ollama** (LLM local). O sistema classifica intenções via RAG + LLM, extrai itens do cardápio com NLP e gerencia um fluxo conversacional de pedidos.

**Problema central:** O projeto é **inteiramente procedural** — zero models orientados a objetos. São **12+ dict schemas** diferentes espalhados por **20 arquivos fonte**, tratados como "poor man's objects". Dados e comportamento estão separados onde deveriam estar juntos.

### Métricas Globais

| Métrica | Valor |
|---|---|
| Arquivos fonte | 20 |
| Linhas de código (src/) | ~4.047 |
| Arquivos de teste | 27 |
| Linhas de teste | ~3.000+ |
| Funções livres | ~70 |
| Classes propriamente ditas | 11 (5 loggers, 4 dataclasses, 2 cache) |
| Dicts como "objetos pobres" | 12+ schemas distintos |
| Lógica duplicada | 6+ instâncias |
| Números mágicos | 12+ |
| Efeitos colaterais no import | 3 arquivos |
| Vulnerabilidades SQL injection | 4 locais |
| Código morto | 3 itens |

---

## 1. Módulo `src/config/` — Configuração

### `cardapio.py` (197 linhas)

**Responsabilidade:** Carrega e cacheia o cardápio do YAML.

**Estruturas de dados:**

| Dict Shape | Chaves |
|---|---|
| Cardápio root | `itens`, `remocoes_genericas`, `observacoes_genericas`, `tenant_id`, `tenant_nome` |
| Item do cardápio | `id`, `nome`, `categoria`, `preco`, `aliases`, `variantes` |
| Variante | `opcao`, `preco` |

**Funções:** `get_cardapio()`, `get_item_por_id()`, `get_itens_por_categoria()`, `get_remocoes_genericas()`, `get_observacoes_genericas()`, `get_variantes()`, `get_preco_item()`, `get_nome_item()`

**Code smells:**
- Cache mutável em nível de módulo (`_CardapioCache` com atributos de classe) — sem mecanismo de invalidação
- `CONFIG_DIR` hardcoded relativo a `__file__`
- Sem tratamento de erro para YAML ausente ou malformado (usa `assert`)
- **Deveria ser:** `Cardapio`, `ItemCardapio`, `VarianteCardapio` como dataclasses com métodos como `por_id()`, `tem_variantes()`, `preco_base()`

### `prompts.py` (110 linhas)

**Responsabilidade:** Carrega prompts e info do tenant do YAML com cache.

**Dict shapes:**
- Prompts: `{nome: {'prompt': str, 'intencoes_validas': [...]}}`
- Tenant info: `{'tenant_id': str, 'tenant_nome': str}`

**Code smells:**
- `CONFIG_DIR` duplicado de `cardapio.py` (DRY violation)
- `get_prompt()` acessa dict aninhado sem `.get()` — levanta `KeyError` se faltar
- Mesmo pattern de cache mutável sem invalidação

### `__init__.py` (48 linhas)

Facade de re-export. Sem problemas.

---

## 2. Módulo `src/extratores/` — Extração NLP

### `spacy_extrator.py` (776 linhas) — **ARQUIVO MAIS CRÍTICO**

**Responsabilidade:** Extração de itens do cardápio via spaCy EntityRuler — identifica itens, quantidades, variantes e remoções.

**Dict shapes usados como "objetos":**

| Dict Shape | Chaves | Usado Em |
|---|---|---|
| Item extraído | `item_id`, `quantidade`, `variante`, `remocoes` | `pedir.py`, `nodes.py`, testes |
| Item do carrinho | `item_id`, `quantidade`, `variante`, `preco` | `nodes.py`, `utils.py`, handlers |
| Extração de troca | `caso`, `item_original`, `variante_nova` | `trocar.py` |
| Item original | `item_id`, `nome`, `indices` | `trocar.py`, `spacy_extrator.py` |
| Item mencionado | `texto`, `variante`, `ent_id` | `spacy_extrator.py` |
| Match carrinho | `item_id`, `variante`, `indices` | `spacy_extrator.py`, `remover.py` |

**Code smells:**
- **Side effects no import** (linhas 277-283): `spacy.load()`, `add_pipe()`, `add_patterns()` rodam ao importar — startup lento, difícil de testar
- **Estado global mutável:** `_nlp`, `_ruler`, `_cardapio`, `_patterns` são globals de módulo
- `extrair_itens_troca()` usa strings mágicas `'A'`, `'B'`, `'C'`, `'vazio'` como códigos de caso — sem TypedDict ou Enum
- Função `extrair_itens_troca()` com 80+ linhas e múltiplos caminhos
- `_fallback_fuzzy_completo` reconstrói `alias_para_id` a cada chamada — deveria ser cacheado
- `nonlocal` closure `_consumir_remocoes_ate` — lógica aninhada complexa
- Strings mágicas `'ITEM'`, `'VARIANTE'`, `'QTD'` sem constantes

**Deveria ser:** `ItemExtraido`, `MatchCarrinho`, `ExtracaoTroca`, `ItemOriginal`, `ItemMencionado` como dataclasses.

### `fuzzy_extrator.py` (264 linhas)

**Responsabilidade:** Fuzzy matching de nomes de itens e variantes com rapidfuzz.

**Code smells:**
- `normalizar()` duplicada — lógica quase idêntica à de `spacy_extrator.py`
- Números mágicos `75` e `5` como cutoffs — documentados mas hardcoded
- Cria lista desnecessária `[*tokens, normalizar(texto)]`

### `__init__.py` (39 linhas)

Re-export. Sem problemas.

---

## 3. Módulo `src/graph/` — Grafo LangGraph

### `state.py` (90 linhas)

**Responsabilidade:** Define o TypedDict `State` do LangGraph e as etapas do fluxo.

**Estrutura:**

```python
class State(TypedDict):
    mensagem_atual: str
    intent: str
    confidence: float
    itens_extraidos: list          # sem tipo!
    carrinho: list                 # sem tipo!
    fila_clarificacao: list        # sem tipo!
    etapa: ETAPAS
    resposta: str
    tentativas_clarificacao: int
```

**Code smells:**
- `State` e `RetornoNode` têm definições de chaves idênticas — duplicação
- `list` sem parâmetros de tipo — perde type safety para `itens_extraidos`, `carrinho`, `fila_clarificacao`
- Zero comportamento — é só um saco de dados
- **Deveria ser:** Dataclass com métodos `total_carrinho()`, `carrinho_vazio()`, `limpar_carrinho()`, `formatar_resumo()`

### `nodes.py` (368 linhas)

**Responsabilidade:** Node functions do LangGraph — wrappers que recebem State e retornam atualizações parciais.

**Code smells:**
- Número mágico `100` (centavos → reais) repetido em 3 nodes
- Pattern `get_config().get('configurable', {}).get('thread_id', '')` duplicado em 3 nodes
- Acoplamento forte com observabilidade — boilerplate de logging em todo node
- Importa `_classificar_intencao` (função privada) do roteador — viola encapsulamento
- `node_verificar_etapa` retorna `{}` — essencialmente um passthrough

### `builder.py` (154 linhas)

**Responsabilidade:** Constrói e compila o grafo com nodes, edges e lógica de roteamento.

**Code smells:**
- Mapping intent→node e o set de targets do `add_conditional_edges` são duplicados — adicionar uma intent exige atualizar dois lugares
- Sem validação de que todas as intents no mapping correspondem a nodes registrados

### `__init__.py` (41 linhas)

Re-export. Sem problemas.

---

## 4. Módulo `src/graph/handlers/` — Handlers por Intenção

### `utils.py` (55 linhas)

**Responsabilidade:** Utilitários de formatação e cálculo do carrinho.

**Code smells:**
- Número mágico `100` para conversão centavos→reais — aparece aqui E em `nodes.py`
- Sem type safety nas chaves do dict — depende do caller passar dicts corretos
- `formatar_carrinho` acessa `it['item_id']` diretamente — levanta `KeyError` se faltar
- **Deveria ser:** Métodos de uma classe `Carrinho`: `total()`, `formatar()`

### `pedir.py` (161 linhas)

**Responsabilidade:** Processa itens extraídos, calcula preços, adiciona ao carrinho, enfileira clarificações.

**Dict shapes:**
- Fila de clarificação: `{'item': dict, 'item_id': str, 'nome': str, 'campo': 'variante', 'opcoes': list[str]}`

**Code smells:**
- `_calcular_preco_item` acessa `item_data['variantes']` sem `.get()` — `KeyError` se item não tem variantes
- `ResultadoPedir.to_dict()` calcula `'etapa'` dinamicamente — lógica implícita
- **Cálculo de preço duplicado** com `trocar.py`

### `clarificacao.py` (315 linhas)

**Responsabilidade:** Fluxo de clarificação de variantes — valida respostas, retenta com limite, avança na fila.

**Code smells:**
- `_log_clarificacao` mapeia `resultado.tipo` para valores do logger com lógica condicional — protocolo implícito
- Número mágico `2` em `tentativas < 2` — acoplado a `MAX_TENTATIVAS = 3`
- Construção repetida de `ResultadoClarificacao` com muitos defaults repetidos entre branches

### `remover.py` (117 linhas)

**Responsabilidade:** Remove itens do carrinho baseado em extração da mensagem.

**Code smells:** Nenhum significativo — limpo e focado.

### `trocar.py` (388 linhas)

**Responsabilidade:** Troca de variantes de itens no carrinho.

**Code smells:**
- **Importa membro privado** `_nlp` de `spacy_extrator` — viola encapsulamento
- Cálculo de preço duplicado de `pedir.py`
- Validação de variante duplicada — reimplementa o que `get_variantes()` + `in` já faz
- Strings mágicas `'A'`, `'B'`, `'C'`, `'vazio'` compartilhadas com `spacy_extrator`

### `desconhecido.py` (19 linhas)

Fallback para intents não reconhecidas. Mínimo e adequado.

### `__init__.py` (57 linhas)

Define `ResultadoHandler` dataclass genérica — **código morto**, nunca usado em lugar nenhum.

---

## 5. Módulo `src/roteador/` — Classificação de Intenções

### `classificador_intencoes.py` (374 linhas)

**Responsabilidade:** Classificador principal com RAG, fallback LLM e lookup direto.

**Dict shapes:**
- Resultado classificação: `{'intent', 'confidence', 'caminho', 'top1_texto', 'top1_intencao', 'mensagem_norm'}`
- Exemplo similar: `{'texto', 'intencao', 'similaridade'}`

**Code smells:**
- **Side effects no import** (linhas 34-67): `get_intencoes_validas()`, `get_prompt()`, `OllamaLLM()`, `_carregar_cache()` — startup lento, requer Ollama rodando
- **5 blocos de fallback idênticos** — cada um retorna o mesmo dict com `'llm_fixo'`
- `ALTA_PRIORIDADE_INTENTS` duplicado com `rag_utils.py`
- `modelo_llm` é global — não configurável por requisição
- `thread_id` na assinatura mas nunca usado
- `classificar_intencao()` retorna só `str` — o grafo importa `_classificar_intencao()` (privada) para obter o dict completo
- `if __name__ == '__main__'` em código de produção

### `rag_utils.py` (330 linhas)

**Responsabilidade:** Utilitários RAG — embeddings, similaridade cosseno, busca de exemplos, votação.

**Code smells:**
- **4 estratégias de votação sobrepostas:** `calcular_votacao`, `calcular_votacao_max`, `calcular_votacao_hybrid`, `calcular_votacao_com_prioridade`
- `calcular_votacao_max` — **código morto**, nunca chamado
- `calcular_votacao` — wrapper desnecessário, só delega para `hybrid`
- `ALTA_PRIORIDADE` duplicado dentro de `calcular_votacao_com_prioridade`
- Número mágico `0.98` hardcoded dentro da função — diferente do threshold `0.95`
- Lista de intents hardcoded em `montar_prompt_rag` — deveria vir do config
- `cosine_similarity` converte para numpy a cada chamada — ineficiente

### `embedding_cache.json` (~40.000 linhas)

Cache de 102 exemplos com embeddings pré-computados.

### `__init__.py` (18 linhas)

Re-export de 2 símbolos. `rag_utils` fica inacessível via `src.roteador`.

---

## 6. Módulo `src/observabilidade/` — Observabilidade

### `registry.py` (122 linhas)

**Responsabilidade:** Singleton global de loggers.

**Code smells:**
- **5 variáveis globais mutáveis** — anti-pattern singleton clássico
- **5 statements `global`** com `# noqa: PLW0603` — lint warnings suprimidos
- Boilerplate repetido: 5 pares idênticos de getter/setter
- `get_obs_logger` levanta `RuntimeError` enquanto outros retornam `None` — inconsistente
- Sem thread safety nos setters

### `logger.py` (246 linhas) — ObservabilidadeLogger

**Responsabilidade:** Logger CSV de eventos de classificação.

**Code smells:**
- Cria `DictWriter` a cada chamada de `registrar()` — deveria ser cacheado

### `funil_logger.py` (51 linhas), `handler_logger.py` (58 linhas), `extracao_logger.py` (84 linhas), `clarificacao_logger.py` (108 linhas)

**Code smells:**
- **Boilerplate CSV duplicado** em todos os 5 loggers — mesmo pattern `_lock`, `mkdir`, `writer`
- `json.dumps(...)[:200]` — número mágico `200` sem constante
- `'|'.join(...)` para serializar listas — frágil se dados contêm `|`
- `','.join(opcoes)` — frágil se opção contém `,`

### `consultas.py` (182 linhas)

**Responsabilidade:** Queries DuckDB para análise dos logs CSV.

**Code smells:**
- **SQL injection**: f-string de `csv_path`, `thread_id`, `limit` diretamente no SQL
- `conn.execute(query)` chamado 2x em algumas funções — executa mesma query duas vezes
- Cada função cria novo `duckdb.connect()` — sem connection pooling
- Retorna `list[dict]` — sem models tipados

### `debug_cli.py` (138 linhas)

**Responsabilidade:** CLI Typer para debug com tabelas Rich.

**Code smells:**
- **SQL injection** via f-string de `thread_id`
- `LOG_DIR = Path('logs')` — path relativo hardcoded, assume cwd
- `# noqa: S608` — security warning suprimido

### `__init__.py` (86 linhas)

Re-export. Sem problemas.

---

## 7. Inventário Completo de "Poor Man's Objects"

| # | Conceito | Formato Atual | Arquivos Usando | Linhas Afetadas | Model Proposto |
|---|---------|--------------|-----------------|-----------------|----------------|
| 1 | Estado do pedido | `TypedDict` sem métodos | `state.py`, `nodes.py`, `builder.py`, todos handlers | ~200 | `EstadoAtendimento` dataclass |
| 2 | Cardápio | `dict` do YAML | `cardapio.py`, `spacy_extrator.py`, `pedir.py`, `trocar.py`, `clarificacao.py` | ~150 | `Cardapio`, `ItemCardapio`, `VarianteCardapio` |
| 3 | Item extraído (NLP) | `dict` chaves implícitas | `spacy_extrator.py`, `pedir.py`, `nodes.py` | ~80 | `ItemExtraido` dataclass |
| 4 | Carrinho | `list[dict]` | `nodes.py`, `utils.py`, `remover.py`, `trocar.py`, `clarificacao.py`, `pedir.py` | ~200 | `Carrinho` com métodos |
| 5 | Item do carrinho | `dict` | `nodes.py`, `utils.py`, handlers | ~200 | `CarrinhoItem` com `calcular_preco()` |
| 6 | Fila de clarificação | `dict` | `clarificacao.py`, `pedir.py`, `state.py` | ~60 | `ClarificacaoPendente` |
| 7 | Resultado classificação | `dict[str, Any]` | `classificador_intencoes.py`, `nodes.py` | ~100 | `ResultadoClassificacao` |
| 8 | Exemplo similar (RAG) | `dict` | `rag_utils.py`, `classificador_intencoes.py` | ~50 | `ExemploSimilar` |
| 9 | Extração de troca | `dict` | `spacy_extrator.py`, `trocar.py` | ~80 | `ExtracaoTroca`, `ItemOriginal` |
| 10 | Match no carrinho | `dict` | `spacy_extrator.py` | ~40 | `MatchCarrinho` |
| 11 | Item mencionado | `dict` | `spacy_extrator.py` | ~30 | `ItemMencionado` |
| 12 | Tenant info | `dict` | `prompts.py` | ~20 | `TenantInfo` dataclass |

---

## 8. Código Duplicado

| Duplicação | Arquivos | Linhas Duplicadas | Solução |
|---|---|---|---|
| Cálculo de preço | `pedir.py:54-75`, `trocar.py:56-83` | ~40 | `CarrinhoItem.calcular_preco()` |
| Normalização de texto | `spacy_extrator.py`, `fuzzy_extrator.py` | ~20 | Módulo compartilhado ou método |
| Boilerplate CSV logger | 5 arquivos em `observabilidade/` | ~50 | `BaseCsvLogger` |
| `CONFIG_DIR` | `cardapio.py`, `prompts.py` | ~4 | Constante compartilhada |
| `ALTA_PRIORIDADE` | `classificador_intencoes.py`, `rag_utils.py` | ~2 | Constante centralizada |
| Fallback dict | `classificador_intencoes.py` (5x) | ~30 | `_criar_resultado()` helper |
| Getter/setter registry | `registry.py` (5x) | ~40 | Registry dict ou decorador |

---

## 9. Números Mágicos

| Valor | Localização | Significado |
|---|---|---|
| `0.95` | `classificador_intencoes.py:72`, `rag_utils.py:192` | RAG forte threshold |
| `0.5` | `classificador_intencoes.py:76` | RAG fraco threshold |
| `0.55` | `rag_utils.py:31` | Similaridade mínima |
| `0.98` | `rag_utils.py:259` | Match quase idêntico (hardcoded!) |
| `500` | `classificador_intencoes.py:82` | Max chars mensagem |
| `100` | `nodes.py` (3x), `utils.py` | Centavos → reais |
| `75` | `fuzzy_extrator.py` | Fuzzy cutoff |
| `5` | `fuzzy_extrator.py` | Ambiguidade limite |
| `200` | `handler_logger.py` | Truncamento JSON |
| `3` | `clarificacao.py` | Max tentativas |
| `5` | `classificador_intencoes.py:260` | Top-k similares |
| `2` | `clarificacao.py:216` | Acoplado a MAX_TENTATIVAS |

---

## 10. Vulnerabilidades de Segurança

| Tipo | Localização | Descrição |
|---|---|---|
| SQL Injection | `consultas.py` (4 funções) | f-string de paths e `thread_id` no SQL |
| SQL Injection | `debug_cli.py` | f-string de `thread_id` no SQL |
| Suppress de security lint | `debug_cli.py` | `# noqa: S608` |
| Suppress de lint | `registry.py` | `# noqa: PLW0603` (5x) |

---

## 11. Código Morto

| Item | Localização | Por que está morto |
|---|---|---|
| `ResultadoHandler` | `handlers/__init__.py` | Nunca instanciado em lugar nenhum |
| `calcular_votacao_max` | `rag_utils.py:175` | Nunca chamado — `calcular_votacao` usa `hybrid` |
| `calcular_votacao` wrapper | `rag_utils.py:282` | Só delega para `calcular_votacao_hybrid` |

---

## 12. Estimativa de Refatoração

| Fase | Escopo | Arquivos | Linhas Mudadas | Risco |
|---|---|---|---|---|
| 1. Criar `src/modelos/` | ~15 dataclasses | 3 novos + 0 existentes | ~400 novas | Baixo |
| 2. Converter cardápio | Loaders → models | 2 | ~150 | Baixo |
| 3. Converter extratores | Retornar models | 2 | ~300 | Alto |
| 4. Converter handlers | Operar em models | 6 | ~400 | Médio |
| 5. Converter roteador | Retornar models | 2 | ~150 | Médio |
| 6. Observabilidade | Event models + base class | 7 | ~100 | Baixo |
| 7. Converter State | Dataclass ou typed accessors | 2 | ~100 | Médio |
| 8. Testes | Atualizar 27 arquivos | 27 | ~500 | Médio |
| **Total** | | **57 arquivos** | **~1.800-2.200** | |

---

## 13. Dívida Técnica por Prioridade

### 🔴 Crítica (impacta estabilidade)
1. Side effects no import em 3 módulos
2. Estado global mutável sem thread safety
3. SQL injection em 4+ locais
4. API pública insuficiente (`classificar_intencao` vs `_classificar_intencao`)

### 🟡 Alta (impacta manutenibilidade)
5. 12+ dict schemas sem type enforcement
6. Cálculo de preço duplicado
7. 4 estratégias de votação sobrepostas
8. Código morto não removido

### 🟢 Média (impacta legibilidade)
9. Números mágicos sem constantes
10. Nomenclatura inconsistente (PT/EN misturados)
11. `__main__` blocks em código de produção
12. Imports de membros privados entre módulos
