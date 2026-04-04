# Plano de Implementação: Handler de Troca de Itens

> **Revisão 3** — pós-debate de arquitetura + análise do spacy_extrator.py  
> Data: 2026-04-03  
> Substitui completamente a Revisão 2.

---

## 1. Decisões de arquitetura

| Decisão | Escolha | Motivo |
|---------|---------|--------|
| D1 — Ambiguidade | Resposta direta sem estado (MVP). Preparado para `clarificando_troca` na Fase 2 sem quebrar interface. | Ambiguidade de troca é rara. Custo de estado extra não justifica no MVP. |
| D2 — Caso B (item + variante) | Incluir no MVP | spaCy já extrai ITEM + VARIANTE juntos. Custo quase zero. Teste 7 do projeto antigo cobre. |
| D3 — Resposta de sucesso | Mostrar carrinho atualizado completo | Consistente com `handler_pedir` e `handler_remover`. Facilita debug. |
| `item_referenciado` no State | Não adicionar | LangGraph persiste carrinho entre turnos. Inferência via carrinho cobre os casos. |
| Troca item por item diferente | Fase 2 explícita | Sprint separado: remover + pedir atômico com resposta unificada. |

---

## 2. Análise do extrator existente

### 2.1. Descoberta crítica: "pra" não é PALAVRAS_PARADA

`PALAVRAS_PARADA = {',', '.', 'com'}` — `"pra"` não está aqui.

`"pra"` é classificado pelo spaCy como `ADP` (preposição), que está em
`POS_IGNORAVEIS = {'DET', 'ADP'}`. Isso significa que em `"muda a pizza pra duplo"`,
o `"pra"` é ignorado pelo parser de remoções — o ITEM `"pizza"` e a VARIANTE
`"duplo"` são extraídos corretamente pelo EntityRuler sem nenhuma mudança.

**O caso B funciona com o extrator atual. Nenhuma mudança em PALAVRAS_PARADA.**

### 2.2. Infraestrutura reutilizável já existente

`extrair_item_carrinho` já implementa tudo que `extrair_itens_troca` vai precisar:

| Função existente | O que faz | Reuso em troca |
|-----------------|-----------|----------------|
| `_verificar_match_nome()` | Partial match por nome e item_id | Buscar item original no carrinho |
| `_verificar_match_variante()` | Match por variante | Verificar variante no carrinho |
| `_buscar_matches_no_carrinho()` | Coordena matches | Base para inferência de troca |
| `normalizar()` | Lowercase + sem acentos | Normalização de entrada |

`extrair_itens_troca` não reimplementa partial match — chama ou adapta essas funções.

### 2.3. Diferença crítica: extrator NÃO roda para 'trocar'

```python
# nodes.py — node_extrator só roda para 'pedir'
def node_extrator(state):
    if state.get('intent') == 'pedir':
        return {'itens_extraidos': extrair(mensagem)}
    return {'itens_extraidos': []}  # sempre vazio para 'trocar'!
```

**Solução:** extrair dentro do handler, como `handler_remover` já faz.

```python
# node_handler_trocar — extrai internamente
def node_handler_trocar(state):
    mensagem = state.get('mensagem_atual', '')
    carrinho = state.get('carrinho', [])
    resultado = processar_troca(carrinho, mensagem)  # extrai aqui
    return resultado.to_dict()
```

---

## 3. Escopo do MVP (Fase 1)

### 3.1. O que o MVP suporta

| Caso | Exemplo | Comportamento |
|------|---------|---------------|
| B — item + variante | `"muda a pizza pra duplo"` | Busca "pizza" no carrinho (partial match), aplica variante "duplo", recalcula preço, mostra carrinho |
| C1 — variante isolada, 1 compatível | `"muda pra duplo"` (só hambúrguer tem duplo) | Detecta que 1 item aceita a variante, troca direto |
| C2 — variante isolada, carrinho com 1 item | `"muda pra duplo"` (1 item no carrinho) | Fallback: único item, aplica variante |
| C3 — variante isolada, ambiguidade | `"muda pra lata"` (coca e suco têm lata) | Resposta direta: `"Qual item? Coca-Cola ou Suco?"` — sem estado |

### 3.2. O que NÃO está no MVP

- **Caso A** — troca item por item diferente (`"troca a coca por guaraná"`) → erro informativo
- Clarificador de trocas com estado (`etapa: clarificando_troca`) → Fase 2
- Merge de complementos e remoções na troca → Fase 2
- Labels `TAMANHO`/`SABOR` no extrator → Fase 2

---

## 4. Árvore de decisão completa

### 4.1. Árvore visual principal

```
═══════════════════════════════════════════════════════════
              ÁRVORE DE DECISÃO — TROCAR ITEM
═══════════════════════════════════════════════════════════

RAIZ: processar_troca(carrinho, mensagem)
│
├── [1] carrinho está vazio?
│   └── SIM → ✗ "Não há pedido para trocar."
│   └── NÃO ↓
│
├── [2] extrair_itens_troca(mensagem, carrinho)
│   │
│   ├── → caso = 'vazio' (0 ITEMs, 0 VARIANTEs)
│   │   └── ✗ "Não entendi o que quer trocar. Ex: 'muda pra duplo'"
│   │
│   ├── → caso = 'A' (2+ ITEMs extraídos)
│   │   │   Ex: "troca a coca por guaraná"
│   │   │
│   │   ├── [Fase 1 — MVP]
│   │   │   └── ✗ "Por enquanto só consigo trocar variantes. Ex: 'muda pra duplo'"
│   │   │
│   │   └── [Fase 2 — troca item por item]
│   │       │
│   │       ├── [3] buscar item_original (1º ITEM) no carrinho
│   │       │   └── NÃO encontrado → ✗ "'[nome]' não está no seu carrinho."
│   │       │   └── encontrado ↓
│   │       │
│   │       ├── [4] buscar item_novo (2º ITEM) no cardápio
│   │       │   └── NÃO existe → ✗ "'[nome]' não existe no cardápio."
│   │       │   └── existe ↓
│   │       │
│   │       ├── [5] item_novo tem variantes?
│   │       │   │
│   │       │   ├── SIM → [6] tem 1 variante só?
│   │       │   │   │   ├── SIM → aplica essa variante ↓
│   │       │   │   │   └── NÃO → ? pergunta qual variante
│   │       │   │   │       └── setar etapa='clarificando_variante'
│   │       │   │   │       └── adicionar à fila_clarificacao
│   │       │   │   └── NÃO ↓
│   │       │
│   │       ├── [7] remover item_original do carrinho
│   │       ├── [8] adicionar item_novo com preço calculado
│   │       └── ✓ "Trocado! Seu pedido:\n[formatar_carrinho]"
│   │
│   ├── → caso = 'B' (1 ITEM + VARIANTE opcional)
│   │   │   Ex: "muda a pizza pra duplo"
│   │   │
│   │   ├── [3] item_original foi encontrado no carrinho?
│   │   │   │   (via _verificar_match_nome + _buscar_matches_no_carrinho)
│   │   │   │
│   │   │   └── NÃO → ✗ "'[nome]' não está no seu carrinho."
│   │   │   └── SIM ↓
│   │   │       (pode ter 1 ou mais matches — troca em todos)
│   │   │
│   │   ├── [4] variante_nova foi extraída?
│   │   │   └── NÃO → ✗ "Mudar '[nome]' pra... o quê? Ex: 'muda pra duplo'"
│   │   │   └── SIM ↓
│   │   │
│   │   ├── [5] variante_nova é válida para o item?
│   │   │   │   (buscar em get_item_por_id(item_id)['variantes'][].opcao)
│   │   │   │
│   │   │   └── NÃO → ✗ "'[nome]' não tem opção '[variante]'."
│   │   │   └── SIM ↓
│   │   │
│   │   ├── [6] calcular novo preço
│   │   │   │   _calcular_preco_variante(item_id, variante, quantidade)
│   │   │   │
│   │   ├── [7] para cada match no carrinho:
│   │   │       substituir item com nova variante + novo preço
│   │   │       (preservar remocoes existentes)
│   │   │
│   │   └── ✓ "Pronto! Seu pedido:\n[formatar_carrinho]"
│   │
│   └── → caso = 'C' (0 ITEMs + 1 VARIANTE isolada)
│       │   Ex: "muda pra duplo"
│       │
│       ├── [3] variante_nova foi extraída?
│       │   └── NÃO → não deveria acontecer, mas:
│       │       └── ✗ "Não entendi. Ex: 'muda pra duplo'"
│       │   └── SIM ↓
│       │
│       ├── [4] detectar compatibilidade no carrinho
│       │   │   Iterar cada item do carrinho:
│       │   │   → get_item_por_id(item['item_id'])
│       │   │   → variante existe em item_data['variantes'][].opcao?
│       │   │   → coletar todos os compatíveis
│       │   │
│       │   ├── 0 compatíveis ↓
│       │   ├── 1 compatível ↓
│       │   └── 2+ compatíveis ↓
│       │
│       │─────────────────────────────────────────────
│       │ [4a] 2+ compatíveis (ambiguidade)
│       │   │
│       │   ├── [Fase 1 — MVP — resposta direta]
│       │   │   └── ? "Qual item? [nome1] ou [nome2]?"
│       │   │       (etapa = 'carrinho', sem estado extra)
│       │   │
│       │   └── [Fase 2 — com estado de clarificação]
│       │       └── ? "Qual item? [nome1] ou [nome2]?"
│       │           etapa = 'clarificando_troca'
│       │           pendente_troca = {variante, opcoes}
│       │           → node_clarificacao_troca aguarda resposta
│       │
│       │─────────────────────────────────────────────
│       │ [4b] 1 compatível (troca direta)
│       │   │
│       │   ├── [5] variante é válida?
│       │   │   └── NÃO → ✗ "'[item]' não tem opção '[variante]'."
│       │   │   └── SIM ↓
│       │   │
│       │   ├── [6] calcular novo preço
│       │   ├── [7] substituir item no carrinho
│       │   └── ✓ "Pronto! Seu pedido:\n[formatar_carrinho]"
│       │
│       │─────────────────────────────────────────────
│       │ [4c] 0 compatíveis → fallback
│       │   │
│       │   ├── carrinho tem 1 item?
│       │   │   │
│       │   │   ├── SIM → assumir que é o alvo
│       │   │   │   │
│       │   │   │   ├── [5] variante é válida para este item?
│       │   │   │   │   └── NÃO → ✗ "Seu item não tem opção '[variante]'."
│       │   │   │   │   └── SIM ↓
│       │   │   │   │
│       │   │   │   ├── [6] calcular novo preço
│       │   │   │   ├── [7] substituir item
│       │   │   │   └── ✓ "Pronto! Seu pedido:\n[formatar_carrinho]"
│       │   │   │
│       │   │   └── NÃO (múltiplos itens, nenhum compatível)
│       │   │       └── ✗ "Nenhum item no seu carrinho aceita '[variante]'."
│       │
│       └── [Fim do caso C]
│
└── [FIM]
```

### 4.2. Sub-árvore: clarificação de trocas (Fase 2)

```
node_clarificacao_troca(state)
│
├── pendente_troca existe?
│   └── NÃO → ✗ "Erro interno, reinicie o pedido."
│   └── SIM ↓
│
├── extrair ITEMs da mensagem
│   │   Ex: "a coca", "o primeiro", "o hambúrguer"
│   │
│   ├── 0 ITEMs extraídos
│   │   └── tentativas_clarificacao < 2?
│   │       ├── SIM → ? "Não entendi. É o [nome1] ou [nome2]?"
│   │       │         tentativas_clarificacao += 1
│   │       └── NÃO → ✗ "Sem resposta, mantive seu pedido como estava."
│   │                 limpar pendente_troca
│   │                 etapa = 'carrinho'
│   │
│   └── 1+ ITEMs extraídos ↓
│
├── encontrar match no carrinho (entre as opções pendentes)
│   │
│   ├── match encontrado ↓
│   ├── NÃO encontrado → tentativas < 2?
│   │   ├── SIM → ? "Não achei '[nome]'. É o [nome1] ou [nome2]?"
│   │   └── NÃO → ✗ "Sem resposta válida, mantive o pedido."
│   │
│   └── match encontrado ↓
│
├── aplicar variante_nova ao item encontrado
│   ├── calcular novo preço
│   ├── substituir no carrinho
│   ├── limpar pendente_troca
│   └── ✓ "Trocado! Seu pedido:\n[formatar_carrinho]"
│       etapa = 'carrinho'
```

### 4.3. Classificação da mensagem

`extrair_itens_troca()` classifica a mensagem em casos antes de qualquer lógica de negócio:

| O que spaCy extrai | Caso | Ação no MVP |
|--------------------|------|-------------|
| 2+ ITEMs | A — troca item por item | Erro informativo: funcionalidade não disponível ainda |
| 1 ITEM + VARIANTE | B — item com nova variante | Buscar item no carrinho, aplicar variante |
| 1 ITEM sem VARIANTE | B parcial | Erro: qual variante? (`"muda a pizza pra... o quê?"`) |
| 0 ITEMs + 1 VARIANTE | C — variante isolada | Cascata de inferência (seção 4.4) |
| 0 ITEMs + 0 VARIANTEs | Sem informação | Erro: não extraiu nada útil |

### 4.4. Cascata de inferência — caso C

Executar em ordem, parar no primeiro que resolver.

**Passo 1 — Detectar compatibilidade:**
Iterar o carrinho. Para cada item, verificar se a variante existe em
`item_data['variantes'][].opcao` (via `get_item_por_id`).

```
0 compatíveis → ir para passo 2
1 compatível  → troca direta (único item aceita essa variante)
2+ compatíveis → ambiguidade → resposta direta perguntando qual item (sem estado)
```

**Passo 2 — Fallback de carrinho único:**
```
len(carrinho) == 1 → assume que é o único item, aplica variante
len(carrinho) > 1  → erro: múltiplos itens, nenhum aceita a variante informada
```

### 4.5. Detecção de ambiguidade

```python
def _detectar_ambiguidade_variante(
    carrinho: list[dict], variante: str
) -> list[dict] | None:
    """
    Retorna lista de itens compatíveis se houver 2+, None caso contrário.
    Compatível = variante existe em item_data['variantes'][].opcao.
    """
    compativeis = []
    for item in carrinho:
        item_data = get_item_por_id(item['item_id'])
        if not item_data:
            continue
        variantes_validas = [v['opcao'] for v in item_data.get('variantes', [])]
        if variante in variantes_validas:
            compativeis.append(item)
    return compativeis if len(compativeis) >= 2 else None
```

Atenção: a contagem é por item do carrinho, não por item do cardápio.
Se o usuário tiver 2x hambúrguer no carrinho, conta como 2 compatíveis.

### 4.6. Recálculo de preço

```python
def _calcular_preco_variante(
    item_id: str, variante: str | None, quantidade: int
) -> int | None:
    """
    Retorna preço total em centavos, ou None se variante não existir.

    Casos:
    - Item com preco fixo (sem variantes): retorna preco * quantidade
    - Item com variantes: busca a variante específica, retorna preco * quantidade
    - Variante não encontrada: retorna None → erro ao usuário
    """
    item_data = get_item_por_id(item_id)
    if not item_data:
        return None
    # item com preco fixo
    if item_data.get('preco') is not None:
        return item_data['preco'] * quantidade
    # item com variantes
    variante_obj = next(
        (v for v in item_data.get('variantes', []) if v['opcao'] == variante),
        None,
    )
    return variante_obj['preco'] * quantidade if variante_obj else None
```

### 4.7. Tabela de todas as folhas (21 cenários)

| # | Caminho | Caso | Fase | Resultado |
|---|---------|------|------|-----------|
| 1 | `[1] SIM` | — | 1 | ✗ Carrinho vazio |
| 2 | `[2] vazio` | vazio | 1 | ✗ Nada extraído |
| 3 | `[2→A→F1]` | A | 1 | ✗ Erro informativo |
| 4 | `[2→A→F2→3 NÃO]` | A | 2 | ✗ Item não no carrinho |
| 5 | `[2→A→F2→4 NÃO]` | A | 2 | ✗ Item não no cardápio |
| 6 | `[2→A→F2→5→6 SIM]` | A | 2 | ? Clarificar variante |
| 7 | `[2→A→F2→7,8]` | A | 2 | ✓ Troca concluída |
| 8 | `[2→B→3 NÃO]` | B | 1 | ✗ Item não no carrinho |
| 9 | `[2→B→4 NÃO]` | B | 1 | ✗ Qual variante? |
| 10 | `[2→B→5 NÃO]` | B | 1 | ✗ Variante inválida |
| 11 | `[2→B→7]` | B | 1 | ✓ Troca concluída |
| 12 | `[2→C→3 NÃO]` | C | 1 | ✗ Nada extraído |
| 13 | `[2→C→4a→F1]` | C | 1 | ? Qual item? (direto) |
| 14 | `[2→C→4a→F2]` | C | 2 | ? Qual item? (estado) |
| 15 | `[2→C→4b→5 NÃO]` | C | 1 | ✗ Variante inválida |
| 16 | `[2→C→4b→7]` | C | 1 | ✓ Troca concluída |
| 17 | `[2→C→4c→SIM→5 NÃO]` | C | 1 | ✗ Variante inválida |
| 18 | `[2→C→4c→SIM→7]` | C | 1 | ✓ Troca concluída |
| 19 | `[2→C→4c→NÃO]` | C | 1 | ✗ Nenhum compatível |
| 20 | `[clarif→0 ITEMs→timeout]` | C | 2 | ✗ Timeout clarificação |
| 21 | `[clarif→match→sucesso]` | C | 2 | ✓ Troca concluída |

**Legenda:** ✗ = erro ao usuário | ? = pergunta clarificação | ✓ = sucesso

---

## 5. Todos os cenários de retorno

| Cenário | sucesso | resposta ao usuário | carrinho muda? |
|---------|---------|---------------------|----------------|
| Carrinho vazio | False | `"Não há pedido para trocar."` | Não |
| Nada extraído (0 ITEMs, 0 VARIANTEs) | False | `"Não entendi o que quer trocar. Ex: 'muda pra duplo'"` | Não |
| Caso A no MVP (2+ ITEMs) | False | `"Por enquanto só consigo trocar variantes. Ex: 'muda pra duplo'"` | Não |
| Item não encontrado no carrinho (caso B) | False | `"'[nome]' não está no seu carrinho."` | Não |
| Variante não existe para o item | False | `"[item] não tem opção '[variante]'."` | Não |
| Ambiguidade (2+ compatíveis, caso C) | False | `"Qual item? [item1] ou [item2]?"` | Não |
| Nenhum compatível + múltiplos itens | False | `"Nenhum item no seu carrinho aceita a variante '[variante]'."` | Não |
| Troca bem-sucedida | True | Carrinho atualizado formatado (igual `handler_pedir`) | Sim |

---

## 6. Componentes a implementar

### 6.1. Visão geral

```
src/extratores/spacy_extrator.py   ← adicionar extrair_itens_troca()
src/extratores/__init__.py         ← exportar extrair_itens_troca
src/graph/handlers/trocar.py       ← novo arquivo: ResultadoTrocar + processar_troca()
src/graph/nodes.py                 ← adicionar node_handler_trocar()
src/graph/builder.py               ← registrar node + mapear intent 'trocar'
src/graph/state.py                 ← nenhuma mudança necessária
tests/src/graph/handlers/test_trocar.py  ← 14 testes
```

### 6.2. `extrair_itens_troca()` — spacy_extrator.py

Nova função pública. Reutiliza `_nlp`, `normalizar`, `_verificar_match_nome`
e `_buscar_matches_no_carrinho` já existentes.

**Assinatura:**
```python
def extrair_itens_troca(mensagem: str, carrinho: list[dict]) -> dict:
    """
    Extrai informações de troca da mensagem e classifica o caso.

    Args:
        mensagem: Mensagem do usuário.
        carrinho: Carrinho atual (necessário para partial match).

    Returns:
        {
            'caso': 'A' | 'B' | 'C' | 'vazio',
            'item_original': {
                'item_id': str,       # ID do item no cardápio
                'nome': str,          # nome normalizado
                'indices': list[int], # posições no carrinho
            } | None,
            'variante_nova': str | None,
        }

    Exemplos de retorno:
        "muda a pizza pra duplo"
        → {'caso': 'B', 'item_original': {item_id: '...', nome: 'pizza', indices: [0]}, 'variante_nova': 'duplo'}

        "muda pra duplo"
        → {'caso': 'C', 'item_original': None, 'variante_nova': 'duplo'}

        "troca a coca por guaraná"  (2 ITEMs)
        → {'caso': 'A', 'item_original': None, 'variante_nova': None}

        "muda o pedido"  (sem informação útil)
        → {'caso': 'vazio', 'item_original': None, 'variante_nova': None}
    """
```

**Lógica interna:**
1. Parsear mensagem com `_nlp`
2. Coletar entidades `ITEM` e `VARIANTE` em ordem
3. Classificar:
   - 2+ ITEMs → caso A (retornar imediatamente, sem buscar no carrinho)
   - 1 ITEM → caso B: buscar no carrinho via `_verificar_match_nome`, associar VARIANTE se presente
   - 0 ITEMs + 1 VARIANTE → caso C: `item_original = None`, `variante_nova = variante`
   - 0 ITEMs + 0 VARIANTEs → caso `vazio`

**Exportar em `__init__.py`:**
```python
from .spacy_extrator import extrair, extrair_variante, extrair_item_carrinho, extrair_itens_troca

__all__ = ['extrair', 'extrair_variante', 'extrair_item_carrinho', 'extrair_itens_troca']
```

### 6.3. `handlers/trocar.py` — novo arquivo

Função pura. Não acessa `State` diretamente. Recebe tudo por parâmetro.

```python
from dataclasses import dataclass, field
from src.graph.state import ETAPAS, RetornoNode
from src.config import get_item_por_id, get_nome_item
from src.extratores import extrair_itens_troca


@dataclass
class ResultadoTrocar:
    sucesso: bool
    carrinho: list[dict] = field(default_factory=list)
    resposta: str = ''
    etapa: ETAPAS = 'carrinho'

    def to_dict(self) -> RetornoNode:
        """
        Converte para dicionário compatível com LangGraph State.

        Nota de design: não inclui fila_clarificacao propositalmente.
        Ambiguidade de troca no MVP é tratada como resposta direta.
        Quando Fase 2 implementar clarificando_troca, só o node muda,
        não esta função.
        """
        return {
            'carrinho': self.carrinho,
            'resposta': self.resposta,
            'etapa': self.etapa,
        }


def processar_troca(carrinho: list[dict], mensagem: str) -> ResultadoTrocar:
    """
    Processa troca de variante de item no carrinho.

    Args:
        carrinho: Lista de itens no carrinho atual.
        mensagem: Mensagem bruta do usuário.

    Returns:
        ResultadoTrocar com carrinho atualizado ou mensagem de erro.
    """
```

**Fluxo interno de `processar_troca`:**
```
1. carrinho vazio? → erro
2. extrair_itens_troca(mensagem, carrinho) → caso, item_original, variante_nova
3. caso == 'vazio'? → erro: não extraiu nada
4. caso == 'A'? → erro informativo (Fase 2)
5. caso == 'B'?
   a. item_original é None? → item não encontrado no carrinho
   b. variante_nova é None? → erro: qual variante?
   c. calcular novo preço → None? → variante não existe para o item
   d. substituir item no carrinho → sucesso
6. caso == 'C'?
   a. variante_nova é None? → não deveria acontecer, mas erro defensivo
   b. _detectar_ambiguidade_variante(carrinho, variante_nova)
      → 2+ compatíveis? → resposta direta com os nomes (sem estado)
   c. buscar único compatível
      → 1 encontrado? → calcular preço, substituir → sucesso
   d. fallback: len(carrinho) == 1?
      → sim? → aplicar variante ao único item
   e. fallback final → nenhum compatível, múltiplos itens → erro
```

**Helpers internos do arquivo:**
```python
def _detectar_ambiguidade_variante(carrinho, variante) -> list[dict] | None
def _calcular_preco_variante(item_id, variante, quantidade) -> int | None
def _substituir_item(carrinho, indice, novo_item_dict) -> list[dict]
def _formatar_carrinho(carrinho) -> str  # igual ao handler_pedir
```

### 6.4. `node_handler_trocar()` — nodes.py

```python
def node_handler_trocar(state: State) -> RetornoNode:
    """
    Processa troca de variante de item no pedido.

    Extrai informações da mensagem internamente (não usa itens_extraidos
    do State, pois node_extrator só roda para intent='pedir').

    Args:
        state: Estado atual do grafo.

    Returns:
        Dicionário com carrinho, resposta e etapa atualizados.

    Note:
        Fase 2: quando clarificador de trocas for implementado,
        este node passará a setar etapa='clarificando_troca' em casos
        de ambiguidade, em vez de apenas retornar resposta direta.
        A interface de processar_troca não muda.
    """
    carrinho = state.get('carrinho', [])
    mensagem = state.get('mensagem_atual', '')
    resultado = processar_troca(carrinho, mensagem)
    return resultado.to_dict()
```

### 6.5. `builder.py` — 3 mudanças

```python
# 1. import
from src.graph.handlers.trocar import processar_troca  # via node

# 2. add_node
builder.add_node('handler_trocar', node_handler_trocar)

# 3. add_conditional_edges — adicionar ao mapeamento existente
{
    ...
    'handler_trocar': 'handler_trocar',  # ← adicionar
}

# 4. add_edge
builder.add_edge('handler_trocar', END)
```

O `_decidir_por_intent` já mapeia `intent → node_name`.
Basta adicionar a entrada `'trocar': 'handler_trocar'` no dicionário existente.

---

## 7. Testes — 14 casos

Arquivo: `tests/src/graph/handlers/test_trocar.py`

| # | Nome | Cenário | Caso |
|---|------|---------|------|
| 1 | `test_trocar_variante_sucesso` | Variante isolada, 1 compatível → troca direta | C1 |
| 2 | `test_trocar_item_com_variante_sucesso` | `"muda a pizza pra duplo"` → item + variante | B |
| 3 | `test_trocar_carrinho_vazio` | Carrinho vazio → erro | — |
| 4 | `test_trocar_sem_item_especificado` | Mensagem sem item nem variante extraível | vazio |
| 5 | `test_trocar_ambiguidade_multiplos` | 2+ itens compatíveis → pergunta qual | C3 |
| 6 | `test_trocar_sem_ambiguidade_unico` | 1 compatível → troca direta sem perguntar | C1 |
| 7 | `test_trocar_inferencia_carrinho` | Variante isolada, 0 compatíveis, 1 item no carrinho → fallback | C2 |
| 8 | `test_trocar_multiplos_sem_especificar` | Variante isolada, 0 compatíveis, múltiplos itens → erro | C2 fail |
| 9 | `test_trocar_item_nao_encontrado` | `"muda a coca pra duplo"` mas coca não está no carrinho | B fail |
| 10 | `test_trocar_carrinho_unico` | Variante isolada, 1 item no carrinho, aceita variante → troca | C1 |
| 11 | `test_trocar_multiplos_extraidos` | `"troca a coca por guaraná"` → erro informativo MVP | A |
| 12 | `test_trocar_item_nao_identificado` | Item extraído mas sem match no carrinho | B fail |
| 13 | `test_trocar_item_referenciado` | Adaptado do antigo: fallback de carrinho único | C2 |
| 14 | `test_trocar_sem_compatibilidade` | Variante não existe em nenhum item do cardápio | C fail |

**Padrão de fixture:**

```python
@pytest.fixture
def carrinho_simples():
    return [{'item_id': 'lanche_001', 'quantidade': 1, 'preco': 1500, 'variante': 'simples'}]

@pytest.fixture
def carrinho_multiplos():
    return [
        {'item_id': 'lanche_001', 'quantidade': 1, 'preco': 1500, 'variante': 'simples'},
        {'item_id': 'bebida_001', 'quantidade': 1, 'preco': 500, 'variante': 'lata'},
    ]
```

---

## 8. Fase 2 — detalhamento completo

### 8.1. Caso A: troca item por item diferente

**Trigger:** `"troca a coca por guaraná"`, `"muda o hambúrguer por x-salada"`

**Complexidade:** média. É um `remover` + `pedir` atômico.

**Lógica:**
```
1. extrair_itens_troca retorna caso='A' com 2 ITEMs
2. item_original = primeiro ITEM (buscar no carrinho por partial match)
3. item_novo = segundo ITEM (buscar no cardápio, não no carrinho)
4. item_original não encontrado no carrinho → erro
5. item_novo não existe no cardápio → erro
6. item_novo tem variantes? → fila_clarificacao (igual ao handler_pedir)
7. senão → remover item_original, adicionar item_novo com preço calculado
8. resposta unificada: "Trocado! Seu pedido: ..." (não mostrar "removido + adicionado")
```

**Componentes a adicionar:**
- `extrair_itens_troca` já retorna caso A com 2 ITEMs — sem mudança no extrator
- `processar_troca`: adicionar branch para caso A, chamando internamente
  `_remover_item` e `_adicionar_item` (funções a extrair do handler_remover e handler_pedir)
- Se item_novo tiver variantes → precisa de clarificação → aqui entra `fila_clarificacao`

**Dependência:** Refatoração para extrair funções puras de `handler_remover.py`
e `handler_pedir.py` antes de reusar em `trocar.py`.

### 8.2. Clarificador de trocas com estado

**Trigger:** ambiguidade no caso C — `"muda pra duplo"` com 2+ itens compatíveis

**Complexidade:** alta. Novo estado persistido.

**O que muda:**
```python
# state.py — adicionar nova etapa
ETAPAS = Literal[
    'inicio', 'clarificando_variante', 'clarificando_troca',  # ← nova
    'confirmando', 'pedindo', 'carrinho', 'saudacao', 'finalizado', 'coletando'
]

# State — adicionar campo
class State(TypedDict):
    ...
    pendente_troca: dict | None  # {'variante': 'duplo', 'opcoes': [...]} — nova chave
```

**Novo node `node_clarificacao_troca`:**
```python
def node_clarificacao_troca(state):
    """
    Processa resposta do usuário durante clarificação de qual item trocar.
    
    Diferente de node_clarificacao (que resolve variante de pedido),
    este node resolve qual item do carrinho é o alvo da troca.
    """
    mensagem = state.get('mensagem_atual', '')
    pendente = state.get('pendente_troca', {})
    carrinho = state.get('carrinho', [])
    # identifica qual item o usuário escolheu
    # aplica a variante pendente ao item escolhido
    # limpa pendente_troca
```

**Mudanças no builder:**
```python
# nova aresta condicional em _decidir_entrada
if state.get('etapa') == 'clarificando_troca':
    return 'clarificacao_troca'

# novo node
builder.add_node('clarificacao_troca', node_clarificacao_troca)
builder.add_edge('clarificacao_troca', END)
```

**Mudança no `node_handler_trocar` (Fase 2):**
```python
# no MVP: retorna resposta direta
if ambiguidade:
    return {'resposta': f"Qual item? {nomes}", 'etapa': 'carrinho'}

# na Fase 2: seta estado de clarificação
if ambiguidade:
    return {
        'resposta': f"Qual item? {nomes}",
        'etapa': 'clarificando_troca',
        'pendente_troca': {'variante': variante_nova, 'opcoes': compativeis},
    }
```

A interface de `processar_troca` não muda. Só o node muda.

### 8.3. Labels TAMANHO/SABOR no extrator

**Trigger:** `"muda a pizza pra grande"` quando "grande" não é uma variante no cardápio
mas sim um tamanho genérico

**Complexidade:** média. Expansão do EntityRuler.

**O que muda em `spacy_extrator.py`:**
```python
# novos labels no EntityRuler
TAMANHOS = {'pequeno', 'pequena', 'medio', 'media', 'grande', 'gigante', 'familia'}
SABORES = {'calabresa', 'mussarela', 'frango', ...}  # domínio específico

# gerar_patterns: adicionar patterns para TAMANHO e SABOR
for tamanho in TAMANHOS:
    patterns.append({'label': 'TAMANHO', 'pattern': tamanho})
```

**`extrair_itens_troca` passa a retornar também `tamanho` e `sabor`:**
```python
{
    'caso': 'B',
    'item_original': {...},
    'variante_nova': None,  # continua para variantes do cardápio
    'tamanho_novo': 'grande',  # novo campo
    'sabor_novo': None,
}
```

**Dependência:** requer mapeamento `tamanho → variante` no cardápio, ou
normalização dos dados do cardápio para incluir `tamanhos[]` e `sabores[]`
além de `variantes[]`.

### 8.4. Merge completo de atributos

**Trigger:** `"muda a pizza dupla sem cebola"` — variante + remoção juntas

**Complexidade:** baixa (dependente de TAMANHO/SABOR estar pronto).

**O que muda:** `processar_troca` passa a preservar `remocoes` do item original
e mesclar com as novas remoções extraídas da mensagem de troca.

```python
# ao criar o novo item após troca
novo_item = {
    **item_original,
    'variante': variante_nova or item_original['variante'],
    'preco': novo_preco,
    'remocoes': novas_remocoes or item_original.get('remocoes', []),
}
```

---

## 9. Ordem de implementação

### Fase 1 (MVP)

| Passo | Arquivo | O que fazer |
|-------|---------|-------------|
| 1 | `spacy_extrator.py` | Implementar `extrair_itens_troca()`. Reutilizar `_verificar_match_nome` e `_buscar_matches_no_carrinho`. Exportar em `__init__.py`. |
| 2 | `handlers/trocar.py` | Criar arquivo. `ResultadoTrocar` + `processar_troca()` + helpers internos. |
| 3 | `nodes.py` | Adicionar `node_handler_trocar()`. Importar `processar_troca`. |
| 4 | `builder.py` | `add_node`, `add_conditional_edges` (`'trocar': 'handler_trocar'`), `add_edge` para END. |
| 5 | `tests/` | 14 testes em `tests/src/graph/handlers/test_trocar.py`. |

### Fase 2 (futura)

| Passo | Arquivo | O que fazer |
|-------|---------|-------------|
| 1 | `spacy_extrator.py` | Adicionar labels `TAMANHO` e `SABOR` ao EntityRuler. |
| 2 | `state.py` | Adicionar etapa `'clarificando_troca'` e campo `pendente_troca`. |
| 3 | `handlers/trocar.py` | Branch para caso A (remover + pedir atômico). |
| 4 | `nodes.py` | `node_clarificacao_troca()`. |
| 5 | `builder.py` | Nova aresta condicional para `clarificacao_troca`. |
| 6 | `nodes.py` | Atualizar `node_handler_trocar` para setar `etapa='clarificando_troca'` em ambiguidade. |
| 7 | `tests/` | Testes para caso A e clarificação de trocas. |

---

## 10. Notas de design

**Por que `ResultadoTrocar` não tem `fila_clarificacao`:**
A `fila_clarificacao` foi desenhada para "qual variante do item X?" e ao ser resolvida
chama `_processar_variante_valida` que adiciona ao carrinho. Para troca, o fluxo é
diferente — a clarificação é "qual item trocar?", não "qual variante?". Reutilizar a
fila aqui criaria um bug: o `clarificacao` handler tentaria resolver como variante
de pedido ao invés de como seleção de item para troca.

No MVP, ambiguidade é resposta direta. Na Fase 2, o campo `pendente_troca` no State
resolve isso com um handler dedicado, sem contaminar `fila_clarificacao`.

**Por que não adicionar `item_referenciado` ao State:**
O projeto antigo precisava desse campo porque não tinha estado persistido entre turnos.
O LangGraph com `SqliteSaver` persiste o `carrinho` entre mensagens. A cascata de
inferência (compatibilidade → carrinho único) cobre os casos que `item_referenciado`
resolvia, sem precisar de um campo extra que precisa ser mantido e limpo.

**Interface estável entre Fase 1 e Fase 2:**
A assinatura de `processar_troca(carrinho, mensagem)` e o `ResultadoTrocar.to_dict()`
não mudam entre fases. O que muda é o comportamento do `node_handler_trocar` e a
adição do `node_clarificacao_troca`. Refatorações futuras ficam isoladas nos nodes,
sem impactar a lógica de negócio em `handlers/trocar.py`.
