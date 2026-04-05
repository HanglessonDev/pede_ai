"""Loader de configuracao do roteador de intencoes.

Carrega config/roteador.yml e fornece acesso via dataclass imutavel.

Example:
    ```python
    from src.config import get_roteador_config

    config = get_roteador_config()
    config.rag_forte_threshold  # 0.95
    ```
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path(__file__).parent.parent.parent / 'config'


@dataclass(frozen=True)
class RoteadorConfig:
    """Configuracao imutavel do classificador de intencoes.

    Attributes:
        rag_forte_threshold: Se confianca >= threshold, usa RAG direto sem LLM.
        rag_fraco_threshold: Se confianca < threshold, usa fallback LLM puro.
        min_similarity: Similaridade minima para incluir exemplo na votacao.
        max_chars: Truncamento maximo da mensagem.
        top_k: Numero de exemplos similares a buscar.
        alta_prioridade: Intents de alta prioridade (acao > conversacao).
        llm_provider: Nome do provider LLM ('groq' ou 'ollama').
        llm_model: Nome do modelo LLM a usar.
        embedding_model: Nome do modelo de embedding.
        embedding_cache_path: Caminho do cache de embeddings.
        exemplos_path: Caminho do arquivo de exemplos.
    """

    rag_forte_threshold: float
    rag_fraco_threshold: float
    min_similarity: float
    max_chars: int
    top_k: int
    alta_prioridade: frozenset[str]
    llm_provider: str
    llm_model: str
    embedding_model: str
    embedding_cache_path: Path
    exemplos_path: Path


class _RoteadorCache:
    """Cache lazy para configuracao do roteador."""

    _config: RoteadorConfig | None = None

    @classmethod
    def carregar(cls) -> RoteadorConfig:
        """Carrega roteador.yml com cache lazy."""
        if cls._config is None:
            cls._config = cls._parsear_yaml()
        return cls._config

    @classmethod
    def _parsear_yaml(cls) -> RoteadorConfig:
        """Le e parseia roteador.yml em RoteadorConfig."""
        caminho = CONFIG_DIR / 'roteador.yml'
        with open(caminho, encoding='utf-8') as f:
            dados: dict[str, Any] = yaml.safe_load(f)

        classif = dados['classificador']
        llm = dados['llm']
        embedding = dados['embedding']
        dados_cfg = dados['dados']

        provider = llm['provider']
        if provider == 'groq':
            llm_model = llm['groq']['model']
        else:
            llm_model = llm['ollama']['model']

        return RoteadorConfig(
            rag_forte_threshold=float(classif['rag_forte_threshold']),
            rag_fraco_threshold=float(classif['rag_fraco_threshold']),
            min_similarity=float(classif['min_similarity']),
            max_chars=int(classif['max_chars']),
            top_k=int(classif['top_k']),
            alta_prioridade=frozenset(classif['alta_prioridade']),
            llm_provider=provider,
            llm_model=llm_model,
            embedding_model=embedding['model'],
            embedding_cache_path=Path(embedding['cache_path']),
            exemplos_path=Path(dados_cfg['exemplos_path']),
        )


def get_roteador_config() -> RoteadorConfig:
    """Retorna configuracao do roteador (cached).

    Returns:
        RoteadorConfig com todos os parametros carregados do YAML.

    Example:
        ```python
        config = get_roteador_config()
        config.rag_forte_threshold
        0.95
        ```
    """
    return _RoteadorCache.carregar()
