"""Подбор новых компаний (которых нет в истории закупок) под закупку.

Релевантность новой компании считается по её ОКВЭД:
  - связь «ОКВЭД → группа ОКПД2» выучена из истории: в каких группах ОКПД2 участвуют
    известные поставщики с таким же основным ОКВЭД;
  - прямое совпадение ОКВЭД (основного или дополнительного) с группой ОКПД2 закупки;
  - текстовая близость предмета закупки к названию ОКВЭД и заявленной продукции.
Итог умножается на достоверность (обороты, численность, стаж в реестре, долги).

    python -m recsys.pool            # собрать data/pool.pkl
"""
import pickle
from datetime import date
from pathlib import Path

import duckdb
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "rlt.duckdb"
INDEX = ROOT / "data" / "index.pkl"
POOL = ROOT / "data" / "pool.pkl"

WEIGHTS = {"affinity": 3.0, "affinity_class": 0.5, "okved_main": 1.0, "okved_extra": 0.3, "text": 2.0}
MIN_OKVED_BIDS = 30  # связь ОКВЭД → ОКПД2 учим только по ОКВЭД с достаточной историей
MIN_PAIR_BIDS = 3

TRUST_SQL = """
    least(1.0, greatest(0.05,
        0.3
        + 0.15 * (coalesce(revenue, 0) > 0 or coalesce(headcount, 0) > 0)::int
        + 0.15 * least(1.0, log10(greatest(coalesce(revenue, 0), 1)) / 9)  -- масштаб: до 1 млрд выручки
        + 0.2 * (msp_since < date '2024-10-01')::int
        + 0.1 * (coalesce(msp_category, 1) >= 2)::int
        + 0.1 * (len(licenses) > 0)::int
        - 0.3 * (coalesce(tax_debt, 0) > 100000)::int
    ))
"""


def build(con: duckdb.DuckDBPyConnection, vectorizer, where: str, cutoff: date | None = None) -> dict:
    """Собрать пул из companies по условию where; связь ОКВЭД→ОКПД2 — по истории до cutoff."""
    rows = con.execute(f"""
        select inn, left(okved_main, 5) as okved, {TRUST_SQL} as trust,
            list_distinct(list_transform(okved_extra, x -> left(x, 5))) as extra,
            okved_main_name || ' ' || okved_main_name || ' '
                || array_to_string(list_transform(products, x -> x.name), ' ') || ' '
                || array_to_string(licenses, ' ') as doc
        from companies where okved_main is not null and ({where}) order by inn
    """).fetchall()
    okveds = sorted({r[1] for r in rows})
    okved_id = {o: i for i, o in enumerate(okveds)}

    date_filter = f"and n.publish_date <= date '{cutoff}'" if cutoff else ""
    pairs = con.execute(f"""
        with bids as (
            select distinct s.supplier_inn as inn, s.lot_id, left(c.okved_main, 5) as okved
            from suppliers s join notices n using (lot_id) join companies c on c.inn = s.supplier_inn
            where c.okved_main is not null {date_filter}
        ), total as (
            select okved, count(*) as n from bids group by all having count(*) >= {MIN_OKVED_BIDS}
        ), lot_groups as (
            select distinct lot_id, left(okpd2_code, 5) as g, left(okpd2_code, 2) as cls
            from tru where length(okpd2_code) >= 2
        ), by_group as (
            select b.okved, lg.g as key, count(distinct (b.inn, b.lot_id)) as n
            from bids b join lot_groups lg using (lot_id) where length(lg.g) = 5 group by all
        ), by_class as (
            select b.okved, lg.cls as key, count(distinct (b.inn, b.lot_id)) as n
            from bids b join lot_groups lg using (lot_id) group by all
        )
        select p.okved, p.key, p.n / t.n as share
        from (select * from by_group union all select * from by_class) p join total t using (okved)
        where p.n >= {MIN_PAIR_BIDS}
    """).fetchall()
    affinity: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    grouped: dict[str, list[tuple[int, float]]] = {}
    for okved, key, share in pairs:
        if okved in okved_id:
            grouped.setdefault(key, []).append((okved_id[okved], share))
    for key, items in grouped.items():
        affinity[key] = (np.array([i for i, _ in items]), np.array([s for _, s in items]))

    extra: dict[str, list[int]] = {}
    for i, r in enumerate(rows):
        for code in r[3]:
            extra.setdefault(code, []).append(i)

    x = vectorizer.transform([r[4] for r in rows])
    return {
        "inn": [r[0] for r in rows],
        "okved": np.array([okved_id[r[1]] for r in rows], dtype=np.int32),
        "okveds": okveds,
        "trust": np.array([r[2] for r in rows], dtype=np.float32),
        "affinity": affinity,
        "extra": {k: np.array(v, dtype=np.int32) for k, v in extra.items()},
        "xt": x.T.tocsr(),
    }


class Pool:
    def __init__(self, data: dict | Path = POOL):
        if not isinstance(data, dict):
            with open(data, "rb") as f:
                data = pickle.load(f)
        self.__dict__.update(data)
        self.okved_id = {o: i for i, o in enumerate(self.okveds)}
        self.n = len(self.inn)

    def score(self, codes: dict[str, float], vec) -> tuple[np.ndarray, dict[str, np.ndarray]]:
        by_okved = {k: np.zeros(len(self.okveds)) for k in ("affinity", "affinity_class", "okved_main")}
        extra = np.zeros(self.n)
        groups: dict[str, float] = {}
        classes: dict[str, float] = {}
        for code, w in codes.items():
            classes[code[:2]] = classes.get(code[:2], 0.0) + w
            if len(code) >= 5:
                groups[code[:5]] = groups.get(code[:5], 0.0) + w
        for key, w in groups.items():
            if key in self.affinity:
                ids, share = self.affinity[key]
                by_okved["affinity"][ids] += w * share
            if key in self.okved_id:
                by_okved["okved_main"][self.okved_id[key]] += w
            if key in self.extra:
                extra[self.extra[key]] += w
        for key, w in classes.items():
            if key in self.affinity:
                ids, share = self.affinity[key]
                by_okved["affinity_class"][ids] += w * share

        raw = {k: v[self.okved] for k, v in by_okved.items()}
        raw["okved_extra"] = extra
        raw["text"] = (np.asarray((vec @ self.xt).todense()).ravel()
                       if vec is not None and vec.nnz else np.zeros(self.n))
        parts = {k: WEIGHTS[k] * raw[k] * (0.5 + self.trust) for k in WEIGHTS}
        return sum(parts.values()), parts

    def recommend(self, codes: dict[str, float], vec, top_n: int = 20) -> list[dict]:
        score, parts = self.score(codes, vec)
        k = min(top_n, int((score > 0).sum()))
        top = np.argsort(-score)[:k]
        return [{
            "inn": self.inn[i],
            "score": round(float(score[i]), 4),
            "trust": round(float(self.trust[i]), 2),
            "parts": {k: round(float(v[i]), 4) for k, v in parts.items() if v[i] > 0},
            # Значения факторов без весов и достоверности: доля заявок, совпадение, близость текста.
            "raw": {k: round(float(v[i] / (WEIGHTS[k] * (0.5 + self.trust[i]))), 4)
                    for k, v in parts.items() if v[i] > 0},
        } for i in top]


def main() -> None:
    con = duckdb.connect(str(DB), read_only=True)
    with open(INDEX, "rb") as f:
        vectorizer = pickle.load(f)["vectorizer"]
    data = build(con, vectorizer, "not in_history and rnp_records = 0")
    with open(POOL, "wb") as f:
        pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"новых компаний в пуле: {len(data['inn']):,}, ОКВЭД: {len(data['okveds']):,}, "
          f"связей ОКВЭД→ОКПД2: {sum(len(v[0]) for v in data['affinity'].values()):,}, "
          f"{POOL.stat().st_size / 2**20:.0f} МБ")


if __name__ == "__main__":
    main()
