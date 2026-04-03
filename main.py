# chat.py
import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver

from src.graph.builder import criar_graph


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

    resultado = graph.invoke({'mensagem_atual': mensagem}, config) # type: ignore

    print(f'Bot: {resultado.get("resposta", "???")}')
    print(
        f'[etapa={resultado.get("etapa")} | intent={resultado.get("intent")} | carrinho={len(resultado.get("carrinho", []))} itens]\n'
    )


# testa esse fluxo:
# ```
# 1. "oi"
# 2. "quero hamburguer"
# 3. "duplo"
# 4. "me mostra meu pedido"
# 5. "confirma"
