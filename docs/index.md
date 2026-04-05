# Pede AI

Chatbot de pedidos com IA para lanchonetes. O sistema usa NLP e LLMs para entender
mensagens de clientes, classificar intenções, extrair itens do cardápio e gerenciar
um fluxo conversacional de pedidos.

## Arquitetura

O fluxo de conversação é construído com **LangGraph**:

1. `verificar_etapa` — verifica o estado atual da conversa
2. `router` — classifica a intenção via cadeia: **Lookup** (tokens exatos) → **RAG** (embeddings + votação) → **LLM** (fallback)
3. `extrator` — extrai itens do cardápio via spaCy + fuzzy matching (apenas para intent='pedir')
4. `handlers` — executa a ação correspondente à intenção
5. `clarificacao` — se item tem variantes pendentes, pergunta qual o usuário quer

A extração de entidades usa **spaCy EntityRuler** com patterns gerados do cardápio YAML,
com fallback de **fuzzy matching** (rapidfuzz).

A persistência do estado usa **SQLite** via LangGraph Checkpointer.

A observabilidade é feita via **CSV loggers** com consultas **DuckDB**.

## Stack

- **Python 3.12+** · FastAPI · LangChain · LangGraph
- **Ollama** (`qwen3.5:2b`) · **Groq** (`llama-3.1-8b-instant`)
- **spaCy** (`pt_core_news_sm`) · **rapidfuzz** · **sentence-transformers**
- **Pydantic** · **DuckDB** · **Uvicorn** · **Typer** · **uv**

## Referência da API

- [Config](api/config.md) — Loaders de configuração com cache
- [Extratores](api/extratores.md) — Extração NLP modular (spaCy + fuzzy)
- [Graph](api/graph.md) — Grafo LangGraph (builder, state, nodes)
- [Handlers](api/handlers.md) — Handlers por intenção (SRP)
- [Observabilidade](api/observabilidade.md) — Logger CSV + consultas DuckDB
- [Roteador](api/roteador.md) — Classificação de intenções (Lookup → RAG → LLM)
- [Infra](api/infra.md) — Providers de LLM e Embedding
- [Scripts](api/scripts.md) — Scripts utilitários
