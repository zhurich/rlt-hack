"""Быстрая оценка подбора на отложенном периоде.

История — по дату отсечки включительно, проверка — на случайных лотах после неё.
Участники-физлица (преподаватели) из истины исключены: их система не рекомендует.

    python scripts/evaluate.py [число_лотов] [дата_отсечки]
"""
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from recsys.recommender import Recommender  # noqa: E402

n_sample = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
cutoff = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else date(2025, 10, 31)
K = 10

rec = Recommender()
cut_day = rec.to_day(cutoff)

has_bids = np.diff(rec.lot_ptr) > 0
test = np.flatnonzero((rec.lot_day > cut_day) & has_bids)
rng = np.random.default_rng(0)
test = rng.choice(test, size=min(n_sample, len(test)), replace=False)

rows = []  # (is_ais, recall@K, победитель в топ-K, AP@K)
t0 = time.time()
for lot in test:
    a, b = rec.lot_ptr[lot], rec.lot_ptr[lot + 1]
    sup, win = rec.bid_sup[a:b], rec.bid_win[a:b]
    keep = ~rec.sup_person[sup]
    sup, win = sup[keep], win[keep]
    if not len(sup):
        continue
    s = rec.score(rec.query_from_lot(int(rec.lot_id[lot])), as_of_day=cut_day + 1)
    top = np.argsort(-s.score)[:K]
    top = top[s.score[top] > 0]
    hit = np.isin(top, sup)
    ap = (np.cumsum(hit) / np.arange(1, len(top) + 1) * hit).sum() / min(len(sup), K) if len(top) else 0.0
    winner_hit = np.isin(sup[win], top).any() if win.any() else np.nan
    rows.append((rec.lot_ais[lot], hit.sum() / len(sup), winner_hit, ap))
elapsed = time.time() - t0

rows = np.array(rows, dtype=float)
print(f"отсечка {cutoff}, лотов {len(rows)}, {elapsed / len(rows) * 1000:.0f} мс на лот\n")
print(f"{'срез':<10} {'лотов':>6} {f'Recall@{K}':>10} {f'Победитель@{K}':>15} {f'MAP@{K}':>8}")
for name, mask in (("все", rows[:, 0] >= 0), ("ЭМ", rows[:, 0] == 0), ("АИС ГЗ", rows[:, 0] == 1)):
    r = rows[mask]
    print(f"{name:<10} {len(r):>6} {r[:, 1].mean():>10.3f} {np.nanmean(r[:, 2]):>15.3f} {r[:, 3].mean():>8.3f}")
