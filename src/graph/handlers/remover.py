"""Handler de remoção de itens do carrinho.

Extrai itens mencionados na mensagem e remove do carrinho.
Suporta remoção por nome do item e por variante específica.

Example:
    ```python
    from src.graph.handlers.remover import processar_remocao

    carrinho = [
        {
            'item_id': 'lanche_001',
            'nome': 'Hambúrguer',
            'quantidade': 1,
            'preco': 1500,
            'variante': 'simples',
        },
    ]
    result = processar_remocao(carrinho, 'tira o hambúrguer')
    result.carrinho
    []
    ```
"""

from dataclasses import dataclass, field

from src.extratores import extrair_item_carrinho
from src.graph.handlers.utils import formatar_carrinho
from src.graph.state import ETAPAS, RetornoNode


@dataclass
class ResultadoRemover:
    """Resultado do processamento de remoção.

    Attributes:
        carrinho: Carrinho atualizado após remoção.
        resposta: Texto formatado para o usuário.
        etapa: Próxima etapa do fluxo.
    """

    carrinho: list[dict] = field(default_factory=list)
    resposta: str = ''
    etapa: ETAPAS = 'inicio'

    def to_dict(self) -> RetornoNode:
        """Converte para dicionário compatível com LangGraph State."""
        return {
            'carrinho': self.carrinho,
            'resposta': self.resposta,
            'etapa': self.etapa,
        }


def processar_remocao(
    carrinho: list[dict],
    mensagem: str,
) -> ResultadoRemover:
    """Processa remoção de itens do carrinho.

    Extrai os itens mencionados na mensagem e remove do carrinho.
    Suporta remoção por nome do item e por variante específica.

    Args:
        carrinho: Carrinho atual do estado.
        mensagem: Mensagem do usuário com o pedido de remoção.

    Returns:
        ResultadoRemover com carrinho, resposta e etapa atualizados.

    Note:
        MVP (Fase 1):
        - Remove TODOS os matches (ignora quantidade)
        - Match parcial por nome
        - "tira tudo" limpa carrinho
        TODO (Fase 2):
        - Suportar quantidade ("tira UMA coca")
        - Clarificação quando ambíguo
    """
    if not carrinho:
        return ResultadoRemover(
            resposta='Seu carrinho está vazio! Não há nada para remover.',
            etapa='inicio',
        )

    itens_para_remover = extrair_item_carrinho(mensagem, carrinho)

    if not itens_para_remover:
        return ResultadoRemover(
            carrinho=carrinho,
            resposta='Não encontrei esse item no seu carrinho.',
            etapa='carrinho',
        )

    indices_para_remover: set[int] = set()
    for item in itens_para_remover:
        indices_para_remover.update(item['indices'])

    carrinho_atualizado = [
        item for i, item in enumerate(carrinho) if i not in indices_para_remover
    ]

    if not carrinho_atualizado:
        return ResultadoRemover(
            carrinho=[],
            resposta='Todos os itens foram removidos do seu pedido.',
            etapa='inicio',
        )

    resposta = 'Itens removidos!\nSeu pedido:\n' + formatar_carrinho(
        carrinho_atualizado
    )
    return ResultadoRemover(
        carrinho=carrinho_atualizado,
        resposta=resposta,
        etapa='carrinho',
    )
