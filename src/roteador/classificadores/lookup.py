"""Classificador por lookup direto de tokens unicos.

Para palavras isoladas como 'sim', 'nao', 'oi', 'cancela' —
match exato e mais confiavel que embedding.

Example:
    ```python
    from src.roteador.classificadores.lookup import ClassificadorLookup

    lookup = ClassificadorLookup({'oi': 'saudacao', 'sim': 'confirmar'})
    resultado = lookup.classificar('oi')
    resultado.intent  # 'saudacao'
    ```
"""

from __future__ import annotations

from src.roteador.classificadores.base import ClassificadorBase
from src.roteador.modelos import ResultadoClassificacao

# Tokens unicos mapeados para intents
# Sao palavras isoladas onde match exato e mais confiavel que embedding
TOKENS_UNICOS: dict[str, str] = {
    'sim': 'confirmar',
    'não': 'negar',
    'nao': 'negar',
    'olá': 'saudacao',
    'ola': 'saudacao',
    'oi': 'saudacao',
    'opa': 'saudacao',
    'cancela': 'cancelar',
    'esquece': 'cancelar',
    'tira': 'remover',
    'remove': 'remover',
    'muda': 'trocar',
    'troca': 'trocar',
}


class ClassificadorLookup(ClassificadorBase):
    """Lookup direto de tokens unicos.

    Faz match exato da mensagem normalizada contra um dicionario
    de tokens unicos. Se encontrar, retorna com confianca 1.0.
    """

    def __init__(self, tokens_unicos: dict[str, str] | None = None) -> None:
        """Inicializa o classificador de lookup.

        Args:
            tokens_unicos: Dicionario token -> intencao.
                Usa TOKENS_UNICOS padrao se None.
        """
        self._tokens = tokens_unicos or TOKENS_UNICOS

    def classificar(self, mensagem: str) -> ResultadoClassificacao | None:
        """Tenta classificar por match exato.

        Args:
            mensagem: Texto normalizado do usuario.

        Returns:
            ResultadoClassificacao se match encontrado, None caso contrario.

        Example:
            ```python
            lookup = ClassificadorLookup()
            lookup.classificar('oi')
            ResultadoClassificacao(intent='saudacao', confidence=1.0, ...)
            ```
        """
        texto = mensagem.strip().lower()

        if texto not in self._tokens:
            return None

        intencao = self._tokens[texto]

        return ResultadoClassificacao(
            intent=intencao,
            confidence=1.0,
            caminho='lookup',
            top1_texto=texto,
            top1_intencao=intencao,
            mensagem_norm=texto,
        )
