"""Пакетный подбор для процедур без участников — всех наборов организаторов (таблица test_lots,
см. add_procedures.py).

    python scripts/predict.py [сколько_из_истории] [сколько_новых]    # по умолчанию 10 и 5

Пишет data/out/test_recommendations.csv в формате исходных файлов (UTF-8, `;`, строки в кавычках):
одна строка — один рекомендованный контрагент. `dataset` — набор, из которого процедура. `list` — «история» (участники прошлых закупок)
или «новые» (компании из реестров, которых в закупках ещё не было); место считается внутри списка.
"""
import csv
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from recsys.service import Service  # noqa: E402

OUT = ROOT / "data" / "out" / "test_recommendations.csv"
COLUMNS = ("dataset", "lot_id", "list", "rank", "supplier_inn", "supplier_name", "score", "role", "status",
           "status_reason", "reasons")

top_n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
new_n = int(sys.argv[2]) if len(sys.argv) > 2 else 5

svc = Service()
lots = svc._rows("""
    select lot_id, string_agg(dataset, ', ' order by dataset) as dataset
    from test_lots group by all order by min(dataset), lot_id""", [])

rows, short = [], []
t0 = time.time()
for lot in lots:
    lot_id = lot["lot_id"]
    res = svc.by_lot(lot_id, top_n=top_n, new_n=new_n)
    for name, items in (("история", res["items"]), ("новые", res["new_items"])):
        for rank, it in enumerate(items, 1):
            c = it["company"]
            rows.append((lot["dataset"], lot_id, name, rank, it["inn"], c.get("name") or "", f"{it['score']:.4f}",
                         c.get("role") or "", c.get("status") or "", c.get("status_reason") or "",
                         " | ".join(it["reasons"])))
    if len(res["items"]) < top_n:
        short.append((lot_id, len(res["items"])))
elapsed = time.time() - t0

OUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUT, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, delimiter=";", quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
    w.writerow(COLUMNS)
    w.writerows(rows)

print(f"лотов {len(lots)}, строк {len(rows)}, {elapsed / max(len(lots), 1) * 1000:.0f} мс на лот → {OUT}")
for lot_id, n in short:
    print(f"  лот {lot_id}: в основном списке только {n}")
