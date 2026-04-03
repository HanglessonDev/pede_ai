"""Logger de observabilidade para classificacao de intents.

Registra eventos de classificacao em um CSV append-only para analise posterior.
Thread-safe para uso com FastAPI.
"""

import csv
import threading
from datetime import datetime, UTC
from pathlib import Path

CAMINHOS_VALIDOS = {'lookup', 'rag_forte', 'llm_rag', 'llm_fixo', 'desconhecido'}

HEADERS = [
    'timestamp',
    'thread_id',
    'mensagem',
    'mensagem_norm',
    'intent',
    'confidence',
    'caminho',
    'top1_texto',
    'top1_intencao',
]


class ObservabilidadeLogger:
    """Logger thread-safe para registrar eventos de classificacao.

    Attributes:
        csv_path: Caminho do arquivo CSV.
        _lock: Lock para thread-safety.
    """

    def __init__(self, csv_path: Path | str) -> None:
        """Inicializa o logger.

        Args:
            csv_path: Caminho para o arquivo CSV de eventos.
        """
        self.csv_path = Path(csv_path)
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

        # Cria CSV com headers se nao existir
        if not self.csv_path.exists():
            with open(self.csv_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=HEADERS)
                writer.writeheader()

    def registrar(
        self,
        thread_id: str,
        mensagem: str,
        mensagem_norm: str,
        intent: str,
        confidence: float,
        caminho: str,
        top1_texto: str,
        top1_intencao: str,
    ) -> None:
        """Registra um evento de classificacao no CSV.

        Args:
            thread_id: Identificador da conversa (LangGraph config).
            mensagem: Input bruto do usuario.
            mensagem_norm: Input apos normalizacao.
            intent: Intencao classificada.
            confidence: Confianca da classificacao (0.0-1.0).
            caminho: Fluxo usado ('lookup', 'rag_forte', 'llm_rag', 'llm_fixo', 'desconhecido').
            top1_texto: Texto do exemplo mais similar.
            top1_intencao: Intencao do exemplo mais similar.
        """
        if caminho not in CAMINHOS_VALIDOS:
            raise ValueError(f'Caminho invalido: {caminho}. Validos: {CAMINHOS_VALIDOS}')

        evento = {
            'timestamp': datetime.now(UTC).isoformat(),
            'thread_id': thread_id,
            'mensagem': mensagem,
            'mensagem_norm': mensagem_norm,
            'intent': intent,
            'confidence': confidence,
            'caminho': caminho,
            'top1_texto': top1_texto,
            'top1_intencao': top1_intencao,
        }

        with self._lock, open(self.csv_path, 'a', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=HEADERS)
            writer.writerow(evento)
