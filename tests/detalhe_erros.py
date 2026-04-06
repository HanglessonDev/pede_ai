"""Mostra os 9 erros restantes com mensagem e esperado vs obteve."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.extratores import extrair

with open("tests/dataset_extrator_deepseek.json", encoding="utf-8") as f:
    data = json.load(f)

erros = []
for i, ex in enumerate(data, 1):
    r = extrair(ex["mensagem"])
    if len(r) != len(ex["esperado"]):
        erros.append((i, ex, r, "count"))
        continue
    ok = True
    for a, b in zip(r, ex["esperado"]):
        if a.get("item_id") != b.get("item_id") or a.get("quantidade") != b.get("quantidade"):
            ok = False
            break
    if not ok:
        erros.append((i, ex, r, "mismatch"))

for idx, ex, r, reason in erros:
    esperado_ids = [(e.get("item_id"), e.get("quantidade")) for e in ex["esperado"]]
    obtido_ids = [(e.get("item_id"), e.get("quantidade")) for e in r]
    print(f"#{idx} [{ex.get('categoria','?')}] '{ex['mensagem']}'")
    print(f"   Esperado: {esperado_ids}")
    print(f"   Obteve:   {obtido_ids}")
    print()
