"""Classe base para loggers CSV thread-safe.

Elimina boilerplate duplicado em todos os loggers de observabilidade.
Cada logger concreto precisa implementar apenas ``headers`` e ``_to_row``.

Example:
    ```python
    from src.observabilidade.base_logger import BaseCsvLogger


    class MeuLogger(BaseCsvLogger):
        @property
        def headers(self) -> list[str]:
            return ['timestamp', 'mensagem']

        def _to_row(self, **kwargs) -> list:
            return [kwargs.get('timestamp', ''), kwargs.get('mensagem', '')]
    ```
"""

from __future__ import annotations

import csv
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class BaseCsvLogger(ABC):
    """Classe base abstrata para loggers CSV thread-safe.

    Subclasses devem implementar:
    - ``headers``: propriedade com lista de colunas do CSV.
    - ``_to_row(**kwargs)``: metodo que converte kwargs em lista de valores.
    """

    NIVEIS = ('INFO', 'DEBUG', 'TRACE')
    """Hierarquia de niveis: INFO < DEBUG < TRACE."""

    def __init__(self, csv_path: Path | str, nivel: str = 'INFO') -> None:
        """Inicializa o logger criando o arquivo CSV se necessario.

        Args:
            csv_path: Caminho para o arquivo CSV.
            nivel: Nivel de detalhe — INFO, DEBUG ou TRACE.
        """
        self._csv_path = Path(csv_path).resolve()
        self._csv_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._nivel = nivel
        self._inicializar_csv()

    @property
    def nivel(self) -> str:
        """Retorna o nivel de log atual."""
        return self._nivel

    def deve_logar(self, nivel_requerido: str) -> bool:
        """Verifica se deve logar baseado no nivel.

        Hierarquia: INFO (menos detalhe) < DEBUG < TRACE (mais detalhe).
        Logger em TRACE logga INFO+DEBUG+TRACE.
        Logger em INFO logga apenas INFO.

        Args:
            nivel_requerido: Nivel minimo necessario para logar.

        Returns:
            True se o nivel atual >= nivel requerido em detalhe.
        """
        try:
            return self.NIVEIS.index(self._nivel) >= self.NIVEIS.index(nivel_requerido)
        except ValueError:
            return True

    @property
    @abstractmethod
    def headers(self) -> list[str]:
        """Retorna lista de colunas do CSV."""
        ...

    @abstractmethod
    def _to_row(self, **kwargs) -> list:
        """Converte kwargs em lista de valores para uma linha do CSV.

        Args:
            **kwargs: Dados a serializar.

        Returns:
            Lista de valores na ordem dos headers.
        """
        ...

    def _inicializar_csv(self) -> None:
        """Cria arquivo CSV com headers se nao existir."""
        with self._lock:
            if not self._csv_path.exists():
                with open(self._csv_path, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(self.headers)

    def registrar(self, **kwargs: Any) -> None:
        """Registra uma linha no CSV de forma thread-safe.

        Args:
            **kwargs: Dados a registrar.
                Serão convertidos via _to_row().
        """
        row = self._to_row(**kwargs)
        with self._lock, open(self._csv_path, 'a', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(row)

    @property
    def csv_path(self) -> Path:
        """Retorna caminho absoluto do arquivo CSV."""
        return self._csv_path
