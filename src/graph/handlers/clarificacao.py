"""Handler de clarificação de variantes.

Processa respostas do usuário durante a clarificação de itens
pendentes no pedido. Suporta validação via extrator spaCy,
re-prompt com limite de tentativas e avanço automático na fila.

Example:
    ```python
    from src.graph.handlers.clarificacao import clarificar

    fila = [
        {
            'item': {
                'item_id': 'lanche_001',
                'quantidade': 1,
                'variante': None,
                'remocoes': [],
            },
            'item_id': 'lanche_001',
            'nome': 'Hambúrguer',
            'campo': 'variante',
            'opcoes': ['simples', 'duplo'],
        }
    ]
    result = clarificar(fila, 'duplo', 0)
    result.tipo
    'sucesso'
    ```
"""

from dataclasses import dataclass, field

from src.config import get_item_por_id, get_nome_item
from src.extratores import extrair_variante
from src.graph.state import ETAPAS, RetornoNode


MAX_TENTATIVAS = 3
"""Número máximo de tentativas antes de desistir do item."""


@dataclass
class ResultadoClarificacao:
    """Resultado do processamento de clarificação.

    Attributes:
        tipo: Tipo do resultado ('sucesso', 'invalida', 'erro').
        resposta: Texto da resposta para o usuário.
        etapa: Próxima etapa do fluxo.
        carrinho: Carrinho atualizado.
        fila: Fila de clarificação atualizada.
        tentativas: Contador de tentativas atual.
    """

    tipo: str
    resposta: str
    etapa: ETAPAS
    carrinho: list = field(default_factory=list)
    fila: list = field(default_factory=list)
    tentativas: int = 0

    def to_dict(self) -> RetornoNode:
        """Converte para dicionário compatível com LangGraph State."""
        return {
            'resposta': self.resposta,
            'etapa': self.etapa,
            'carrinho': self.carrinho,
            'fila_clarificacao': self.fila,
            'tentativas_clarificacao': self.tentativas,
        }


def _proxima_clarificacao(fila: list[dict]) -> str:
    """Gera prompt para o próximo item na fila de clarificação.

    Args:
        fila: Fila de itens pendentes de clarificação.

    Returns:
        String formatada com nome do item e opções disponíveis.
    """
    proxima = fila[0]
    opcoes_str = ', '.join(proxima['opcoes'])
    return f'{proxima["nome"]}: qual opção? {opcoes_str}'


def _formatar_carrinho(carrinho: list[dict]) -> str:
    """Formata o carrinho como string legível.

    Args:
        carrinho: Lista de itens no carrinho.

    Returns:
        String formatada com quantidade, nome e preço de cada item.
    """
    linhas = [
        f'{it["quantidade"]}x {get_nome_item(it["item_id"]) or it["item_id"]} — R$ {it["preco"] / 100:.2f}'
        for it in carrinho
    ]
    return '\n'.join(linhas)


def clarificar(
    fila: list[dict],
    mensagem: str,
    tentativas: int,
) -> ResultadoClarificacao:
    """Processa a resposta do usuário durante clarificação de variante.

    Tenta extrair uma variante válida da mensagem usando o extrator
    spaCy. Se válida, calcula o preço e adiciona ao carrinho. Se
    inválida, incrementa o contador de tentativas e faz re-prompt
    (até MAX_TENTATIVAS tentativas).

    Args:
        fila: Fila de itens pendentes de clarificação.
        mensagem: Mensagem do usuário com a resposta.
        tentativas: Contador atual de tentativas falhas.

    Returns:
        ResultadoClarificacao com estado atualizado.
    """
    if not fila:
        return ResultadoClarificacao(
            tipo='sucesso',
            resposta='',
            etapa='inicio',
            fila=[],
            carrinho=[],
            tentativas=0,
        )

    item_fila = fila[0]
    item_id = item_fila['item_id']
    nome = item_fila['nome']
    opcoes = item_fila['opcoes']
    item_dados = item_fila['item']

    variante = extrair_variante(mensagem, item_id)

    if variante is not None:
        return _processar_variante_valida(fila, item_id, item_dados, variante)

    return _processar_variante_invalida(fila, nome, opcoes, tentativas)


def _processar_variante_valida(
    fila: list[dict],
    item_id: str,
    item_dados: dict,
    variante: str,
) -> ResultadoClarificacao:
    """Processa uma variante válida e adiciona ao carrinho.

    Args:
        fila: Fila de itens pendentes.
        item_id: ID do item no cardápio.
        item_dados: Dados do item extraído (com quantidade).
        variante: Variante escolhida pelo usuário.

    Returns:
        ResultadoClarificacao com carrinho atualizado.
    """
    item_data = get_item_por_id(item_id)
    if item_data is None:
        fila.pop(0)
        return ResultadoClarificacao(
            tipo='erro',
            resposta='Erro ao processar item.',
            etapa='inicio' if not fila else 'clarificando_variante',
            fila=list(fila),
            carrinho=[],
            tentativas=0,
        )

    variante_obj = next(
        (v for v in item_data.get('variantes', []) if v['opcao'] == variante),
        None,
    )
    if variante_obj is None:
        fila.pop(0)
        return ResultadoClarificacao(
            tipo='erro',
            resposta='Erro ao processar variante.',
            etapa='inicio' if not fila else 'clarificando_variante',
            fila=list(fila),
            carrinho=[],
            tentativas=0,
        )

    preco_total = variante_obj['preco'] * item_dados['quantidade']
    item_dados = dict(item_dados)
    item_dados['variante'] = variante
    item_dados['preco'] = preco_total

    carrinho = [item_dados]
    fila = list(fila[1:])

    if fila:
        resposta = _proxima_clarificacao(fila)
        etapa = 'clarificando_variante'
    else:
        resposta = _formatar_carrinho(carrinho)
        etapa = 'inicio'

    return ResultadoClarificacao(
        tipo='sucesso',
        resposta=resposta,
        etapa=etapa,
        carrinho=carrinho,
        fila=fila,
        tentativas=0,
    )


def _processar_variante_invalida(
    fila: list[dict],
    nome: str,
    opcoes: list[str],
    tentativas: int,
) -> ResultadoClarificacao:
    """Processa uma variante inválida e decide re-prompt ou desistência.

    Args:
        fila: Fila de itens pendentes.
        nome: Nome do item para mensagens.
        opcoes: Lista de opções válidas.
        tentativas: Contador atual de tentativas falhas.

    Returns:
        ResultadoClarificacao com decisão de re-prompt ou desistência.
    """
    tentativas += 1

    if tentativas >= MAX_TENTATIVAS:
        fila = list(fila[1:])
        if fila:
            resposta = f'Não consegui entender. {_proxima_clarificacao(fila)}'
            return ResultadoClarificacao(
                tipo='invalida',
                resposta=resposta,
                etapa='clarificando_variante',
                fila=fila,
                carrinho=[],
                tentativas=0,
            )
        return ResultadoClarificacao(
            tipo='invalida',
            resposta='Não consegui entender a opção. Vamos continuar com o pedido.',
            etapa='inicio',
            fila=[],
            carrinho=[],
            tentativas=0,
        )

    opcoes_str = ', '.join(opcoes)
    return ResultadoClarificacao(
        tipo='invalida',
        resposta=f'Essa opção não está disponível. {nome}: {opcoes_str}?',
        etapa='clarificando_variante',
        fila=list(fila),
        carrinho=[],
        tentativas=tentativas,
    )
