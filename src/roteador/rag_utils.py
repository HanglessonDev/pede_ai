"""RAG utilities para classificação de intenções.

DEPRECATED — Código legado, mantido apenas para compatibilidade.

Este módulo foi substituído por:
- `src/roteador/embedding_service.py` — EmbeddingService (cache + busca)
- `src/roteador/voting.py` — votar_com_prioridade
- `src/infra/embedding_providers.py` — SentenceTransformerEmbeddings

TODO: Remover este arquivo após migrar todos os imports externos.
Rastrear: `git grep rag_utils` para verificar uso.
"""

import re
from collections import Counter
from typing import Any

import numpy as np
import ollama

# Prioridade de intents: quanto menor, mais importante
# Pedir > Remover/Trocar > Carrinho > Confirmar/Cancelar > Saudacao
INTENT_PRIORITY = {
    'pedir': 1,
    'remover': 2,
    'trocar': 3,
    'carrinho': 4,
    'duvida': 5,
    'confirmar': 6,
    'negar': 7,
    'cancelar': 8,
    'saudacao': 9,
    'desconhecido': 10,
}


EMBEDDING_MODEL = 'mini-embed'

# Threshold mínimo de similaridade para incluir exemplos no RAG.
# Valor baseado na análise empírica: exemplos >= 0.55 têm relevância aceitável,
# enquanto < 0.55 tendem a ser ruído (palavras similares mas intenção diferente).
MIN_SIMILARITY_THRESHOLD = 0.55

# Lookup direto para tokens únicos (mais confiável que embedding para palavras isoladas)
TOKENS_UNICOS = {
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


def normalizar_input(texto: str) -> str:
    """Normaliza input do usuário para melhor matching de embeddings.

    - Remove pontuação (!, ?, ., ,)
    - Strip de espaços extras
    - Lowercase

    Args:
        texto: Texto original do usuário.

    Returns:
        Texto normalizado.
    """
    # Lowercase
    texto = texto.lower()
    # Strip de espaços primeiro (para pontuação no final ser detectada)
    texto = texto.strip()
    # Remove pontuação do final de palavras
    texto = re.sub(r'[!?.,]+$', '', texto)
    texto = re.sub(r'([a-z])[!?.,]+([a-z])', r'\1\2', texto)
    # Normaliza múltiplos espaços
    texto = re.sub(r'\s+', ' ', texto)
    return texto


def lookup_intencao_direta(texto: str) -> str | None:
    """Lookup direto para tokens únicos (1-2 palavras).

    Mais confiável que embedding para palavras isoladas como 'sim', 'não', 'olá'.

    Args:
        texto: Texto do usuário (será normalizado).

    Returns:
        Intenção se match encontrado, senão None.
    """
    texto = normalizar_input(texto).strip()

    # Match exato para tokens únicos
    if texto in TOKENS_UNICOS:
        return TOKENS_UNICOS[texto]

    return None


def gerar_embedding(texto: str) -> list[float]:
    """Gera embedding para um texto usando Ollama.

    Args:
        texto: Texto para gerar embedding.

    Returns:
        Lista de floats representando o embedding.
    """
    # API nova: ollama.embed() com input= (não embeddings com prompt=)
    response = ollama.embed(model=EMBEDDING_MODEL, input=texto)
    return response['embeddings'][0]


def cosine_similarity(
    a: list[float] | np.ndarray, b: list[float] | np.ndarray
) -> float:
    """Calcula similaridade cosseno entre dois vetores.

    Args:
        a: Primeiro vetor.
        b: Segundo vetor.

    Returns:
        Similaridade cosseno entre -1 e 1.
    """
    a = np.array(a)
    b = np.array(b)
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def buscar_similares(
    mensagem: str,
    exemplos: list[dict[str, Any]],
    embeddings: list[list[float]],
    top_k: int = 5,
    min_similarity: float = MIN_SIMILARITY_THRESHOLD,
) -> list[dict[str, Any]]:
    """Busca os top-k exemplos mais similares à mensagem.

    Args:
        mensagem: Mensagem do usuário.
        exemplos: Lista de exemplos com 'texto' e 'intencao'.
        embeddings: Lista de embeddings pré-computados.
        top_k: Número de resultados a retornar.
        min_similarity: Similaridade mínima para incluir exemplo (padrão: 0.55).

    Returns:
        Lista de exemplos mais similares com 'similaridade'.
        Apenas exemplos com similaridade >= min_similarity são retornados.
    """
    mensagem = normalizar_input(mensagem)
    query_emb = gerar_embedding(mensagem)
    query_vec = np.array(query_emb)

    similarities = []
    for emb in embeddings:
        emb_vec = np.array(emb)
        sim = cosine_similarity(query_vec, emb_vec)
        similarities.append(sim)

    top_indices = np.argsort(similarities)[::-1][:top_k]

    results = [
        {**exemplos[idx], 'similaridade': float(similarities[idx])}
        for idx in top_indices
    ]

    # Filtra exemplos abaixo do threshold mínimo
    results = [r for r in results if r['similaridade'] >= min_similarity]

    return results


def calcular_votacao_max(similares: list[dict[str, Any]]) -> str:
    """Voto majoritário simples: conta exemplos, ignora similaridade.

    Args:
        similares: Lista de exemplos similares com 'intencao'.

    Returns:
        Nome da intenção com mais exemplos no top-k.
    """
    if not similares:
        return 'desconhecido'

    votos = Counter(s['intencao'] for s in similares)
    return votos.most_common(1)[0][0]


def calcular_votacao_hybrid(
    similares: list[dict[str, Any]], threshold: float = 0.95
) -> str:
    """Hybrid Voting: confia no top-1 se similaridade >= threshold, senão maioria.

    Lógica:
    - Se top-1 tem similaridade >= 0.95: retorna intenção do top-1 (match exato)
    - Senão: usa voto majoritário com tiebreaker de prioridade
      (ex: empate entre saudacao e pedir → pedir vence)

    Args:
        similares: Lista de exemplos similares com 'intencao' e 'similaridade'.
        threshold: Similaridade mínima para confiar no top-1 (padrão: 0.95).

    Returns:
        Nome da intenção classificada.
    """
    if not similares:
        return 'desconhecido'

    top_sim = similares[0]['similaridade']

    # Match muito forte: confia no top-1
    if top_sim >= threshold:
        return similares[0]['intencao']

    # Ambiguidade: usa voto majoritário com tiebreaker de prioridade
    votos = Counter(s['intencao'] for s in similares)
    max_votos = votos.most_common(1)[0][1]

    # Pega todas as intents empatadas no topo
    empatadas = [intent for intent, count in votos.items() if count == max_votos]

    # Se há empate, usa prioridade como tiebreaker
    if len(empatadas) > 1:
        return min(empatadas, key=lambda i: INTENT_PRIORITY.get(i, 99))

    return votos.most_common(1)[0][0]


def calcular_votacao_com_prioridade(
    similares: list[dict[str, Any]], threshold: float = 0.95
) -> str:
    """Votação com prioridade de intents quando há múltiplas intents no top-K.

    Útil para mensagens compostas como "bom dia, quero um suco" onde
    saudação e pedido aparecem juntos.

    Regra: se há qualquer exemplo de alta prioridade (pedir, remover, trocar)
    no top-K com similaridade >= 0.55, essa intent prevalece sobre
    intents de baixa prioridade (saudacao), mesmo que saudacao tenha
    mais exemplos ou maior similaridade.

    Args:
        similares: Lista de exemplos similares com 'intencao' e 'similaridade'.
        threshold: Similaridade mínima para confiar no top-1 (padrão: 0.95).

    Returns:
        Nome da intenção classificada.
    """
    if not similares:
        return 'desconhecido'

    top_sim = similares[0]['similaridade']

    # Match muito forte (>0.98 = praticamente idêntico): confia no top-1
    if top_sim >= 0.98:
        return similares[0]['intencao']

    # Intents de alta prioridade (pedido/ação > conversação)
    ALTA_PRIORIDADE = {
        'pedir',
        'remover',
        'trocar',
        'carrinho',
        'confirmar',
        'cancelar',
    }

    # Busca a melhor intent de alta prioridade no top-K
    best_high = None
    best_high_sim = 0.0
    for s in similares:
        if s['intencao'] in ALTA_PRIORIDADE and s['similaridade'] > best_high_sim:
            best_high = s['intencao']
            best_high_sim = s['similaridade']

    # Se encontrou alta prioridade com similaridade razoável, ela vence
    if best_high and best_high_sim >= MIN_SIMILARITY_THRESHOLD:
        return best_high

    # Fallback: maioria simples
    votos = Counter(s['intencao'] for s in similares)
    return votos.most_common(1)[0][0]


def calcular_votacao(similares: list[dict[str, Any]]) -> str:
    """Calcula a intenção usando Hybrid Voting (novo padrão).

    Usa Hybrid Voting: confia no top-1 se similaridade >= 0.95,
    senão usa voto majoritário simples.

    Args:
        similares: Lista de exemplos similares com 'intencao' e 'similaridade'.

    Returns:
        Nome da intenção classificada.
    """
    return calcular_votacao_hybrid(similares)


def montar_prompt_rag(
    mensagem: str,
    similares: list[dict[str, Any]],
    intencao_dominante: str,
) -> str:
    """Monta prompt dinâmico com exemplos similares e votação.

    Args:
        mensagem: Mensagem do usuário.
        similares: Lista de exemplos similares.
        intencao_dominante: Intenção mais comum nos exemplos.

    Returns:
        Prompt formatado para o LLM.
    """
    exemplos_formatados = '\n'.join(
        f'"{s["texto"]}" → {s["intencao"]}' for s in similares[:5]
    )

    prompt = f"""Classifique a intenção do usuário em UMA palavra.
Responda APENAS o NOME DA INTENÇÃO exatamente como listado abaixo.

INTENÇÕES VÁLIDAS: saudacao, pedir, remover, trocar, carrinho, duvida, confirmar, negar, cancelar

Analise os exemplos abaixo e classifique a nova mensagem.
Cada exemplo mostra a intenção correta para aquela frase.

EXEMPLOS:
{exemplos_formatados}

Agora classifique esta mensagem:
"{mensagem}" →
"""
    return prompt
