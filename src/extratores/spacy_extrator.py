import re
import unicodedata

import spacy

from src.config import get_cardapio

# ── Constantes ──────────────────────────────────────────────────────────────

_PUNCTUATION_RE = re.compile(r'[^\w\s]')
_WHITESPACE_RE = re.compile(r'\s+')
PALAVRAS_REMOCAO = {'sem', 'tira', 'remove', 'retira', 'nao coloca'}
PALAVRAS_PARADA = {',', '.', 'com'}
CONECTIVOS = {'e', 'ou'}
POS_IGNORAVEIS = {'DET', 'ADP'}
NUMEROS_ESCRITOS = {
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

# ── Normalização ────────────────────────────────────────────────────────────


def normalizar(texto: str) -> str:
    texto = texto.lower()
    texto = unicodedata.normalize('NFKD', texto)
    texto = texto.encode('ascii', 'ignore').decode('utf-8')
    texto = _PUNCTUATION_RE.sub('', texto)
    texto = texto.replace('-', ' ')
    texto = _WHITESPACE_RE.sub(' ', texto).strip()
    return texto


# ── Geração de patterns ─────────────────────────────────────────────────────


def _adicionar_pattern(
    lista_patterns: list[dict], vistos: set, label: str, texto_bruto: str, item_id: str
):
    texto = normalizar(texto_bruto)
    chave = (label, texto)
    if chave not in vistos:
        vistos.add(chave)
        tokens = texto.split()
        if len(tokens) == 1:
            lista_patterns.append(dict(label=label, pattern=texto, id=item_id))
        else:
            # Token pattern: matcha "x tudo" (tokenizados separados)
            lista_patterns.append(
                dict(label=label, pattern=[{'LOWER': t} for t in tokens], id=item_id)
            )
            # String pattern: matcha "x-tudo" (token único com hífen)
            unico = texto.replace(' ', '-')
            if unico not in vistos:
                vistos.add((label, unico))
                lista_patterns.append(dict(label=label, pattern=unico, id=item_id))


def gerar_patterns(cardapio: dict) -> list[dict]:
    patterns = []
    vistos = set()

    for item in cardapio['itens']:
        _adicionar_pattern(patterns, vistos, 'ITEM', item.get('nome'), item.get('id'))

        for alias in item.get('aliases') or []:
            _adicionar_pattern(patterns, vistos, 'ITEM', alias, item.get('id'))

        for variante in item.get('variantes') or []:
            _adicionar_pattern(
                patterns, vistos, 'VARIANTE', variante.get('opcao'), item.get('id')
            )

    patterns.extend(
        [{'label': 'QTD', 'pattern': palavra} for palavra in NUMEROS_ESCRITOS]
    )

    return patterns


# ── Captura de remoções ─────────────────────────────────────────────────────


def _pular_artigos(tokens: list, indice: int) -> int:
    """Pula artigos e preposições a partir do índice."""
    while indice < len(tokens) and tokens[indice].pos_ in POS_IGNORAVEIS:
        indice += 1
    return indice


def _deve_parar_no_conectivo(tokens: list, indice_conectivo: int) -> bool:
    """
    Decide se deve parar no conectivo 'e'/'ou'.

    Para se o próximo token não-artigo for outro sinal de remoção
    ou uma quantidade (início de novo item).
    Ex: 'sem cebola e sem tomate' → para (novo sinal de remoção)
    Ex: 'tira tomate e cebola' → continua (mesmo sinal)
    Ex: 'sem cebola e 1 x-salada' → para (quantidade = novo item)
    """
    indice = _pular_artigos(tokens, indice_conectivo + 1)
    if indice >= len(tokens):
        return False
    return (
        tokens[indice].text.lower() in PALAVRAS_REMOCAO or tokens[indice].text.isdigit()
    )


def capturar_remocoes(doc) -> list[tuple[str, int]]:
    """
    Captura itens a remover após sinais como 'sem', 'tira', etc.

    Args:
        doc: Documento spaCy processado.

    Returns:
        Lista de tuplas (texto, índice_do_token).
    """
    remocoes = []
    tokens = list(doc)
    indice = 0

    while indice < len(tokens):
        token = tokens[indice]

        if token.text.lower() not in PALAVRAS_REMOCAO:
            indice += 1
            continue

        # Encontrou sinal de remoção, captura itens seguintes
        indice += 1
        while indice < len(tokens):
            token = tokens[indice]

            # Conectivos: decide se para ou continua
            if token.text.lower() in CONECTIVOS:
                if _deve_parar_no_conectivo(tokens, indice):
                    break
                indice += 1
                continue

            # Palavras de parada obrigatória
            if token.text.lower() in PALAVRAS_PARADA:
                break

            # Ignora artigos/preposições
            if token.pos_ in POS_IGNORAVEIS:
                indice += 1
                continue

            # Token relevante: adiciona às remoções
            remocoes.append((token.text, token.i))
            indice += 1

    return remocoes


# ── Setup do NLP ────────────────────────────────────────────────────────────

_nlp = spacy.load('pt_core_news_sm')
_ruler = _nlp.add_pipe('entity_ruler', before='ner')
_ruler.add_patterns([{'label': 'QTD', 'pattern': [{'IS_DIGIT': True}]}])

_cardapio = get_cardapio()
_patterns = gerar_patterns(_cardapio)
_ruler.add_patterns(_patterns)


# ── API pública ─────────────────────────────────────────────────────────────


def extrair(mensagem: str) -> list[dict]:
    doc = _nlp(mensagem)

    qtd_pendente = 1
    remocoes_fila = capturar_remocoes(doc)
    prox_remocao = 0
    itens: list[dict] = []
    item_atual = None

    def _consumir_remocoes_ate(limite: int):
        nonlocal prox_remocao
        while (
            prox_remocao < len(remocoes_fila)
            and remocoes_fila[prox_remocao][1] < limite
        ):
            if item_atual:
                item_atual['remocoes'].append(remocoes_fila[prox_remocao][0])
            prox_remocao += 1

    for ent in doc.ents:
        # Consome remoções que estão antes desta entidade
        if item_atual:
            _consumir_remocoes_ate(ent.start)

        if ent.label_ == 'QTD':
            texto = normalizar(ent.text)
            qtd_pendente = (
                int(ent.text) if texto.isdigit() else NUMEROS_ESCRITOS.get(texto, 1)
            )

        elif ent.label_ == 'ITEM':
            if item_atual:
                itens.append(item_atual)
            item_atual = {
                'item_id': ent.ent_id_,
                'quantidade': qtd_pendente,
                'variante': None,
                'remocoes': [],
            }
            qtd_pendente = 1

        elif ent.label_ == 'VARIANTE' and item_atual:
            item_atual['variante'] = ent.text

    # Consome remoções restantes pro último item
    if item_atual:
        _consumir_remocoes_ate(len(doc))
        itens.append(item_atual)

    return itens


__all__ = ['extrair']
