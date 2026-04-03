"""Logger de observabilidade para classificação de intents.

Este módulo fornece o `ObservabilidadeLogger` para registrar eventos de
classificação em um arquivo CSV append-only. Cada evento captura informações
detalhadas sobre como uma mensagem do usuário foi classificada.

O logger é thread-safe, projetado para uso seguro em aplicações FastAPI com
múltiplas requisições concorrentes.

Example:
    ```python
    from src.observabilidade import ObservabilidadeLogger

    logger = ObservabilidadeLogger("logs/eventos.csv")
    logger.registrar(
        thread_id="sessao_123",
        mensagem="Quero um X-Burguer",
        mensagem_norm="querer x-burguer",
        intent="pedido_lanche",
        confidence=0.95,
        caminho="rag_forte",
        top1_texto="quero um x-burguer",
        top1_intencao="pedido_lanche",
    )
    ```

Note:
    O arquivo CSV é criado automaticamente se não existir. O diretório pai
    também é criado automaticamente.

Warning:
    O caminho `caminho` deve ser um dos valores válidos definidos em
    `CAMINHOS_VALIDOS`. Um `ValueError` será levantado para valores inválidos.
"""

import csv
import threading
from datetime import datetime, UTC
from pathlib import Path

CAMINHOS_VALIDOS = {'lookup', 'rag_forte', 'llm_rag', 'llm_fixo', 'desconhecido'}
"""Conjunto de caminhos válidos para o parâmetro `caminho`.

Os caminhos representam os diferentes fluxos de classificação:

- `lookup`: Correspondência exata via dicionário de intenções
- `rag_forte`: Classificação RAG com alta confiança (>= threshold)
- `llm_rag`: Fallback para LLM quando RAG não atingiu confiança suficiente
- `llm_fixo`: LLM com prompt fixo (sem contexto RAG)
- `desconhecido`: Intent não reconhecida

Example:
    ```python
    'rag_forte' in CAMINHOS_VALIDOS
    True
    'caminho_invalido' in CAMINHOS_VALIDOS
    False
    ```
"""

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
"""Cabeçalhos do arquivo CSV de eventos.

Cada coluna representa:

- `timestamp`: Data/hora ISO do evento (UTC)
- `thread_id`: Identificador único da sessão/conversa
- `mensagem`: Texto original do usuário
- `mensagem_norm`: Texto após normalização
- `intent`: Intent classificada pelo sistema
- `confidence`: Nível de confiança (0.0 a 1.0)
- `caminho`: Fluxo de classificação utilizado
- `top1_texto`: Texto do exemplo mais similar no banco
- `top1_intencao`: Intent do exemplo mais similar
"""


class ObservabilidadeLogger:
    """Logger thread-safe para registrar eventos de classificação.

    Este logger escreve em um arquivo CSV append-only, onde cada linha
    representa um evento de classificação. É seguro para uso com múltiplas
    threads (FastAPI).

    Attributes:
        csv_path: Caminho absoluto do arquivo CSV onde os eventos são
            registrados.

    Example:
        ```python
        from src.observabilidade import ObservabilidadeLogger

        logger = ObservabilidadeLogger("logs/classificacoes.csv")
        logger.registrar(
            thread_id="user_42",
            mensagem="Me vê uma coca cola",
            mensagem_norm="me ver coca cola",
            intent="pedido_bebida",
            confidence=0.88,
            caminho="rag_forte",
            top1_texto="quero uma coca cola",
            top1_intencao="pedido_bebida",
        )
        ```

    Note:
        O logger é thread-safe através de um `threading.Lock`. Múltiplas
        threads podem chamar `registrar()` simultaneamente sem risco de
        corrupção de dados.
    """

    def __init__(self, csv_path: Path | str) -> None:
        """Inicializa o logger criando o arquivo CSV se necessário.

        O diretório pai é criado automaticamente se não existir. Se o
        arquivo CSV já existir, os eventos serão adicionados ao final
        (append).

        Args:
            csv_path: Caminho para o arquivo CSV de eventos. Pode ser uma
                string ou objeto `Path`.

        Example:
            ```python
            from pathlib import Path
            from src.observabilidade import ObservabilidadeLogger

            # Com string
            logger = ObservabilidadeLogger("logs/eventos.csv")

            # Com Path
            logger = ObservabilidadeLogger(Path("logs/eventos.csv"))
            ```

        Note:
            O arquivo CSV é criado com os cabeçalhos definidos em `HEADERS`.
            Se o arquivo já existir, novos eventos são adicionados ao final.
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
        """Registra um evento de classificação no CSV.

        Cada chamada adiciona uma nova linha ao arquivo CSV com todas as
        informações sobre a classificação realizada.

        Args:
            thread_id: Identificador único da conversa (LangGraph
                `configurable.thread_id`).
            mensagem: Input bruto do usuário (texto original).
            mensagem_norm: Input após normalização (minúsculas, sem acentos).
            intent: Intenção classificada pelo sistema
                (ex: "pedido_lanche", "pedido_bebida").
            confidence: Confiança da classificação, de 0.0 a 1.0.
            caminho: Fluxo de classificação utilizado. Deve ser um dos
                valores em `CAMINHOS_VALIDOS`.
            top1_texto: Texto do exemplo mais similar encontrado no banco.
            top1_intencao: Intenção associada ao exemplo mais similar.

        Raises:
            ValueError: Se `caminho` não estiver em `CAMINHOS_VALIDOS`.

        Example:
            Registrando uma classificação via RAG:

            ```python
            logger = ObservabilidadeLogger("logs/eventos.csv")
            logger.registrar(
                thread_id="sessao_abc",
                mensagem="Quero dois X-Salada e uma coca",
                mensagem_norm="querer dois x-salada e uma coca",
                intent="pedido_combinado",
                confidence=0.92,
                caminho="rag_forte",
                top1_texto="quero um x-salada e uma coca",
                top1_intencao="pedido_combinado",
            )
            ```

            Registrando um fallback para LLM (baixa confiança):

            ```python
            logger.registrar(
                thread_id="sessao_xyz",
                mensagem="Tem algo sem glúten?",
                mensagem_norm="ter algo sem gluten",
                intent="informacao_nutricional",
                confidence=0.45,
                caminho="llm_rag",
                top1_texto="quais opcoes sem gluten",
                top1_intencao="informacao_nutricional",
            )
            ```

        Note:
            O timestamp é gerado automaticamente em UTC. A operação é
            atômica e thread-safe.
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
