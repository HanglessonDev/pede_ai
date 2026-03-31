from src.config import get_item_por_id, get_tenant_nome
from src.extratores import extrair
from src.graph.state import State
from src.roteador import classificar_intencao


def node_router(state: State) -> dict:
    intent = classificar_intencao(state.get('mensagem_atual', ''))
    return {'intent': intent}


def node_extrator(state: State) -> dict:
    if state.get('intent') == 'pedir':
        return {'itens_extraidos': extrair(state.get('mensagem_atual', ''))}
    return {'itens_extraidos': []}


def node_handler_pedir(state: State) -> dict:
    itens_extraidos = state.get('itens_extraidos') or []
    carrinho = state.get('carrinho', [])
    fila = state.get('fila_clarificacao', [])
    itens_adicionados = []

    for item in itens_extraidos:
        item_data = get_item_por_id(item['item_id'])
        if item_data is None:
            continue

        preco = item_data.get('preco')
        variante_extraida = item.get('variante')
        variantes_validas = [v['opcao'] for v in item_data.get('variantes', [])]

        if preco is not None:
            item['preco'] = preco * item['quantidade']
            carrinho.append(item)
            itens_adicionados.append(
                (item_data['nome'], item['quantidade'], item['preco'])
            )

        elif variante_extraida and variante_extraida in variantes_validas:
            variante_obj = next(
                v for v in item_data['variantes'] if v['opcao'] == variante_extraida
            )
            item['preco'] = variante_obj['preco'] * item['quantidade']
            carrinho.append(item)
            itens_adicionados.append(
                (item_data['nome'], item['quantidade'], item['preco'])
            )

        else:
            fila.append(
                {
                    'item': item,
                    'item_id': item['item_id'],
                    'nome': item_data['nome'],  # ← guarda o nome aqui
                    'campo': 'variante',
                    'opcoes': variantes_validas,
                }
            )

    # monta resposta
    if fila:
        proxima = fila[0]
        opcoes = ', '.join(proxima['opcoes'])
        resposta = f'{proxima["nome"]}: qual opção? {opcoes}'
    else:
        linhas = [
            f'{qtd}x {nome} — R$ {preco / 100:.2f}'
            for nome, qtd, preco in itens_adicionados
        ]
        resposta = '\n'.join(linhas)

    return {
        'carrinho': carrinho,
        'fila_clarificacao': fila,
        'resposta': resposta,
    }


def node_handler_saudacao(state: State) -> dict:
    nome_restaurante = get_tenant_nome()
    resposta = f'Ola! Seja bem-vindo(a) a {nome_restaurante}!\nComo posso ajudar?'
    return {'resposta': resposta, 'etapa': 'saudacao'}


def node_handler_carrinho(state: State) -> dict:
    carrinho = state.get('carrinho', [])
    if not carrinho:
        return {'resposta': 'Seu carrinho está vazio!', 'etapa': 'carrinho'}
    linhas = []
    total = 0
    for item in carrinho:
        item_data = get_item_por_id(item['item_id'])
        if item_data is None:
            continue
        nome = item_data['nome']
        preco = item['preco']
        linhas.append(f'{item["quantidade"]}x {nome} - R$ {preco / 100:.2f}')
        total += preco
    resposta = 'Seu pedido:\n' + '\n'.join(linhas) + f'\nTotal: R$ {total / 100:.2f}'
    return {'resposta': resposta, 'etapa': 'carrinho'}


def node_handler_confirmar(state: State) -> dict:
    etapa = state.get('etapa', '')
    carrinho = state.get('carrinho', [])
    
    match etapa:
        case 'clarificando_variante':
            return {'resposta': 'Variante confirmada.', 'etapa': etapa}
        case _:
            # Confirmação genérica (ex: "sim" no final do pedido)
            if carrinho:
                total = sum(item.get('preco', 0) for item in carrinho)
                resposta = f"Pedido confirmado! Total: R$ {total/100:.2f}"
                return {'resposta': resposta, 'etapa': 'finalizado'}

            return {'resposta': 'Não tenho nada no carrinho para confirmar.'}

def node_handler_cancelar(state: State) -> dict: ...
