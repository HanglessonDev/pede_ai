"""Classificadores de intencao — base abstrata.

Define a interface comum para todos os classificadores.

Example:
    ```python
    from abc import ABC, abstractmethod
    from src.roteador.classificadores.base import ClassificadorBase
    ```
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.roteador.modelos import ResultadoClassificacao


class ClassificadorBase(ABC):
    """Base para classificadores de intencao.

    Cada classificador implementa a logica de uma estrategia especifica.
    Retorna ResultadoClassificacao se conseguir classificar,
    None se a mensagem nao se encaixa nesta estrategia.
    """

    @abstractmethod
    def classificar(self, mensagem: str) -> ResultadoClassificacao | None:
        """Classifica a mensagem.

        Args:
            mensagem: Texto normalizado do usuario.

        Returns:
            ResultadoClassificacao se conseguir classificar,
            None se nao for responsabilidade deste classificador.
        """
        ...
