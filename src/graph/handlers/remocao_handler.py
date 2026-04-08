"""Handler de remocao de itens do carrinho.

Extrai itens mencionados na mensagem e remove do carrinho.
Suporta remocao por nome do item e por variante especifica.

Example:
    ```python
    from src.graph.handlers.remocao_handler import processar_remocao

    carrinho_dicts = [
        {
            'item_id': 'lanche_001',
            'quantidade': 1,
            'preco': 1500,
            'variante': 'simples',
        },
    ]
    result = processar_remocao(carrinho_dicts, 'tira o hamburguer')
    result.carrinho
    []
    ```
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from src.extratores import extrair_item_carrinho
from src.graph.handlers.carrinho import Carrinho
from src.graph.state import MODOS, RetornoNode

if TYPE_CHECKING:
    from src.observabilidade.loggers import ObservabilidadeLoggers


@dataclass
class ResultadoRemover:
    """Resultado do processamento de remocao.

    Attributes:
        carrinho: Carrinho atualizado apos remocao.
        resposta: Texto formatado para o usuario.
        etapa: Proxima etapa do fluxo.
    """

    carrinho: list[dict] = field(default_factory=list)
    resposta: str = ''
    modo: MODOS = 'ocioso'

    def to_dict(self) -> RetornoNode:
        """Converte para dicionario compativel com LangGraph State."""
        return {
            'carrinho': self.carrinho,
            'resposta': self.resposta,
            'modo': self.modo,
        }


def processar_remocao(
    carrinho_dicts: list[dict],
    mensagem: str,
    loggers: ObservabilidadeLoggers | None = None,
    thread_id: str = '',
    turn_id: str = '',
) -> ResultadoRemover:
    """Processa remocao de itens do carrinho."""
    if not carrinho_dicts:
        resultado = ResultadoRemover(
            resposta='Seu carrinho esta vazio! Nao ha nada para remover.',
            modo='ocioso',
        )
        return _log_remocao(
            resultado, carrinho_dicts, loggers, thread_id, turn_id, 'remover'
        )

    itens_para_remover = extrair_item_carrinho(mensagem, carrinho_dicts)

    if not itens_para_remover:
        resultado = ResultadoRemover(
            carrinho=carrinho_dicts,
            resposta='Não encontrei esse item no seu carrinho.',
            modo='coletando',
        )
        return _log_remocao(
            resultado, carrinho_dicts, loggers, thread_id, turn_id, 'remover'
        )

    indices_para_remover: set[int] = set()
    for item in itens_para_remover:
        indices_para_remover.update(item['indices'])

    carrinho = Carrinho.from_state_dicts(carrinho_dicts)
    carrinho.remover_indices(indices_para_remover)

    if carrinho.vazio():
        resultado = ResultadoRemover(
            carrinho=[],
            resposta='Todos os itens foram removidos do seu pedido.',
            modo='ocioso',
        )
        return _log_remocao(
            resultado, carrinho_dicts, loggers, thread_id, turn_id, 'remover'
        )

    resposta = 'Itens removidos!\nSeu pedido:\n' + carrinho.formatar()
    resultado = ResultadoRemover(
        carrinho=carrinho.to_state_dicts(),
        resposta=resposta,
        modo='coletando',
    )
    return _log_remocao(
        resultado, carrinho_dicts, loggers, thread_id, turn_id, 'remover'
    )


def _log_remocao(
    resultado: ResultadoRemover,
    carrinho_original: list[dict],
    loggers: ObservabilidadeLoggers | None,
    thread_id: str,
    turn_id: str,
    evento: str,
) -> ResultadoRemover:
    """Registra evento de negocio se loggers disponiveis."""
    if loggers and loggers.negocio is not None:
        carrinho_resultado = resultado.carrinho
        preco_total = sum(
            i.get('preco_centavos', i.get('preco', 0)) for i in carrinho_resultado
        )
        loggers.negocio.registrar(
            thread_id=thread_id,
            turn_id=turn_id,
            evento=evento,
            carrinho_size=len(carrinho_resultado),
            preco_total_centavos=preco_total,
            intent='remover',
            resposta=resultado.resposta,
            tentativas_clarificacao=0,
        )
    return resultado
