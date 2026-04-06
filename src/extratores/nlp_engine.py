"""Engine NLP com lazy initialization.

Wrapper do spaCy que elimina side effects no import.
O modelo so e carregado na primeira chamada de processar().

Example:
    ```python
    from src.extratores.config import get_extrator_config
    from src.extratores.nlp_engine import NlpEngine

    engine = NlpEngine(get_extrator_config(), cardapio)
    doc = engine.processar('quero um x-bacon')
    ```
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import spacy

from src.extratores.normalizador import normalizar_para_busca
from src.extratores.patterns import gerar_patterns

if TYPE_CHECKING:
    from spacy.tokens import Doc

    from src.extratores.config import ExtratorConfig


class NlpEngine:
    """Wrapper do spaCy com lazy initialization.

    Elimina side effects no import. O modelo spaCy e o EntityRuler
    so sao inicializados na primeira chamada de processar().

    Attributes:
        config: Configuracao do extrator.
        cardapio: Dados do cardapio para gerar patterns.
    """

    def __init__(self, config: ExtratorConfig, cardapio: dict) -> None:
        """Inicializa o engine sem carregar o modelo.

        Args:
            config: Configuracao com thresholds e parametros.
            cardapio: Dados do cardapio para gerar patterns.
        """
        self._config = config
        self._cardapio = cardapio
        self._nlp: spacy.language.Language | None = None
        self._patterns_gerados: bool = False

    def _inicializar(self) -> None:
        """Carrega modelo e configura EntityRuler (lazy)."""
        if self._nlp is not None:
            return

        self._nlp = spacy.load(self._config.spacy_model)
        ruler = self._nlp.add_pipe('entity_ruler', before='ner')
        ruler.add_patterns([{'label': 'NUM_PENDING', 'pattern': [{'IS_DIGIT': True}]}])
        ruler.add_patterns(
            [
                {'label': 'NUM_PENDING', 'pattern': [{'LOWER': 'meio'}]},
                {'label': 'NUM_PENDING', 'pattern': [{'LOWER': 'meia'}]},
            ]
        )

        # Patterns para numeros por extenso → NUM_PENDING
        patterns_numeros = [
            {'label': 'NUM_PENDING', 'pattern': [{'LOWER': num}]}
            for num in self._config.numeros_escritos
        ]
        ruler.add_patterns(patterns_numeros)

        # Gerar e adicionar patterns do cardapio
        patterns = gerar_patterns(self._cardapio, normalizar_para_busca)
        ruler.add_patterns(patterns)
        self._patterns_gerados = True

    def processar(self, mensagem: str) -> Doc:
        """Processa mensagem com o pipeline NLP.

        Carrega o modelo na primeira chamada (lazy).

        Args:
            mensagem: Texto da mensagem do usuario.

        Returns:
            Documento spaCy processado com entidades.
        """
        self._inicializar()
        return self._nlp(mensagem)  # type: ignore[return-value]

    @property
    def inicializado(self) -> bool:
        """Retorna True se o modelo ja foi carregado."""
        return self._nlp is not None

    @property
    def nlp(self) -> spacy.language.Language | None:
        """Retorna o objeto spaCy (ou None se nao inicializado).

        Para uso interno — prefira processar().
        """
        return self._nlp
