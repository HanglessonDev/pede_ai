"""Chat CLI do Pede AI."""

import os
import sqlite3
import uuid
from pathlib import Path

from dotenv import load_dotenv
from langgraph.checkpoint.sqlite import SqliteSaver

from src.config import get_intencoes_validas, get_prompt, get_roteador_config
from src.graph.builder import criar_graph
from src.infra import GroqProvider, SentenceTransformerEmbeddings
from src.observabilidade.loggers import (
    ObservabilidadeLoggers,
    set_global_loggers,
)
from src.roteador.embedding_service import EmbeddingService
from src.roteador.service import ClassificadorIntencoes


# Carrega variaveis do .env
load_dotenv()

# Configura loggers de observabilidade (sistema unificado)
LOG_DIR = Path('logs')
LOG_DIR.mkdir(parents=True, exist_ok=True)
loggers = ObservabilidadeLoggers.criar_padrao(LOG_DIR)
set_global_loggers(loggers)


def criar_classificador() -> ClassificadorIntencoes:
    """Factory para o classificador de intencoes."""
    config = get_roteador_config()
    llm = GroqProvider(api_key=os.getenv('GROQ_API_KEY', ''))
    embeddings = SentenceTransformerEmbeddings(diretorio_modelos='modelos')
    embedding_service = EmbeddingService(
        provider=embeddings,
        exemplos_path=config.exemplos_path,
        cache_path=config.embedding_cache_path,
    )
    prompt = get_prompt('classificador_intencoes')
    intencoes = get_intencoes_validas()

    return ClassificadorIntencoes(
        llm=llm,
        embedding_service=embedding_service,
        config=config,
        prompt_template=prompt,
        intencoes_validas=intencoes,
        loggers=loggers,
    )


classificador = criar_classificador()
conn = sqlite3.connect('./pede_ai.db', check_same_thread=False)
checkpointer = SqliteSaver(conn)
graph = criar_graph(checkpointer, classificador=classificador)
user_id = 'teste_001'
config = {'configurable': {'thread_id': user_id}}

print('=== Pede AI - Modo Teste ===')
print("Digite 'sair' para encerrar\n")

while True:
    mensagem = input('Você: ').strip()
    if mensagem.lower() == 'sair':
        break
    if not mensagem:
        continue

    resultado = graph.invoke(
        {'mensagem_atual': mensagem, 'turn_id': uuid.uuid4().hex[:8]},
        config,
    )  # type: ignore

    print(f'Bot: {resultado.get("resposta", "???")}')
    print(
        f'[etapa={resultado.get("etapa")} | intent={resultado.get("intent")} | '
        f'confidence={resultado.get("confidence", 0):.2f} | '
        f'carrinho={len(resultado.get("carrinho", []))} itens]\n'
    )
