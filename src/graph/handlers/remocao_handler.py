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

from src.extratores import extrair_item_carrinho
from src.graph.handlers.carrinho import Carrinho
from src.graph.state import MODOS, RetornoNode


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
) -> ResultadoRemover:
    """Processa remocao de itens do carrinho."""
    if not carrinho_dicts:
        return ResultadoRemover(
            resposta='Seu carrinho esta vazio! Nao ha nada para remover.',
            modo='ocioso',
        )

    itens_para_remover = extrair_item_carrinho(mensagem, carrinho_dicts)

    if not itens_para_remover:
        return ResultadoRemover(
            carrinho=carrinho_dicts,
            resposta='Não encontrei esse item no seu carrinho.',
            modo='coletando',
        )

    indices_para_remover: set[int] = set()
    for item in itens_para_remover:
        indices_para_remover.update(item['indices'])

    carrinho = Carrinho.from_state_dicts(carrinho_dicts)
    carrinho.remover_indices(indices_para_remover)

    if carrinho.vazio():
        return ResultadoRemover(
            carrinho=[],
            resposta='Todos os itens foram removidos do seu pedido.',
            modo='ocioso',
        )

    resposta = 'Itens removidos!\nSeu pedido:\n' + carrinho.formatar()
    return ResultadoRemover(
        carrinho=carrinho.to_state_dicts(),
        resposta=resposta,
        modo='coletando',
    )
