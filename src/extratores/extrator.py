"""Extrator principal de itens do cardapio.

API publica com compatibilidade retroativa — retorna dicts
para nao quebrar consumidores existentes.

Example:
    ```python
    from src.extratores.extrator import extrair, extrair_variante

    extrair('2 x-bacon sem cebola')
    [
        {
            'item_id': 'lanche_003',
            'quantidade': 2,
            'variante': None,
            'remocoes': ['cebola'],
        }
    ]
    ```
"""

from __future__ import annotations

from dataclasses import asdict

from src.extratores.config import ExtratorConfig
from src.extratores.fuzzy_extrator import fuzzy_match_item, fuzzy_match_variante
from src.extratores.modelos import ItemExtraido
from src.extratores.nlp_engine import NlpEngine
from src.extratores.normalizador import normalizar_para_fuzzy
from src.extratores.remocoes import capturar_remocoes


class Extrator:
    """Extrator de itens do cardapio via spaCy + fuzzy fallback."""

    def __init__(self, engine: NlpEngine, config: ExtratorConfig) -> None:
        """Inicializa o extrator.

        Args:
            engine: NlpEngine com modelo spaCy lazy-loaded.
            config: Configuracao do extrator.
        """
        self._engine = engine
        self._config = config

    def extrair(self, mensagem: str) -> list[ItemExtraido]:
        """Extrai itens do cardapio de uma mensagem.

        Tenta EntityRuler (spaCy) primeiro. Se nao encontrar itens,
        usa fuzzy matching como fallback para tolerar typos.

        Args:
            mensagem: Texto da mensagem do usuario.

        Returns:
            Lista de ItemExtraido.
        """
        doc = self._engine.processar(mensagem)

        itens_spacy = self._extrair_spacy(doc)

        # EntityRuler encontrou itens — usa direto
        if itens_spacy:
            return itens_spacy

        # Fallback: tenta fuzzy matching para tolerar typos
        return self._extrair_fuzzy(mensagem)

    def _extrair_spacy(self, doc) -> list[ItemExtraido]:
        """Extrai itens via spaCy EntityRuler."""
        qtd_pendente = 1
        remocoes_fila = capturar_remocoes(doc, self._config)
        prox_remocao = 0
        itens: list[ItemExtraido] = []
        item_atual: ItemExtraido | None = None

        def _consumir_remocoes_ate(limite: int) -> None:
            nonlocal prox_remocao
            nonlocal item_atual
            while (
                prox_remocao < len(remocoes_fila)
                and remocoes_fila[prox_remocao][1] < limite
            ):
                if item_atual is not None:
                    item_atual = ItemExtraido(
                        item_id=item_atual.item_id,
                        quantidade=item_atual.quantidade,
                        variante=item_atual.variante,
                        remocoes=[*item_atual.remocoes, remocoes_fila[prox_remocao][0]],
                    )
                prox_remocao += 1

        for ent in doc.ents:
            if item_atual is not None:
                _consumir_remocoes_ate(ent.start)

            if ent.label_ == 'QTD':
                texto = ent.text.lower()
                qtd_pendente = (
                    int(ent.text)
                    if ent.text.isdigit()
                    else self._config.numeros_escritos.get(texto, 1)
                )

            elif ent.label_ == 'ITEM':
                if item_atual is not None:
                    itens.append(item_atual)
                item_atual = ItemExtraido(
                    item_id=ent.ent_id_,
                    quantidade=qtd_pendente,
                    variante=None,
                    remocoes=[],
                )
                qtd_pendente = 1

            elif ent.label_ == 'VARIANTE' and item_atual is not None:
                item_atual = ItemExtraido(
                    item_id=item_atual.item_id,
                    quantidade=item_atual.quantidade,
                    variante=ent.text,
                    remocoes=item_atual.remocoes,
                )

        if item_atual is not None:
            _consumir_remocoes_ate(len(doc))
            itens.append(item_atual)

        return itens

    def _extrair_fuzzy(self, mensagem: str) -> list[ItemExtraido]:
        """Fallback com fuzzy matching quando EntityRuler nao acha nada.

        Args:
            mensagem: Mensagem original do usuario.

        Returns:
            Lista com 0 ou 1 ItemExtraido encontrado via fuzzy.
        """
        from src.config import get_cardapio  # noqa: PLC0415 — lazy loading

        cardapio = get_cardapio()
        alias_para_id: dict[str, str] = {}
        for item in cardapio.get('itens', []):
            alias_para_id[item['nome'].lower()] = item['id']
            for alias in item.get('aliases', []):
                alias_para_id[alias.lower()] = item['id']

        alias, _score, item_id = fuzzy_match_item(mensagem, alias_para_id)
        if item_id is None:
            return []

        # Tenta extrair variante do texto restante
        item_cfg = next(
            (i for i in cardapio.get('itens', []) if i['id'] == item_id), None
        )
        variante = None
        if item_cfg and item_cfg.get('variantes'):
            variantes = [v['opcao'] for v in item_cfg['variantes']]
            texto_sem_item = (
                normalizar_para_fuzzy(mensagem).replace(alias or '', '').strip()
            )
            if texto_sem_item:
                var_match, _var_score = fuzzy_match_variante(texto_sem_item, variantes)
                if var_match:
                    variante = var_match

        return [
            ItemExtraido(
                item_id=item_id,
                quantidade=1,
                variante=variante,
                remocoes=[],
            )
        ]

    def extrair_variante(self, mensagem: str, item_id: str) -> str | None:
        """Extrai e valida uma variante de uma mensagem para um item especifico.

        Args:
            mensagem: Texto da mensagem do usuario.
            item_id: ID do item no cardapio para validacao.

        Returns:
            Texto da variante valida ou None.
        """
        if not mensagem or not mensagem.strip():
            return None

        doc = self._engine.processar(mensagem)
        for ent in doc.ents:
            if ent.label_ == 'VARIANTE' and ent.ent_id_ == item_id:
                return ent.text

        return None


# ── API publica compativel com a versao procedural ─────────────────────────

_extrator: Extrator | None = None


def _get_extrator() -> Extrator:
    """Retorna extrator singleton lazy."""
    global _extrator  # noqa: PLW0603 — lazy singleton intencional
    if _extrator is None:
        from src.config import get_cardapio  # noqa: PLC0415 — lazy loading
        from src.extratores.config import get_extrator_config  # noqa: PLC0415
        from src.extratores.nlp_engine import NlpEngine  # noqa: PLC0415

        config = get_extrator_config()
        cardapio = get_cardapio()
        engine = NlpEngine(config, cardapio)
        _extrator = Extrator(engine, config)
    return _extrator


def extrair(mensagem: str) -> list[dict]:
    """Extrai itens do cardapio de uma mensagem do usuario.

    API compativel com a versao procedural — retorna list[dict].

    Args:
        mensagem: Texto da mensagem do usuario.

    Returns:
        Lista de dicionarios com as chaves:
            - item_id: ID do item no cardapio.
            - quantidade: Quantidade solicitada.
            - variante: Variante selecionada (ou None).
            - remocoes: Lista de ingredientes a remover.

    Example:
        ```python
        from src.extratores import extrair

        extrair('2 x-bacon sem cebola')
        [
            {
                'item_id': 'lanche_003',
                'quantidade': 2,
                'variante': None,
                'remocoes': ['cebola'],
            }
        ]
        ```
    """
    itens = _get_extrator().extrair(mensagem)
    return [asdict(item) for item in itens]


def extrair_variante(mensagem: str, item_id: str) -> str | None:
    """Extrai e valida uma variante de uma mensagem para um item especifico.

    Args:
        mensagem: Texto da mensagem do usuario.
        item_id: ID do item no cardapio para validacao.

    Returns:
        Texto da variante valida ou None.
    """
    return _get_extrator().extrair_variante(mensagem, item_id)
