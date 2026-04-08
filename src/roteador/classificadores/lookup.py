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

from typing import TYPE_CHECKING

from src.roteador.classificadores.base import ClassificadorBase
from src.roteador.modelos import ResultadoClassificacao

if TYPE_CHECKING:
    from src.observabilidade.loggers import ObservabilidadeLoggers

# Tokens unicos mapeados para intents
# Sao palavras isoladas onde match exato e mais confiavel que embedding
TOKENS_UNICOS: dict[str, str] = {
    'sim': 'confirmar',
    'não': 'negar',
    'nao': 'negar',
    # saudações
    'olá': 'saudacao',
    'ola': 'saudacao',
    'oi': 'saudacao',
    'opa': 'saudacao',
    'bom dia': 'saudacao',
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

    def __init__(
        self,
        tokens_unicos: dict[str, str] | None = None,
        loggers: ObservabilidadeLoggers | None = None,
    ) -> None:
        """Inicializa o classificador de lookup.

        Args:
            tokens_unicos: Dicionario token -> intencao.
                Usa TOKENS_UNICOS padrao se None.
            loggers: Loggers de observabilidade para decision tracing.
        """
        self._tokens = tokens_unicos or TOKENS_UNICOS
        self._loggers = loggers

    def classificar(
        self,
        mensagem: str,
        thread_id: str = '',
        turn_id: str = '',
    ) -> ResultadoClassificacao | None:
        """Tenta classificar por match exato.

        Args:
            mensagem: Texto normalizado do usuario.
            thread_id: ID da sessao para correlacao de logs.
            turn_id: ID do turno para correlacao de logs.

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
            if self._loggers and self._loggers.decisor:
                self._loggers.decisor.registrar(
                    thread_id=thread_id,
                    turn_id=turn_id,
                    componente='classificacao_lookup',
                    decisao='nao_encontrado',
                    alternativas=[],
                    criterio='nenhum_token_exato',
                    threshold='match_exato',
                    resultado='None',
                    contexto={'mensagem': mensagem},
                )
            return None

        intencao = self._tokens[texto]

        if self._loggers and self._loggers.decisor:
            primeiros_5 = list(self._tokens.keys())[:5]
            self._loggers.decisor.registrar(
                thread_id=thread_id,
                turn_id=turn_id,
                componente='classificacao_lookup',
                decisao='retornar_intent',
                alternativas=primeiros_5,
                criterio=f"token_exato: '{texto}'",
                threshold='match_exato',
                resultado=intencao,
                contexto={'mensagem': mensagem},
            )

        return ResultadoClassificacao(
            intent=intencao,
            confidence=1.0,
            caminho='lookup',
            top1_texto=texto,
            top1_intencao=intencao,
            mensagem_norm=texto,
            metadados={'lookup': intencao},
        )
