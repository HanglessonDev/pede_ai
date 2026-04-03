"""Logger para eventos de clarificação de variantes.

Registra eventos de clarificação em um CSV append-only para análise posterior.
Thread-safe para uso com FastAPI.
"""

import csv
import threading
from datetime import UTC, datetime
from pathlib import Path

RESULTADOS_VALIDOS = {'sucesso', 'invalida_reprompt', 'invalida_desistiu'}

HEADERS = [
    'timestamp',
    'thread_id',
    'item_id',
    'nome_item',
    'campo',
    'opcoes',
    'mensagem',
    'tentativas',
    'resultado',
    'variante_escolhida',
]


class ClarificacaoLogger:
    """Logger thread-safe para registrar eventos de clarificação.

    Cada linha do CSV representa uma tentativa de clarificação de variante
    (ex: simples/duplo, tamanho P/M/G).

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
        item_id: str,
        nome_item: str,
        campo: str,
        opcoes: list[str],
        mensagem: str,
        tentativas: int,
        resultado: str,
        variante_escolhida: str = '',
    ) -> None:
        """Registra um evento de clarificação no CSV.

        Args:
            thread_id: Identificador único da sessão/conversa.
            item_id: ID do item no cardápio.
            nome_item: Nome legível do item.
            campo: Tipo de clarificação (ex: 'variante').
            opcoes: Lista de opções válidas oferecidas ao usuário.
            mensagem: Resposta do usuário.
            tentativas: Número de tentativas falhas antes deste evento.
            resultado: Um de 'sucesso', 'invalida_reprompt', 'invalida_desistiu'.
            variante_escolhida: Variante selecionada (apenas se sucesso).

        Raises:
            ValueError: Se resultado não estiver em RESULTADOS_VALIDOS.
        """
        if resultado not in RESULTADOS_VALIDOS:
            raise ValueError(
                f'Resultado invalido: {resultado}. Validos: {RESULTADOS_VALIDOS}'
            )

        with self._lock, open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    datetime.now(UTC).isoformat(),
                    thread_id,
                    item_id,
                    nome_item,
                    campo,
                    ','.join(opcoes),
                    mensagem,
                    tentativas,
                    resultado,
                    variante_escolhida,
                ]
            )
