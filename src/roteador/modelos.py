"""Value objects imutaveis para classificacao de intencoes.

Todos os models sao frozen dataclasses — representam valores, nao entidades.

Example:
    ```python
    from src.roteador.modelos import ResultadoClassificacao, ExemploSimilar

    resultado = ResultadoClassificacao(
        intent='pedir',
        confidence=0.95,
        caminho='rag_forte',
        top1_texto='quero um xbacon',
        top1_intencao='pedir',
        mensagem_norm='quero um xbacon',
    )
    resultado.intent
    'pedir'
    ```
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class ResultadoClassificacao:
    """Resultado completo da classificacao de intencao.

    Attributes:
        intent: Nome da intencao classificada.
        confidence: Nivel de confianca (0.0 a 1.0).
        caminho: Estrategia usada ('lookup', 'rag_forte', 'llm_rag', 'llm_fixo').
        top1_texto: Texto do exemplo mais similar.
        top1_intencao: Intencao do exemplo mais similar.
        mensagem_norm: Mensagem original normalizada.
        metadados: Rastro de cada camada para debug (opcional).
    """

    intent: str
    confidence: float
    caminho: Literal['lookup', 'rag_forte', 'llm_rag', 'llm_fixo']
    top1_texto: str
    top1_intencao: str
    mensagem_norm: str
    metadados: dict = field(default_factory=dict)

    def __hash__(self) -> int:
        """Hash baseado em campos hashable (ignora metadados dict)."""
        return hash((
            self.intent,
            self.confidence,
            self.caminho,
            self.top1_texto,
            self.top1_intencao,
            self.mensagem_norm,
            tuple(sorted(self.metadados.items())),
        ))


@dataclass(frozen=True)
class ExemploClassificacao:
    """Exemplo de treinamento para RAG.

    Attributes:
        texto: Texto da mensagem de exemplo.
        intencao: Intencao correta rotulada.
    """

    texto: str
    intencao: str


@dataclass(frozen=True)
class ExemploSimilar:
    """Exemplo similar encontrado via embedding.

    Attributes:
        texto: Texto da mensagem de exemplo.
        intencao: Intencao rotulada do exemplo.
        similaridade: Similaridade cosseno com a query (0.0 a 1.0).
    """

    texto: str
    intencao: str
    similaridade: float
