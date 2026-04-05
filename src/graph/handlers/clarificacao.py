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

from src.config import get_item_por_id
from src.extratores import extrair_variante
from src.extratores.fuzzy_extrator import fuzzy_match_variante
from src.graph.handlers.carrinho import Carrinho
from src.graph.state import ETAPAS, RetornoNode
from src.observabilidade.registry import get_clarificacao_logger


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
    carrinho: list[dict] = field(default_factory=list)
    fila: list[dict] = field(default_factory=list)
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


def clarificar(
    fila: list[dict],
    mensagem: str,
    tentativas: int,
    thread_id: str = '',
) -> ResultadoClarificacao:
    """Processa a resposta do usuário durante clarificação de variante.

    Tenta extrair uma variante válida da mensagem usando o extrator
    spaCy. Se não encontrar, usa fuzzy matching como fallback. Se
    válida, calcula o preço e adiciona ao carrinho. Se inválida,
    incrementa o contador de tentativas e faz re-prompt.

    Args:
        fila: Fila de itens pendentes de clarificação.
        mensagem: Mensagem do usuário com a resposta.
        tentativas: Contador atual de tentativas falhas.
        thread_id: Identificador da sessão para observabilidade.

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

    # Tenta extrair via EntityRuler
    variante = extrair_variante(mensagem, item_id)

    # Valida: se EntityRuler retornou parcial (ex: "limão" em vez de "limão 300ml"),
    # usa fuzzy matching para encontrar a variante exata
    if variante is not None and variante not in opcoes:
        variante_fuzzy, _score = fuzzy_match_variante(mensagem, opcoes)
        if variante_fuzzy:
            variante = variante_fuzzy
        else:
            variante = None

    # Fallback: fuzzy matching se EntityRuler não encontrou
    if variante is None:
        variante_fuzzy, _score = fuzzy_match_variante(mensagem, opcoes)
        if variante_fuzzy:
            variante = variante_fuzzy

    if variante is not None:
        resultado = _processar_variante_valida(fila, item_id, item_dados, variante)
    else:
        resultado = _processar_variante_invalida(fila, nome, opcoes, tentativas)

    _log_clarificacao(
        thread_id=thread_id,
        item_id=item_id,
        nome_item=nome,
        opcoes=opcoes,
        mensagem=mensagem,
        tentativas=tentativas,
        resultado=resultado,
        variante=variante,
    )

    return resultado


def _log_clarificacao(
    thread_id: str,
    item_id: str,
    nome_item: str,
    opcoes: list[str],
    mensagem: str,
    tentativas: int,
    resultado: ResultadoClarificacao,
    variante: str | None,
) -> None:
    """Registra evento de clarificação no logger se configurado."""
    logger = get_clarificacao_logger()
    if logger is None:
        return

    # Mapeia tipo interno para valores válidos do logger
    tipo_logger = resultado.tipo
    if tipo_logger == 'invalida':
        tipo_logger = 'invalida_reprompt' if tentativas < 2 else 'invalida_desistiu'

    logger.registrar(
        thread_id=thread_id,
        item_id=item_id,
        nome_item=nome_item,
        campo='variante',
        opcoes=opcoes,
        mensagem=mensagem,
        tentativas=tentativas,
        resultado=tipo_logger,
        variante_escolhida=variante or '',
    )


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
        resposta = Carrinho.from_state_dicts(carrinho).formatar()
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
