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


class BaseCsvLogger(ABC):
    """Classe base abstrata para loggers CSV thread-safe.

    Subclasses devem implementar:
    - ``headers``: propriedade com lista de colunas do CSV.
    - ``_to_row(**kwargs)``: metodo que converte kwargs em lista de valores.
    """

    def __init__(self, csv_path: Path | str) -> None:
        """Inicializa o logger criando o arquivo CSV se necessario.

        Args:
            csv_path: Caminho para o arquivo CSV.
        """
        self._csv_path = Path(csv_path).resolve()
        self._csv_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._inicializar_csv()

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

    def registrar(self, **kwargs: str | float | int | None) -> None:
        """Registra uma linha no CSV de forma thread-safe.

        Args:
            **kwargs: Dados a registrar (str, float, int ou None).
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
