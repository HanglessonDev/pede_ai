"""Resumo rapido da validacao - sem emojis."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.extratores import extrair

with open("tests/dataset_extrator_deepseek.json", encoding="utf-8") as f:
    data = json.load(f)

total = len(data)
acertos = 0
erros_cat = {}
for ex in data:
    r = extrair(ex["mensagem"])
    # Compare as items como sets (ordem nao importa para multi-itens)
    def item_key(item):
        return (item.get("item_id"), item.get("quantidade"))

    esperado_set = set(item_key(e) for e in ex["esperado"])
    obteve_set = set(item_key(r_item) for r_item in r)

    if esperado_set == obteve_set:
        acertos += 1
    else:
        cat = ex.get("categoria", "?")
        erros_cat[cat] = erros_cat.get(cat, 0) + 1

pct = acertos / total * 100 if total else 0
print(f"Total: {total}")
print(f"Acertos: {acertos}")
print(f"Erros: {total - acertos}")
print(f"Acuracia: {pct:.0f}%")
if erros_cat:
    print("Erros por categoria:")
    for k, v in sorted(erros_cat.items(), key=lambda x: -x[1]):
        tot = sum(1 for e in data if e.get("categoria") == k)
        print(f"  {k}: {v}/{tot}")
