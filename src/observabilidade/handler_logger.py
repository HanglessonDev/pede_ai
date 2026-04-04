"""Logger generico para execucao de handlers."""

import csv
import json
import threading
from datetime import UTC, datetime
from pathlib import Path

HEADERS = [
    'timestamp',
    'thread_id',
    'handler',
    'intent',
    'input_resumo',
    'output_resumo',
    'tempo_ms',
    'erro',
]


class HandlerLogger:
    """Logger thread-safe para registrar execucoes de handlers."""

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
        handler: str,
        intent: str,
        input_dados: dict,
        output_dados: dict,
        tempo_ms: float,
        erro: str | None = None,
    ) -> None:
        with self._lock, open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now(UTC).isoformat(),
                thread_id,
                handler,
                intent,
                json.dumps(input_dados, ensure_ascii=False)[:200],
                json.dumps(output_dados, ensure_ascii=False)[:200],
                f'{tempo_ms:.2f}',
                erro or '',
            ])
