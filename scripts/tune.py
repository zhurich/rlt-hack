"""Подбор весов и разбор вклада факторов.

Веса подбираются на одном периоде, проверяются на следующем:
  настройка: история по 2025-08-31, лоты сентября–октября 2025;
  проверка:  история по 2025-10-31, лоты ноября–декабря 2025.

Признаки считаются один раз и кэшируются (data/tune_cache.pkl), дальше перебираются только веса.

    python scripts/tune.py [--fresh] [--half-life N] [--win-bonus X]
"""
import argparse
import pickle
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from recsys.recommender import MOD_WEIGHTS, REL_WEIGHTS, Recommender  # noqa: E402

REL, MOD = list(REL_WEIGHTS), list(MOD_WEIGHTS)
K = 10
SPLITS = {
    "настройка": (date(2025, 8, 31), date(2025, 10, 31), 2000),
    "проверка": (date(2025, 10, 31), date(2025, 12, 31), 3000),
}
REL_GRID = [0, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1, 1.5, 2, 3, 5]
MOD_GRID = [0, 0.1, 0.2, 0.3, 0.5, 0.75, 1, 1.5, 2, 3, 5, 8]


def collect(rec: Recommender, cutoff: date, until: date, n_sample: int) -> list[dict]:
    """Признаки кандидатов по случайным лотам из (cutoff, until]; история — по cutoff."""
    cut_day, end_day = rec.to_day(cutoff), rec.to_day(until)
    rec._build_profiles(cut_day)
    lots = np.flatnonzero((rec.lot_day > cut_day) & (rec.lot_day <= end_day) & (np.diff(rec.lot_ptr) > 0))
    lots = np.random.default_rng(0).choice(lots, size=min(n_sample, len(lots)), replace=False)
    popular = np.argsort(-np.where(rec.sup_person, 0, rec.sup_total))[:K]
    w_rel = np.array([REL_WEIGHTS[k] for k in REL])
    w_mod = np.array([MOD_WEIGHTS[k] for k in MOD])

    data = []
    for lot in lots:
        a, b = rec.lot_ptr[lot], rec.lot_ptr[lot + 1]
        sup, win = rec.bid_sup[a:b], rec.bid_win[a:b]
        keep = ~rec.sup_person[sup]
        sup, win = sup[keep], win[keep]
        if not len(sup):
            continue
        f = rec.features(rec.query_from_lot(int(rec.lot_id[lot])), as_of_day=cut_day + 1)
        r = np.stack([f.rel[k] for k in REL])
        m = np.stack([f.mod[k] for k in MOD])
        r[:, rec.sup_person] = 0
        # Кандидаты: топ по исходным весам + топ по каждому фактору отдельно + истина.
        default = (w_rel @ r) * (1 + w_mod @ m)
        cand = [np.argsort(-default)[:500], sup]
        cand += [np.argsort(-row)[:200] for row in r]
        cand = np.unique(np.concatenate(cand))
        data.append({
            "rel": r[:, cand].T.astype(np.float32),
            "mod": m[:, cand].T.astype(np.float32),
            "truth": np.isin(cand, sup),
            "winner": np.isin(cand, sup[win]),
            "is_ais": bool(rec.lot_ais[lot]),
            "popular_recall": np.isin(sup, popular).mean(),
        })
    return data


def metrics(data: list[dict], w_rel: np.ndarray, w_mod: np.ndarray) -> np.ndarray:
    """Строка на лот: is_ais, Recall@K, победитель в топ-K, AP@K."""
    out = np.empty((len(data), 4))
    for i, d in enumerate(data):
        score = (d["rel"] @ w_rel) * (1 + d["mod"] @ w_mod)
        top = np.argsort(-score)[:K]
        hit = d["truth"][top] & (score[top] > 0)
        n_true = d["truth"].sum()
        ap = (np.cumsum(hit) / np.arange(1, len(top) + 1) * hit).sum() / min(n_true, K)
        win = (d["winner"][top] & (score[top] > 0)).any() if d["winner"].any() else np.nan
        out[i] = (d["is_ais"], hit.sum() / n_true, win, ap)
    return out


def objective(data, w_rel, w_mod) -> float:
    m = metrics(data, w_rel, w_mod)
    return m[:, 1].mean() + m[:, 3].mean()


def tune(data, w_rel: np.ndarray, w_mod: np.ndarray, passes: int = 3):
    """Покоординатный перебор по сетке."""
    w_rel, w_mod = w_rel.copy(), w_mod.copy()
    best = objective(data, w_rel, w_mod)
    for p in range(passes):
        changed = False
        for w, grid in ((w_rel, REL_GRID), (w_mod, MOD_GRID)):
            for j in range(len(w)):
                keep = w[j]
                for v in grid:
                    w[j] = v
                    cur = objective(data, w_rel, w_mod)
                    if cur > best + 1e-6:
                        best, keep, changed = cur, v, True
                w[j] = keep
        print(f"  проход {p + 1}: Recall@{K} + MAP@{K} = {best:.4f}")
        if not changed:
            break
    return w_rel, w_mod


def row(name: str, m: np.ndarray) -> str:
    em, ais = m[m[:, 0] == 0], m[m[:, 0] == 1]
    return (f"{name:<34} {m[:, 1].mean():>7.3f} {np.nanmean(m[:, 2]):>7.3f} {m[:, 3].mean():>7.3f}"
            f" {em[:, 1].mean():>9.3f} {ais[:, 1].mean():>9.3f}")


def report(title: str, data, variants: dict) -> None:
    print(f"\n{title} ({len(data)} лотов)")
    print(f"{'вариант':<34} {'R@10':>7} {'Win@10':>7} {'MAP@10':>7} {'R@10 ЭМ':>9} {'R@10 АИС':>9}")
    pop = np.array([d["popular_recall"] for d in data])
    ais = np.array([d["is_ais"] for d in data])
    print(f"{'самые активные в целом':<34} {pop.mean():>7.3f} {'':>7} {'':>7}"
          f" {pop[~ais].mean():>9.3f} {pop[ais].mean():>9.3f}")
    for name, (w_rel, w_mod) in variants.items():
        print(row(name, metrics(data, w_rel, w_mod)))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fresh", action="store_true", help="пересчитать признаки")
    ap.add_argument("--half-life", type=float)
    ap.add_argument("--win-bonus", type=float)
    ap.add_argument("--top-lots", type=int)
    ap.add_argument("--sim-power", type=float)
    args = ap.parse_args()

    tag = f"hl{args.half_life}_wb{args.win_bonus}_tl{args.top_lots}_sp{args.sim_power}"
    cache = ROOT / "data" / f"tune_cache_{tag}.pkl"
    if cache.exists() and not args.fresh:
        sets = pickle.loads(cache.read_bytes())
    else:
        rec = Recommender()
        for name in ("half_life", "win_bonus", "top_lots", "sim_power"):
            if getattr(args, name) is not None:
                setattr(rec, name, getattr(args, name))
        sets = {}
        for name, (cutoff, until, n) in SPLITS.items():
            t0 = time.time()
            sets[name] = collect(rec, cutoff, until, n)
            print(f"{name}: {len(sets[name])} лотов, {time.time() - t0:.0f} с")
        cache.write_bytes(pickle.dumps(sets))

    hand = (np.array([REL_WEIGHTS[k] for k in REL]), np.array([MOD_WEIGHTS[k] for k in MOD]))
    zero_mod = np.zeros(len(MOD))

    def only(*names: str):
        return np.array([1.0 if k in names else 0.0 for k in REL]), zero_mod

    print("\nПодбор весов на периоде настройки:")
    tuned = tune(sets["настройка"], *hand)
    print("  релевантность:", {k: float(v) for k, v in zip(REL, tuned[0])})
    print("  множители:    ", {k: float(v) for k, v in zip(MOD, tuned[1])})

    variants = {
        "только класс ОКПД2 (2 знака)": only("okpd2"),
        "только полный код ОКПД2": only("okpd9"),
        "только текст": only("text"),
        "только история с заказчиком": only("customer"),
        "ОКПД2 все уровни": (np.where([k.startswith("okpd") for k in REL], tuned[0], 0), zero_mod),
        "ОКПД2 + текст": (np.where([k != "customer" for k in REL], tuned[0], 0), zero_mod),
        "релевантность без множителей": (tuned[0], zero_mod),
        "веса руками (шаг 2)": hand,
        "подобранные веса": tuned,
    }
    for j, k in enumerate(REL):
        w = tuned[0].copy()
        w[j] = 0
        variants[f"  без {k}"] = (w, tuned[1])
    for j, k in enumerate(MOD):
        w = tuned[1].copy()
        w[j] = 0
        variants[f"  без {k}"] = (tuned[0], w)

    report("Период настройки", sets["настройка"], {k: variants[k] for k in ("веса руками (шаг 2)", "подобранные веса")})
    report("Период проверки", sets["проверка"], variants)


if __name__ == "__main__":
    main()
