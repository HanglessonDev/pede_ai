"""Handlers de processamento do grafo de atendimento.

Cada handler encapsula a lógica de um tipo específico de
processamento no fluxo de atendimento.

Submódulos:
    clarificacao: Lógica de clarificação de variantes e campos pendentes.
    pedir: Processamento de pedidos e cálculo de preços.

Example:
    ```python
    from src.graph.handlers import ResultadoPedir, ResultadoClarificacao
    ```
"""

from dataclasses import dataclass

from .clarificacao import ResultadoClarificacao
from .pedir import ResultadoPedir


@dataclass
class ResultadoHandler:
    """Resultado padronizado de um handler.

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
    etapa: str
    carrinho: list
    fila: list
    tentativas: int

    def to_dict(self) -> dict:
        """Converte para dicionário compatível com LangGraph State."""
        return {
            'resposta': self.resposta,
            'etapa': self.etapa,
            'carrinho': self.carrinho,
            'fila_clarificacao': self.fila,
            'tentativas_clarificacao': self.tentativas,
        }


__all__ = [
    'ResultadoClarificacao',
    'ResultadoHandler',
    'ResultadoPedir',
]
