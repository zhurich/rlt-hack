"""Сборка полного ответа: подбор + карточки компаний + статусы + объяснения.

Единая точка входа для API и скриптов. Внешних запросов нет — только индексы и DuckDB.
"""
from pathlib import Path

import duckdb
import numpy as np

from .codefix import CodeFixer
from .explain import NEW_FACTOR_LABELS, explain_known, explain_new, factors
from .pool import POOL, Pool
from .recommender import Query, Recommender

DB = Path(__file__).resolve().parent.parent / "data" / "rlt.duckdb"

CARD_COLUMNS = (
    "inn", "kind", "name", "region", "place", "in_history", "bids", "wins", "last_bid",
    "status", "status_reason", "role", "role_reason", "role_source",
    "okved_main", "okved_main_name", "msp_category", "msp_since", "headcount",
    "revenue", "tax_debt", "rnp_records", "licenses", "sources",
)


class Service:
    def __init__(self):
        self.rec = Recommender()
        self.pool = Pool() if POOL.exists() else None
        self.con = duckdb.connect(str(DB), read_only=True)
        # Наборы организаторов (scripts/add_procedures.py): участники неизвестны, часть кодов исправлена.
        self.has_sets = bool(self._rows("select 1 from duckdb_tables() where table_name = 'code_fixes'", []))
        test = [r["lot_id"] for r in self._rows("select distinct lot_id from test_lots", [])] if self.has_sets else []
        pos = np.searchsorted(self.rec.lot_id, test)
        pos = pos[pos < len(self.rec.lot_id)]
        self.fixer = CodeFixer(self.rec, exclude_lots=pos[np.isin(self.rec.lot_id[pos], test)])

    def _rows(self, sql: str, params: list) -> list[dict]:
        cur = self.con.cursor().execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def cards(self, inns: list[str]) -> dict[str, dict]:
        if not inns:
            return {}
        rows = self._rows(
            f"select {', '.join(CARD_COLUMNS)} from companies where inn in ({', '.join('?' * len(inns))})", inns)
        return {r["inn"]: r for r in rows}

    def lot(self, lot_id: int) -> dict | None:
        rows = self._rows("""
            select lot_id, publish_date, source, start_price as price, subject, is_smp, customer_inn
            from notices where lot_id = ?""", [lot_id])
        if not rows:
            return None
        lot = rows[0]
        lot["positions"] = self._rows("""
            select product_name as name, okpd2_code as code, count(*) as n
            from tru where lot_id = ? group by all order by n desc, name limit 15""", [lot_id])
        lot["participants"] = self._rows("""
            select supplier_inn as inn, bool_or(is_winner) as won
            from suppliers where lot_id = ? group by all""", [lot_id])
        lot["datasets"], lot["code_fixes"] = [], []
        if self.has_sets:
            lot["datasets"] = [r["dataset"] for r in self._rows(
                "select dataset from test_lots where lot_id = ? order by dataset", [lot_id])]
            lot["code_fixes"] = self._rows("""
                select original as "from", fixed as "to", how, positions
                from code_fixes where lot_id = ? order by positions desc, original""", [lot_id])
            was = {f["to"]: f["from"] for f in lot["code_fixes"]}
            for p in lot["positions"]:
                if p["code"] in was:
                    p["code_original"] = was[p["code"]]
        return lot

    def test_examples(self) -> list[dict]:
        """Все процедуры из наборов организаторов; лот из нескольких наборов — строка на каждый."""
        if not self.has_sets:
            return []
        return self._rows("""
            select n.lot_id, n.publish_date, n.source, n.start_price as price, n.subject,
                0 as participants, t.dataset
            from test_lots t join notices n using (lot_id) order by t.dataset, n.lot_id""", [])

    def search_lots(self, text: str, limit: int = 10) -> list[dict]:
        """Найти закупки в истории по тексту — чтобы выбрать лот для подбора."""
        vec = self.rec.vectorizer.transform([text])
        if not vec.nnz:
            return []
        sims = np.asarray((vec @ self.rec.xt).todense()).ravel()
        top = np.argsort(-sims)[:limit]
        ids = [int(self.rec.lot_id[i]) for i in top if sims[i] > 0]
        if not ids:
            return []
        rows = {r["lot_id"]: r for r in self._rows(f"""
            select n.lot_id, n.publish_date, n.source, n.start_price as price, n.subject,
                (select count(distinct supplier_inn) from suppliers s where s.lot_id = n.lot_id) as participants
            from notices n where n.lot_id in ({', '.join('?' * len(ids))})""", ids)}
        return [rows[i] for i in ids if i in rows]

    def examples(self, lot_ids: list[int] | None = None) -> list[dict]:
        """Готовые кейсы для показа: заданные лоты либо свежие лоты ЭМ из разных классов ОКПД2."""
        if lot_ids:
            rows = {r["lot_id"]: r for r in self._rows(f"""
                select n.lot_id, n.publish_date, n.source, n.start_price as price, n.subject,
                    (select count(distinct supplier_inn) from suppliers s where s.lot_id = n.lot_id) as participants
                from notices n where n.lot_id in ({', '.join('?' * len(lot_ids))})""", lot_ids)}
            found = [rows[i] for i in lot_ids if i in rows]
            if found:
                return found
        return self._rows("""
            with c as (
                select n.lot_id, n.publish_date, n.source, n.start_price as price, n.subject,
                    min(substr(t.okpd2_code, 1, 2)) as cls, count(distinct s.supplier_inn) as participants
                from notices n join tru t using (lot_id) join suppliers s using (lot_id)
                where n.publish_date >= date '2025-11-15' and n.source = 'ЭМ'
                    and n.start_price between 100000 and 3000000 and length(n.subject) between 25 and 110
                group by all
                having count(distinct substr(t.okpd2_code, 1, 2)) = 1 and count(distinct s.supplier_inn) between 3 and 6
            )
            select * exclude (cls) from c where cls in ('17', '21', '26', '32', '43', '81', '33', '10')
            qualify row_number() over (partition by cls order by publish_date desc, lot_id) = 1
            order by cls""", [])

    def stats(self) -> dict:
        row = self._rows("""
            select (select count(*) from notices) as lots,
                count(*) filter (in_history) as known, count(*) filter (not in_history) as new_total,
                count(*) filter (status = 'новый, подтверждён') as new_confirmed,
                count(*) filter (in_history and name is not null) as known_named
            from companies""", [])[0]
        row["pool"] = self.pool.n if self.pool else 0
        return row

    def by_lot(self, lot_id: int, top_n: int = 15, new_n: int = 10) -> dict | None:
        lot = self.lot(lot_id)
        if lot is None:
            return None
        q = self.rec.query_from_lot(lot_id)
        out = self._build(q, lot, top_n, new_n)
        # Где в выдаче оказались реальные участники (история — строго до даты лота).
        order = np.argsort(-out.pop("_score"))
        place = {int(i): r for r, i in enumerate(order, 1)}
        cards = self.cards([p["inn"] for p in lot["participants"]])
        for p in lot["participants"]:
            i = self.rec.sup_idx.get(p["inn"])
            p["name"] = (cards.get(p["inn"]) or {}).get("name")
            p["place"] = place[i] if i is not None and out["_positive"][i] else None
        lot["participants"].sort(key=lambda p: (p["place"] is None, p["place"] or 0))
        out.pop("_positive")
        return out

    def by_input(self, text: str, codes: list[str] | None = None, price: float | None = None,
                 customer_inn: str | None = None, source: str | None = None, is_smp: bool = False,
                 top_n: int = 15, new_n: int = 10) -> dict:
        is_ais = {"АИС ГЗ": True, "ЭМ": False}.get(source)
        # Код с испорченным классом (как в части файлов организаторов) восстанавливается по тексту.
        fixes = []
        for i, code in enumerate(codes or []):
            fix = self.fixer.fix(code.strip(), text, text)
            if fix.changed:
                fixes.append({"from": code.strip(), "to": fix.code, "how": fix.how, "positions": 1})
                codes[i] = fix.code
        q = self.rec.query_from_input(text, codes, price, customer_inn, is_ais, is_smp)
        lot = {"lot_id": None, "subject": text, "price": price, "source": source, "is_smp": is_smp,
               "customer_inn": customer_inn, "positions": [], "participants": [],
               "datasets": [], "code_fixes": fixes}
        out = self._build(q, lot, top_n, new_n)
        out.pop("_score")
        out.pop("_positive")
        return out

    def _build(self, q: Query, lot: dict, top_n: int, new_n: int) -> dict:
        s = self.rec.score(q)
        res = self.rec.recommend(q, top_n=top_n)
        items, codes = res["items"], res["codes"]
        new_items = self.pool.recommend(codes, q.vec, top_n=new_n) if self.pool else []

        cards = self.cards([it["inn"] for it in items + new_items])
        similar_ids = [sl["lot_id"] for it in items for sl in it["similar_lots"]]
        subjects = {}
        if similar_ids:
            subjects = {r["lot_id"]: r["subject"] for r in self._rows(
                f"select lot_id, subject from notices where lot_id in ({', '.join('?' * len(similar_ids))})",
                similar_ids)}

        for it in items:
            it["company"] = cards.get(it["inn"]) or {"inn": it["inn"]}
            it["reasons"] = explain_known(it, lot, subjects)
            it["factors"] = factors(it["parts"])
            for sl in it["similar_lots"]:
                sl["subject"] = subjects.get(sl["lot_id"])
        for it in new_items:
            it["company"] = cards.get(it["inn"]) or {"inn": it["inn"]}
            it["reasons"] = explain_new(it, it["company"], codes)
            it["factors"] = factors(it["parts"], NEW_FACTOR_LABELS)

        return {
            "lot": lot,
            "codes": [{"code": c, "share": round(w, 3)} for c, w in codes.items()],
            "codes_inferred": not q.codes and bool(codes),
            "items": items,
            "new_items": new_items,
            "_score": s.score,
            "_positive": s.score > 0,
        }
