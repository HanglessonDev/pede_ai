"""Módulo de observabilidade para classificação de intents.

Este módulo fornece ferramentas para registrar e analisar eventos de
classificação do Pede AI. Permite:

- **Registrar eventos**: Cada classificação é logada em um CSV com
  detalhes como confiança, caminho usado (lookup, RAG, LLM) e o
  exemplo mais similar.
- **Analisar dados**: Consultas DuckDB prontas para extrair insights
  dos logs, como casos de baixa confiança e distribuição de caminhos.

Componentes principais:

- `ObservabilidadeLogger`: Logger thread-safe para registrar eventos
  de classificação em CSV.

Example:
    ```python
    from src.observabilidade import ObservabilidadeLogger
    from src.observabilidade.consultas import distribuicao_caminhos

    # Registrar evento
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

    # Analisar distribuição de caminhos
    dist = distribuicao_caminhos("logs/eventos.csv")
    for item in dist:
        print(f"{item['caminho']}: {item['total']} eventos")
    ```

Note:
    Os logs são armazenados em CSV para facilitar análise posterior
    com DuckDB, pandas ou ferramentas de visualização.

See Also:
    - `ObservabilidadeLogger`: Classe principal para registrar eventos.
    - `src.observabilidade.consultas`: Funções de análise com DuckDB.
"""

from src.observabilidade.logger import ObservabilidadeLogger

__all__ = ['ObservabilidadeLogger']
