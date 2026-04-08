"""Container para loggers de observabilidade — injeção direta, zero registry.

Substitui o modulo registry.py com 20+ funcoes getter/setter por uma
dataclass simples que pode ser injetada via construtor ou context.

Example:
    ```python
    from src.observabilidade.loggers import ObservabilidadeLoggers

    # Criar com paths padrao
    loggers = ObservabilidadeLoggers.criar_padrao('logs')

    # Injetar no grafo
    graph = criar_graph(loggers=loggers)

    # Ou desativar para testes
    loggers.desativar_todos()
    ```
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.observabilidade.decisor_logger import DecisorLogger
    from src.observabilidade.exception_logger import ExceptionLogger
    from src.observabilidade.fluxo_logger import FluxoLogger
    from src.observabilidade.negocio_logger import NegocioLogger


@dataclass
class ObservabilidadeLoggers:
    """Container para todos os loggers — injeção direta, zero registry.

    Attributes:
        negocio: Logger de metricas de negocio (confirmar, cancelar, ticket).
        decisor: Logger de decision tracing (cada bifurcação de decisão).
        fluxo: Logger de fluxo de execução (por onde passou, tempos).
        excecoes: Logger de exceções (stack traces + estado).
    """

    negocio: NegocioLogger | None = None
    decisor: DecisorLogger | None = None
    fluxo: FluxoLogger | None = None
    excecoes: ExceptionLogger | None = None

    # Cache interno de paths para recriação
    _log_dir: Path = field(default=Path('logs'), init=False, repr=False)

    @classmethod
    def criar_padrao(cls, log_dir: Path | str = 'logs') -> ObservabilidadeLoggers:
        """Cria loggers com paths padrão.

        Args:
            log_dir: Diretorio para arquivos de log.

        Returns:
            Instancia com todos os loggers configurados.
        """
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        # Importação tardia para evitar ciclo
        from src.observabilidade.decisor_logger import DecisorLogger  # noqa: PLC0415
        from src.observabilidade.exception_logger import ExceptionLogger  # noqa: PLC0415
        from src.observabilidade.fluxo_logger import FluxoLogger  # noqa: PLC0415
        from src.observabilidade.negocio_logger import NegocioLogger  # noqa: PLC0415

        instance = cls(
            negocio=NegocioLogger(log_path / 'negocio.csv'),
            decisor=DecisorLogger(log_path / 'decisoes.csv'),
            fluxo=FluxoLogger(log_path / 'fluxo.csv'),
            excecoes=ExceptionLogger(log_path / 'erros.jsonl'),
        )
        instance._log_dir = log_path
        return instance

    def desativar_todos(self) -> None:
        """Desativa todos os loggers (útil para testes)."""
        self.negocio = None
        self.decisor = None
        self.fluxo = None
        self.excecoes = None

    def ativar_debug(self) -> None:
        """Recria loggers se foram desativados."""
        if self.negocio is None and self._log_dir:
            novo = self.criar_padrao(self._log_dir)
            self.negocio = novo.negocio
            self.decisor = novo.decisor
            self.fluxo = novo.fluxo
            self.excecoes = novo.excecoes
