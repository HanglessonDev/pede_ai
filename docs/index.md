# Pede AI

Chatbot de pedidos com IA para lanchonetes. O sistema usa NLP e LLMs para entender
mensagens de clientes, classificar intenções, extrair itens do cardápio e gerenciar
um fluxo conversacional de pedidos.

## Arquitetura

O fluxo de conversação é construído com **LangGraph**:

1. `verificar_etapa` — verifica o estado atual da conversa
2. `router` — classifica a intenção da mensagem (9 intents: saudacao, pedir, remover,
   trocar, carrinho, duvida, confirmar, negar, cancelar)
3. `handlers` — executa a ação correspondente à intenção
4. Resposta ao usuário

A classificação de intenções usa **RAG** (embeddings + similaridade de cosseno) como
padrão, com fallback para prompt fixo via LLM. A extração de entidades (itens,
quantidades, variantes) é feita com **spaCy** EntityRuler.

A persistência do estado usa **SQLite** via LangGraph Checkpointer.

## Stack

- **Python 3.12+** · FastAPI · LangChain · LangGraph
- **Ollama** (LLM local: `qwen3.5:2b`, embeddings: `mini-embed`)
- **spaCy** (`pt_core_news_sm`) para extração de entidades em português
- **Pydantic** para validação de dados
- **uv** como gerenciador de pacotes

## Referência da API

- [Config](api/config.md) — Loaders de configuração (cardápio, prompts)
- [Extratores](api/extratores.md) — Extratores NLP baseados em spaCy
- [Graph](api/graph.md) — Grafo LangGraph (builder, state, nodes)
- [Handlers](api/handlers.md) — Handlers por intenção (pedir, clarificação, desconhecido)
- [Roteador](api/roteador.md) — Classificação de intenções (RAG + LLM)
