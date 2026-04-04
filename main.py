# chat.py
import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from src.graph.builder import criar_graph
from src.observabilidade.clarificacao_logger import ClarificacaoLogger
from src.observabilidade.extracao_logger import ExtracaoLogger
from src.observabilidade.funil_logger import FunilLogger
from src.observabilidade.handler_logger import HandlerLogger
from src.observabilidade.logger import ObservabilidadeLogger
from src.observabilidade.registry import (
    set_clarificacao_logger,
    set_extracao_logger,
    set_funil_logger,
    set_handler_logger,
    set_obs_logger,
)

# Configura loggers de observabilidade
LOG_DIR = Path('logs')
set_obs_logger(ObservabilidadeLogger(LOG_DIR / 'classificacoes.csv'))
set_clarificacao_logger(ClarificacaoLogger(LOG_DIR / 'clarificacoes.csv'))
set_extracao_logger(ExtracaoLogger(LOG_DIR / 'extracoes.csv'))
set_handler_logger(HandlerLogger(LOG_DIR / 'handlers.csv'))
set_funil_logger(FunilLogger(LOG_DIR / 'funil.csv'))

conn = sqlite3.connect('./pede_ai.db', check_same_thread=False)
checkpointer = SqliteSaver(conn)
graph = criar_graph(checkpointer)
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

    resultado = graph.invoke({'mensagem_atual': mensagem}, config)  # type: ignore

    print(f'Bot: {resultado.get("resposta", "???")}')
    print(
        f'[etapa={resultado.get("etapa")} | intent={resultado.get("intent")} | '
        f'confidence={resultado.get("confidence", 0):.2f} | '
        f'carrinho={len(resultado.get("carrinho", []))} itens]\n'
    )


# testa esse fluxo:
# ```
# 1. "oi"
# 2. "quero hamburguer"
# 3. "duplo"
# 4. "me mostra meu pedido"
# 5. "confirma"
