"""Segmentacao de itens multiplos.

Fase 4.2 — Camada 2: Segmentacao de Itens Multiplos.

Duas abordagens sao testadas:
- Entity-Anchor: usa posicoes dos ITEMs como ancora para dividir segmentos
- noun_chunks: usa spaCy noun_chunks como segmentador natural

Ambas retornam list[Segmento] com indices de token (nao caractere).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from spacy.tokens import Doc


@dataclass(frozen=True)
class Segmento:
    """Fatia do texto para processamento por camada.

    Attributes:
        texto: Texto completo da mensagem (referencia).
        start: Indice de token inicial (nao caractere).
        end: Indice de token final (exclusive).
    """

    texto: str
    start: int  # índice de TOKEN
    end: int  # índice de TOKEN (exclusive)


def segmentar_itens_entity_anchor(doc: Doc, entidades) -> list[Segmento]:
    """Divide a frase em segmentos usando posicoes dos ITEMs como ancora.

    Cada ITEM detectado vira o nucleo de um segmento. Os limites do segmento
    sao definidos pelo fim do item anterior e inicio do proximo item.

    Args:
        doc: Documento spaCy processado.
        entidades: Lista de entidades (Span) do documento.

    Returns:
        Lista de Segmento com start/end em indices de token.
    """
    itens_pos = [(e.start, e.end) for e in entidades if e.label_ == 'ITEM']
    if len(itens_pos) <= 1:
        return [Segmento(doc.text, 0, len(doc))]

    segmentos: list[Segmento] = []
    for i, (_start, _end) in enumerate(itens_pos):
        seg_start = itens_pos[i - 1][1] if i > 0 else 0
        seg_end = itens_pos[i + 1][0] if i + 1 < len(itens_pos) else len(doc)
        segmentos.append(Segmento(doc.text, seg_start, seg_end))

    return segmentos


def segmentar_itens_noun_chunks(doc: Doc, entidades) -> list[Segmento]:
    """Divide a frase usando noun_chunks do spaCy.

    Noun chunks sao grupos nominais naturais que tendem a corresponder
    a itens individuais em pedidos.

    Args:
        doc: Documento spaCy processado.
        entidades: Lista de entidades (Span) do documento (nao usado diretamente).

    Returns:
        Lista de Segmento com start/end em indices de token.
    """
    chunks = list(doc.noun_chunks)
    chunks_validos = [c for c in chunks if len(c.text.strip()) > 1]

    if len(chunks_validos) <= 1:
        return [Segmento(doc.text, 0, len(doc))]

    return [Segmento(doc.text, c.start, c.end) for c in chunks_validos]
