"""Logger para progressao no funil de pedidos."""

import csv
import threading
from datetime import UTC, datetime
from pathlib import Path

HEADERS = [
    'timestamp',
    'thread_id',
    'etapa_anterior',
    'etapa_atual',
    'intent',
    'carrinho_size',
]


class FunilLogger:
    """Logger thread-safe para registrar transicoes no funil."""

    def __init__(self, csv_path: Path | str) -> None:
        self.csv_path = Path(csv_path)
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._inicializar_csv()

    def _inicializar_csv(self) -> None:
        with self._lock:
            if not self.csv_path.exists():
                with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(HEADERS)

    def registrar(
        self,
        thread_id: str,
        etapa_anterior: str,
        etapa_atual: str,
        intent: str,
        carrinho_size: int = 0,
    ) -> None:
        with self._lock, open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    datetime.now(UTC).isoformat(),
                    thread_id,
                    etapa_anterior,
                    etapa_atual,
                    intent,
                    carrinho_size,
                ]
            )
