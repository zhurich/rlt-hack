"""Проверка подбора руками — тот же ответ, что отдаёт API, в текстовом виде.

    python scripts/try_lot.py 5369122                 # по lot_id; видно, где оказались реальные участники
    python scripts/try_lot.py "поставка бумаги А4"    # новая закупка по тексту
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from recsys.service import Service  # noqa: E402

arg = " ".join(sys.argv[1:])
t0 = time.time()
svc = Service()
print(f"сервис загружен за {time.time() - t0:.1f} с")

t0 = time.time()
res = svc.by_lot(int(arg)) if arg.isdigit() else svc.by_input(arg)
ms = (time.time() - t0) * 1000
if res is None:
    sys.exit(f"лот {arg} не найден")

lot = res["lot"]
if lot["lot_id"]:
    print(f"\nЛот {lot['lot_id']}: {lot['publish_date']}, {lot['source']}, цена {lot['price']:,.0f}, "
          f"заказчик {lot['customer_inn']}, СМП {lot['is_smp']}")
print(f"  {lot['subject']}")
inferred = " (выведены из похожих закупок)" if res["codes_inferred"] else ""
print(f"\nКоды ОКПД2{inferred}: " + (", ".join(f"{c['code']} ({c['share']:.0%})" for c in res["codes"]) or "нет"))
print(f"Ответ за {ms:.0f} мс")
actual = {p["inn"]: p["won"] for p in lot["participants"]}


def show(items: list[dict]) -> None:
    for rank, it in enumerate(items, 1):
        c = it["company"]
        mark = {True: "  <- ПОБЕДИТЕЛЬ", False: "  <- участник"}.get(actual.get(it["inn"]), "")
        print(f"\n{rank:>2}. {c.get('name') or '—'} (ИНН {it['inn']}), балл {it['score']:.2f}{mark}")
        print(f"    Роль: {c.get('role', '—')} — {c.get('role_reason', '—')}")
        print(f"    Статус: {c.get('status', '—')} — {c.get('status_reason', '—')}")
        for reason in it["reasons"]:
            print(f"    • {reason}")
        f = it["factors"]
        print("    Релевантность: " + ", ".join(f"{x['label']} {x['share']}%" for x in f["relevance"]))
        if f["boosts"]:
            print("    Надбавки: " + ", ".join(f"{x['label']} +{x['pct']}%" for x in f["boosts"]))


print("\n=== Рекомендуемые поставщики ===")
show(res["items"][:7])
print("\n=== Новые компании из реестров (нет в истории закупок) ===")
show(res["new_items"][:5])

if lot["participants"]:
    print("\n=== Реальные участники и их место в выдаче ===")
    for p in lot["participants"]:
        print(f"  {p['inn']:<12} {'победитель' if p['won'] else 'участник  '}  "
              f"место: {p['place'] or 'не найден'}  {p['name'] or ''}")
