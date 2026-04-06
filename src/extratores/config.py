"""Configuracao do extrator de itens do cardapio.

Centraliza thresholds, stopwords, numeros escritos e parametros do spaCy.

Example:
    ```python
    from src.extratores.config import get_extrator_config

    config = get_extrator_config()
    config.fuzzy_item_cutoff  # 75
    ```
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ExtratorConfig:
    """Configuracao imutavel do extrator.

    Attributes:
        fuzzy_item_cutoff: Score minimo para fuzzy match de itens (0-100).
        fuzzy_variante_cutoff: Score minimo para fuzzy match de variantes (0-100).
        ambiguidade_limite: Diferenca maxima entre top-2 scores para considerar ambiguo.
        palavras_remocao: Palavras que indicam remocao de ingrediente.
        palavras_parada: Palavras que interrompem captura de remocoes.
        conectivos: Conectivos que podem separar remocoes.
        pos_ignoraveis: POS tags do spaCy a ignorar (DET, ADP).
        numeros_escritos: Mapeamento de numeros por extenso para inteiros.
        stop_words: Stop words para fuzzy matching.
        spacy_model: Nome do modelo spaCy a carregar.
        palavras_complemento: Palavras que indicam complementos de um item.
        numeros_fracionarios: Mapeamento de numeros fracionarios por extenso.
        palavras_negacao: Palavras e expressoes que indicam negacao/cancelamento.
        palavras_filtro_remocao: Palavras comuns que NUNCA devem ser capturadas como remocoes.
    """

    fuzzy_item_cutoff: int = 75
    fuzzy_variante_cutoff: int = 75
    ambiguidade_limite: int = 5
    palavras_remocao: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {'sem', 'tira', 'remove', 'retira', 'nao coloca'}
        )
    )
    palavras_parada: frozenset[str] = field(
        default_factory=lambda: frozenset({',', '.', 'com'})
    )
    conectivos: frozenset[str] = field(default_factory=lambda: frozenset({'e', 'ou'}))
    pos_ignoraveis: frozenset[str] = field(
        default_factory=lambda: frozenset({'DET', 'ADP'})
    )
    numeros_escritos: Mapping[str, int] = field(
        default_factory=lambda: {
            'um': 1,
            'uma': 1,
            'dois': 2,
            'duas': 2,
            'tres': 3,
            'quatro': 4,
            'cinco': 5,
            'seis': 6,
            'sete': 7,
            'oito': 8,
            'nove': 9,
            'dez': 10,
        }
    )
    stop_words: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {
                'quero',
                'quer',
                'me',
                'da',
                'de',
                'do',
                'um',
                'uma',
                'uns',
                'umas',
                'o',
                'a',
                'os',
                'as',
                'e',
                'ou',
                'pra',
                'para',
                'por',
                'pelo',
                'pela',
                'no',
                'na',
                'nos',
                'nas',
                'muda',
                'mudar',
                'troca',
                'trocar',
                'coloca',
                'bota',
                'veja',
                'ver',
                'mostra',
                'mostrar',
                'pode',
                'favor',
                'por favor',
                'aqui',
                'ali',
                'isso',
                'isto',
                'esse',
                'essa',
            }
        )
    )
    spacy_model: str = 'pt_core_news_sm'
    palavras_complemento: frozenset[str] = field(
        default_factory=lambda: frozenset({'com', 'extra', 'adicional'})
    )
    numeros_fracionarios: Mapping[str, float] = field(
        default_factory=lambda: {
            'meio': 0.5,
            'meia': 0.5,
            'um e meio': 1.5,
            'uma e meia': 1.5,
        }
    )
    palavras_negacao: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {
                'nao',
                'não',
                'nem',
                'quero nao',
                'quero não',
                'esquece',
                'esqueça',
                'cancela',
                'cancelar',
                'deixa pra la',
                'deixa para lá',
                'deixa',
                'desisto',
                'muda de ideia',
            }
        )
    )
    palavras_filtro_remocao: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {
                # Cortesia / polidez
                'favor',
                'gentileza',
                'obrigado',
                'obrigada',
                # Intensificadores / restritivos
                'também',
                'tambem',
                'ainda',
                'mais',
                'so',
                'só',
                'apenas',
                # Temporais / posicionais
                'alem',
                'além',
                'depois',
                'antes',
                'durante',
                # Qualificadores genericos
                'basico',
                'básico',
                'normal',
                'padrao',
                'padrão',
                # Pronomes indefinidos
                'nada',
                'tudo',
                'algo',
                'coisa',
                # Verbos auxiliares
                'pode',
                'ser',
                'poder',
                'será',
                'sera',
                # Preposicoes e artigos que escapam do POS filter
                'por',
                'pra',
                'para',
                'com',
                'sem',
                'de',
                'do',
                'da',
            }
        )
    )


class _ExtratorCache:
    """Cache lazy para configuracao do extrator."""

    _config: ExtratorConfig | None = None

    @classmethod
    def carregar(cls) -> ExtratorConfig:
        """Retorna configuracao com cache lazy."""
        if cls._config is None:
            cls._config = ExtratorConfig()
        return cls._config


def get_extrator_config() -> ExtratorConfig:
    """Retorna configuracao do extrator (cached).

    Returns:
        ExtratorConfig com todos os parametros.
    """
    return _ExtratorCache.carregar()
