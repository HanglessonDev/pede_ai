"""
Extrator spaCy para NLP em português.

Processa mensagens do usuário para extrair itens do cardápio,
quantidades, variantes e remoções usando o modelo pt_core_news_sm.

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

import re
import unicodedata

import spacy

from src.config import get_cardapio, get_nome_item


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
    """
    Normaliza um texto para busca fuzzy.

    Aplica lowercase, normalização Unicode (remove acentos),
    remove pontuação e normaliza espaços.

    Args:
        texto: Texto original a ser normalizado.

    Returns:
        Texto normalizado em minúsculas sem acentos.

    Example:
        ```python
        normalizar('X-Tudo!')
        'xtudo'
        ```
    """
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
    """
    Adiciona patterns de entidade ao lista de patterns.

    Gera múltiplas representações do mesmo texto (tokenizado,
    com hífen, etc.) para melhorar o matching.

    Args:
        lista_patterns: Lista de patterns para adicionar.
        vistos: Conjunto de patterns já adicionados (para evitar duplicatas).
        label: Rótulo da entidade (ITEM, VARIANTE, etc.).
        texto_bruto: Texto original do item/variante.
        item_id: ID do item no cardápio.
    """
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
    """
    Gera patterns de entidade para o EntityRuler do spaCy.

    Cria patterns para todos os itens, aliases, variantes do cardápio
    e números escritos por extenso.

    Args:
        cardapio: Dicionário com dados do cardápio.

    Returns:
        Lista de patterns no formato spaCy EntityRuler.

    Example:
        ```python
        cardapio = get_cardapio()
        patterns = gerar_patterns(cardapio)
        len(patterns) > 0
        True
        ```
    """
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
    """
    Pula artigos e preposições a partir do índice.

    Ignora tokens com POS em POS_IGNORAVEIS (DET, ADP).

    Args:
        tokens: Lista de tokens do documento spaCy.
        indice: Índice inicial para começar a verificação.

    Returns:
        Novo índice após pular artigos/preposições.
    """
    while indice < len(tokens) and tokens[indice].pos_ in POS_IGNORAVEIS:
        indice += 1
    return indice


def _deve_parar_no_conectivo(tokens: list, indice_conectivo: int) -> bool:
    """
    Decide se deve parar no conectivo 'e'/'ou'.

    Args:
        tokens: Lista de tokens do documento spaCy.
        indice_conectivo: Índice do token conectivo ('e' ou 'ou').

    Returns:
        True se deve parar no conectivo, False para continuar.

    Note:
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
    """
    Extrai itens do cardápio de uma mensagem do usuário.

    Processa a mensagem usando spaCy com EntityRuler treinado
    para identificar itens, quantidades, variantes e remoções.

    Args:
        mensagem: Texto da mensagem do usuário.

    Returns:
        Lista de dicionários com as chaves:
            - item_id: ID do item no cardápio.
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


def extrair_variante(mensagem: str, item_id: str) -> str | None:
    """
    Extrai e valida uma variante de uma mensagem para um item específico.

    Usa o EntityRuler para identificar apenas variantes que pertencem
    ao item especificado. Retorna None se nenhuma variante válida for
    encontrada ou se a mensagem for vazia.

    Args:
        mensagem: Texto da mensagem do usuário.
        item_id: ID do item no cardápio para validação.

    Returns:
        Texto da variante válida ou None.

    Example:
        ```python
        from src.extratores import extrair_variante

        extrair_variante('duplo', 'lanche_001')
        'duplo'
        extrair_variante('lata', 'lanche_001')  # lata é de bebida
        None
        ```
    """
    if not mensagem or not mensagem.strip():
        return None

    doc = _nlp(mensagem)
    for ent in doc.ents:
        if ent.label_ == 'VARIANTE' and ent.ent_id_ == item_id:
            return ent.text

    return None


def _buscar_matches_no_carrinho(
    itens_mencionados: list[dict], carrinho: list
) -> list[dict]:
    """Busca itens mencionados no carrinho e retorna matches."""
    resultados = []
    indices_ja_adicionados = set()

    for item_mencionado in itens_mencionados:
        texto_mencionado = item_mencionado['texto']
        variante_mencionada = item_mencionado['variante']

        for i, item_carrinho in enumerate(carrinho):
            if i in indices_ja_adicionados:
                continue

            nome_item = (
                get_nome_item(item_carrinho['item_id']) or item_carrinho['item_id']
            )
            nome_normalizado = normalizar(nome_item)
            variante_carrinho = normalizar(item_carrinho.get('variante') or '')

            match_nome = _verificar_match_nome(
                texto_mencionado,
                item_mencionado['ent_id'],
                item_carrinho['item_id'],
                nome_normalizado,
            )
            match_variante = _verificar_match_variante(
                variante_mencionada, variante_carrinho
            )

            if match_nome and match_variante:
                _adicionar_ou_atualizar_resultado(
                    resultados, item_carrinho, i, indices_ja_adicionados
                )

    return resultados


def _verificar_match_nome(
    texto_mencionado: str | None,
    ent_id: str,
    item_id_carrinho: str,
    nome_normalizado: str,
) -> bool:
    """Verifica se há match por nome ou ID."""
    if texto_mencionado and texto_mencionado in nome_normalizado:
        return True
    return ent_id == item_id_carrinho


def _verificar_match_variante(
    variante_mencionada: str | None, variante_carrinho: str
) -> bool:
    """Verifica se há match por variante."""
    if variante_mencionada:
        return variante_mencionada in variante_carrinho
    return True


def _adicionar_ou_atualizar_resultado(
    resultados: list[dict],
    item_carrinho: dict,
    indice: int,
    indices_ja_adicionados: set,
):
    """Adiciona ou atualiza resultado existente."""
    existente = next(
        (r for r in resultados if r['item_id'] == item_carrinho['item_id']), None
    )
    if existente:
        existente['indices'].append(indice)
    else:
        resultados.append(
            {
                'item_id': item_carrinho['item_id'],
                'variante': item_carrinho.get('variante'),
                'indices': [indice],
            }
        )
    indices_ja_adicionados.add(indice)


def extrair_item_carrinho(mensagem: str, carrinho: list) -> list[dict]:
    """
    Extrai itens do carrinho para remoção com base na mensagem do usuário.

    Usa spaCy para identificar itens mencionados e faz match com os itens
    no carrinho. Suporta match parcial por nome e match exato com variantes.

    Args:
        mensagem: Texto da mensagem do usuário (ex: "tira a coca", "tira tudo").
        carrinho: Lista de itens no carrinho atual.

    Returns:
        Lista de dicionários com:
            - item_id: ID do item a remover.
            - variante: Variante específica ou None.
            - indices: Lista de índices no carrinho que matcham.

    Note:
        TODO (Fase 2):
        - Suportar quantidade ("tira UMA coca" → remove 1 unidade)
        - Clarificação quando ambíguo (2 itens similares no carrinho)
        - Remoção de variantes específicas em frases como "sem cebola"

        MVP (Fase 1):
        - Remove TODOS os matches (ignora quantidade)
        - Match parcial por nome normalizado
        - "tira tudo" limpa carrinho inteiro
        - Match exato se mencionar variante

    Example:
        ```python
        carrinho = [
            {'item_id': 'lanche_001', 'quantidade': 2, 'variante': None},
            {'item_id': 'bebida_001', 'quantidade': 1, 'variante': 'lata'},
        ]
        extrair_item_carrinho('tira a coca', carrinho)
        [{'item_id': 'bebida_001', 'variante': 'lata', 'indices': [1]}]
        ```
    """
    if not mensagem or not mensagem.strip():
        return []

    if not carrinho:
        return []

    # Caso especial: "tira tudo"
    if 'tira tudo' in normalizar(mensagem) or 'remove tudo' in normalizar(mensagem):
        return [
            {
                'item_id': item['item_id'],
                'variante': item.get('variante'),
                'indices': [i],
            }
            for i, item in enumerate(carrinho)
        ]

    # Extrair itens mencionados na mensagem
    doc = _nlp(mensagem)
    itens_mencionados = []

    for ent in doc.ents:
        if ent.label_ == 'ITEM':
            itens_mencionados.append(
                {'texto': normalizar(ent.text), 'variante': None, 'ent_id': ent.ent_id_}
            )
        elif ent.label_ == 'VARIANTE':
            if itens_mencionados:
                itens_mencionados[-1]['variante'] = normalizar(ent.text)
            else:
                itens_mencionados.append(
                    {
                        'texto': '',
                        'variante': normalizar(ent.text),
                        'ent_id': ent.ent_id_,
                    }
                )

    return _buscar_matches_no_carrinho(itens_mencionados, carrinho)


__all__ = ['extrair', 'extrair_item_carrinho', 'extrair_variante']
