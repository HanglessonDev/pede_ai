"""Logger para eventos de extração de itens do cardápio.

Registra extrações de itens em um CSV append-only para análise posterior.
Thread-safe para uso com FastAPI.
"""

import csv
import threading
from datetime import UTC, datetime
from pathlib import Path

HEADERS = [
    'timestamp',
    'thread_id',
    'mensagem',
    'itens_encontrados',
    'itens_ids',
    'variantes_encontradas',
    'tempo_ms',
]


class ExtracaoLogger:
    """Logger thread-safe para registrar eventos de extração de itens.

    Cada linha do CSV representa uma extração de itens do cardápio
    a partir da mensagem do usuário.

    Attributes:
        csv_path: Caminho absoluto do arquivo CSV onde os eventos são registrados.
    """

    def __init__(self, csv_path: Path | str) -> None:
        """Inicializa o logger criando o arquivo CSV se necessário.

        O diretório pai é criado automaticamente se não existir. Se o
        arquivo CSV já existir, os eventos serão adicionados ao final (append).

        Args:
            csv_path: Caminho para o arquivo CSV de eventos.
        """
        self.csv_path = Path(csv_path)
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._inicializar_csv()

    def _inicializar_csv(self) -> None:
        """Cria o arquivo CSV com headers se não existir."""
        with self._lock:
            if not self.csv_path.exists():
                with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(HEADERS)

    def registrar(
        self,
        thread_id: str,
        mensagem: str,
        itens_extraidos: list[dict],
        tempo_ms: float,
    ) -> None:
        """Registra um evento de extração no CSV.

        Args:
            thread_id: Identificador único da sessão/conversa.
            mensagem: Texto original do usuário.
            itens_extraidos: Lista de dicts com informações dos itens extraídos.
                Cada dict deve conter 'item_id', 'quantidade', 'variante' e
                'remocoes'.
            tempo_ms: Tempo de processamento da extração em milissegundos.
        """
        with self._lock, open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    datetime.now(UTC).isoformat(),
                    thread_id,
                    mensagem,
                    len(itens_extraidos),
                    '|'.join(i.get('item_id', '') for i in itens_extraidos),
                    '|'.join(i.get('variante', '') or 'None' for i in itens_extraidos),
                    f'{tempo_ms:.2f}',
                ]
            )
