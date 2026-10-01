"""Проверка подбора новых компаний на истории.

Новых компаний в истории по определению нет, поэтому проверяем сам способ: ранжируем
известных поставщиков только по сведениям из реестров (ОКВЭД, достоверность), как будто
их истории закупок нет, и смотрим, находит ли он реальных участников отложенных лотов.
Связь ОКВЭД→ОКПД2 учится только на истории до отсечки.

    python scripts/validate_pool.py [число_лотов]
"""
import pickle
import sys
from datetime import date
from pathlib import Path

import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from recsys.pool import WEIGHTS, Pool, build  # noqa: E402
from recsys.recommender import Recommender  # noqa: E402

n_sample = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
cutoff = date(2025, 10, 31)

rec = Recommender(stats_cutoff=cutoff)
con = duckdb.connect(str(ROOT / "data" / "rlt.duckdb"), read_only=True)
pool = Pool(build(con, rec.vectorizer, "in_history", cutoff))
pos = {inn: i for i, inn in enumerate(pool.inn)}
print(f"известных поставщиков с ОКВЭД: {pool.n:,}")

cut_day = rec.to_day(cutoff)
test = np.flatnonzero((rec.lot_day > cut_day) & (np.diff(rec.lot_ptr) > 0))
test = np.random.default_rng(0).choice(test, size=min(n_sample, len(test)), replace=False)

KS = (10, 50, 200)
VARIANTS = {
    "принятые веса": WEIGHTS,
    "только связь ОКВЭД→ОКПД2 (группа)": {"affinity": 1},
    "только связь ОКВЭД→ОКПД2 (класс)": {"affinity_class": 1},
    "только совпадение основного ОКВЭД": {"okved_main": 1},
    "только текст": {"text": 1},
    "связь + текст 1:1": {"affinity": 1, "text": 1},
    "связь + текст 1:3": {"affinity": 1, "text": 3},
    "связь + текст 3:1": {"affinity": 3, "text": 1},
    "всё, текст x3": {**WEIGHTS, "text": 6.0},
}
hits = {name: {k: [] for k in KS} for name in VARIANTS}
for lot in test:
    sup = rec.bid_sup[rec.lot_ptr[lot]:rec.lot_ptr[lot + 1]]
    truth = [pos[rec.sup_inn[s]] for s in sup if rec.sup_inn[s] in pos]
    if not truth:
        continue
    q = rec.query_from_lot(int(rec.lot_id[lot]))
    _, parts = pool.score(q.codes, q.vec)
    for name, w in VARIANTS.items():
        score = sum(w[k] / WEIGHTS[k] * parts[k] for k in w)
        order = np.argsort(-score)[:max(KS)]
        order = order[score[order] > 0]
        for k in KS:
            hits[name][k].append(np.isin(truth, order[:k]).mean())

print(f"лотов: {len(hits['принятые веса'][10])}")
print(f"{'вариант':<36}" + "".join(f"{f'Recall@{k}':>12}" for k in KS))
print(f"{'случайный выбор':<36}" + "".join(f"{k / pool.n:>12.4f}" for k in KS))
for name in VARIANTS:
    print(f"{name:<36}" + "".join(f"{np.mean(hits[name][k]):>12.3f}" for k in KS))
