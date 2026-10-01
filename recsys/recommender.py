"""Базовый подбор поставщиков под закупку.

Все признаки — плотные векторы по поставщикам, считаются при запросе из постингов
с отсечкой по дате: в историю попадают только лоты, опубликованные раньше `day`.
"""
import pickle
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np

INDEX = Path(__file__).resolve().parent.parent / "data" / "index.pkl"

LEVEL_NAMES = {2: "okpd2", 5: "okpd4", 8: "okpd6", 12: "okpd9"}

# Веса релевантности (перед log1p от взвешенного числа заявок) ...
# Подобраны scripts/tune.py (см. docs/metrics.md). Верхние уровни ОКПД2 поверх текста метрику
# не меняют; малые веса оставлены, чтобы закупка без текстовых совпадений не оставалась пустой.
REL_WEIGHTS = {"okpd9": 0.3, "okpd6": 0.1, "okpd4": 0.05, "okpd2": 0.02, "text": 5.0, "customer": 0.75}
# ... и множителей: итог = релевантность * (1 + сумма множителей).
MOD_WEIGHTS = {"price": 0.5, "region": 0.0, "spec": 0.75, "source": 2.0, "smp": 2.0}

HALF_LIFE = 365.0  # дней: заявка годовой давности весит вдвое меньше
WIN_BONUS = 1.5  # победа весит как 2.5 участия
TOP_LOTS = 300  # сколько похожих по тексту лотов учитывать
SIM_POWER = 4.0 # вес похожего лота = близость в этой степени
MIN_SIM = 0.2
MAX_CODES = 15  # кодов ОКПД2 из лота-запроса
PRICE_SIGMA_FLOOR = 0.7
LOCAL_REGIONS = {"78": 1.0, "47": 0.5}
PROFILE_CACHE = 32  # на сколько дней запроса хранить профили поставщиков


@dataclass
class Query:
    codes: dict[str, float]  # код ОКПД2 -> доля в лоте
    vec: object  # TF-IDF вектор 1×V или None
    day: int  # история берётся строго до этого дня
    logprice: float = float("nan")
    cust: int = -1
    is_ais: bool | None = None
    is_smp: bool = False
    lot_idx: int | None = None


@dataclass
class Features:
    rel: dict[str, np.ndarray]  # log1p от взвешенного числа заявок, по факторам релевантности
    mod: dict[str, np.ndarray]  # множители, каждый в [0, 1]
    facts: dict[str, np.ndarray]
    codes: dict[str, float]
    sim_bids: tuple[np.ndarray, np.ndarray] | None = None


@dataclass
class Scored:
    score: np.ndarray
    parts: dict[str, np.ndarray]  # вклад каждого фактора, в сумме даёт score
    facts: dict[str, np.ndarray]  # сырые числа для объяснений
    mods: dict[str, np.ndarray]  # значения множителей в [0, 1]
    codes: dict[str, float]
    sim_bids: tuple[np.ndarray, np.ndarray] | None = None  # заявки в похожих лотах и их близость


@dataclass
class Profiles:
    """Общие профили поставщиков по заявкам в лотах, опубликованных раньше `day`."""
    day: int
    total: np.ndarray  # число заявок
    ais_share: np.ndarray  # доля заявок в АИС ГЗ
    smp: np.ndarray  # побеждал в закупках для СМП
    price_n: np.ndarray
    price_mean: np.ndarray  # по логарифму начальной цены
    price_std: np.ndarray


class Recommender:
    def __init__(self, path: Path = INDEX):
        with open(path, "rb") as f:
            self.__dict__.update(pickle.load(f))
        self.epoch = date.fromisoformat(self.epoch)
        self.n_sup = len(self.sup_inn)
        self.sup_idx = {inn: i for i, inn in enumerate(self.sup_inn)}
        self.cust_idx = {inn: i for i, inn in enumerate(self.cust_inn)}
        self.sup_local = np.array([LOCAL_REGIONS.get(r, 0.0) for r in self.sup_region])
        self.max_day = int(self.lot_day.max())
        self.rel_w = dict(REL_WEIGHTS)
        self.mod_w = dict(MOD_WEIGHTS)
        self.half_life = HALF_LIFE
        self.win_bonus = WIN_BONUS
        self.top_lots = TOP_LOTS
        self.sim_power = SIM_POWER
        self.bid_day = self.lot_day[self.bid_lot]
        self._profiles: dict[int, Profiles] = {}

    def to_day(self, d: date) -> int:
        return (d - self.epoch).days

    def to_date(self, day: int) -> date:
        return self.epoch + timedelta(days=int(day))

    def profiles(self, day: int) -> Profiles:
        """Профили на день запроса — как и остальные признаки, только по истории строго до него.

        Расчёт (~60 мс) запоминается по дню: метрика и повторные запросы спрашивают одни и те же дни.
        """
        p = self._profiles.get(day)
        if p is not None:
            return p
        keep = self.bid_day < day
        lot, sup, win = self.bid_lot[keep], self.bid_sup[keep], self.bid_win[keep]
        n = self.n_sup
        total = np.bincount(sup, minlength=n).astype(float)
        lp = self.lot_logprice[lot].astype(float)
        ok = ~np.isnan(lp)
        cnt = np.bincount(sup[ok], minlength=n)
        mean = np.bincount(sup[ok], weights=lp[ok], minlength=n) / np.maximum(cnt, 1)
        var = np.bincount(sup[ok], weights=lp[ok] ** 2, minlength=n) / np.maximum(cnt, 1) - mean**2
        p = Profiles(
            day=day, total=total,
            ais_share=np.bincount(sup, weights=self.lot_ais[lot], minlength=n) / np.maximum(total, 1),
            smp=np.bincount(sup, weights=self.lot_smp[lot] & win, minlength=n) > 0,
            price_n=cnt, price_mean=mean,
            price_std=np.maximum(np.sqrt(np.maximum(var, 0)), PRICE_SIGMA_FLOOR),
        )
        if len(self._profiles) >= PROFILE_CACHE:
            self._profiles.pop(next(iter(self._profiles)), None)
        self._profiles[day] = p
        return p

    # ---------- построение запроса ----------

    def query_from_lot(self, lot_id: int) -> Query:
        i = int(np.searchsorted(self.lot_id, lot_id))
        if i >= len(self.lot_id) or self.lot_id[i] != lot_id:
            raise KeyError(f"лот {lot_id} не найден")
        a, b = self.lot_code_ptr[i], self.lot_code_ptr[i + 1]
        ids, cnt = self.lot_code_id[a:b][:MAX_CODES], self.lot_code_n[a:b][:MAX_CODES].astype(float)
        codes = {self.code_list[c]: w for c, w in zip(ids, cnt / cnt.sum())} if len(ids) else {}
        return Query(
            codes=codes, vec=self.x[i], day=int(self.lot_day[i]), logprice=float(self.lot_logprice[i]),
            cust=int(self.lot_cust[i]), is_ais=bool(self.lot_ais[i]), is_smp=bool(self.lot_smp[i]), lot_idx=i,
        )

    def query_from_input(
        self, text: str, codes: list[str] | None = None, price: float | None = None,
        customer_inn: str | None = None, is_ais: bool | None = None, is_smp: bool = False,
    ) -> Query:
        codes = [c.strip() for c in codes or [] if c.strip()]
        return Query(
            codes={c: 1 / len(codes) for c in codes},
            vec=self.vectorizer.transform([text]) if text.strip() else None,
            day=self.max_day + 1,
            logprice=float(np.log(price)) if price and price > 0 else float("nan"),
            cust=self.cust_idx.get(customer_inn, -1), is_ais=is_ais, is_smp=is_smp,
        )

    # ---------- признаки ----------

    def _weights(self, bid_idx: np.ndarray, day: int) -> np.ndarray:
        """Вес заявки: затухание по давности, надбавка за победу; будущее обнуляется."""
        age = day - self.lot_day[self.bid_lot[bid_idx]]
        decay = np.where(age > 0, 0.5 ** (age / self.half_life), 0.0)
        return decay * (1 + self.win_bonus * self.bid_win[bid_idx])

    def _lot_bids(self, lots: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Заявки по списку лотов и для каждой — позиция её лота в списке."""
        start = self.lot_ptr[lots]
        cnt = self.lot_ptr[lots + 1] - start
        rep = np.repeat(np.arange(len(lots)), cnt)
        offs = np.arange(cnt.sum()) - np.repeat(np.cumsum(cnt) - cnt, cnt)
        return (start[rep] + offs).astype(np.int64), rep

    def _infer_codes(self, lots: np.ndarray, sims: np.ndarray, top: int = 50, keep: int = 5) -> dict[str, float]:
        """Коды ОКПД2 для закупки без кодов — голосованием самых похожих лотов."""
        order = np.argsort(-sims)[:top]
        votes: dict[int, float] = {}
        for lot, sim in zip(lots[order], sims[order]):
            a, b = self.lot_code_ptr[lot], self.lot_code_ptr[lot + 1]
            for c in self.lot_code_id[a:b][:3]:
                votes[c] = votes.get(c, 0.0) + float(sim)
        best = sorted(votes.items(), key=lambda kv: -kv[1])[:keep]
        total = sum(v for _, v in best)
        return {self.code_list[c]: v / total for c, v in best if v / total >= 0.1}

    def features(self, q: Query, as_of_day: int | None = None) -> Features:
        day = q.day if as_of_day is None else as_of_day
        n = self.n_sup
        raw: dict[str, np.ndarray] = {}
        facts: dict[str, np.ndarray] = {}
        codes, sim_bids = q.codes, None

        raw["text"] = np.zeros(n)
        if q.vec is not None and q.vec.nnz:
            sims = np.asarray((q.vec @ self.xt).todense()).ravel()
            sims[self.lot_day >= day] = 0
            top = np.argpartition(sims, -self.top_lots)[-self.top_lots:]
            top = top[sims[top] >= MIN_SIM]
            if not codes and len(top):
                codes = self._infer_codes(top, sims[top])
            bid_idx, rep = self._lot_bids(top)
            sim = sims[top][rep]
            raw["text"] = np.bincount(
                self.bid_sup[bid_idx], weights=sim**self.sim_power * self._weights(bid_idx, day), minlength=n)
            facts["text_lots"] = np.bincount(self.bid_sup[bid_idx], minlength=n)
            sim_bids = (bid_idx, sim)

        for level in self.levels:
            name = LEVEL_NAMES[level]
            prefixes: dict[str, float] = {}
            for code, w in codes.items():
                if len(code) >= level:
                    prefixes[code[:level]] = prefixes.get(code[:level], 0.0) + w
            acc, seen = np.zeros(n), []
            for prefix, w in prefixes.items():
                a, b = self.post.get(prefix, (0, 0))
                bid_idx = self.post_data[a:b]
                bw = self._weights(bid_idx, day)
                acc += w * np.bincount(self.bid_sup[bid_idx], weights=bw, minlength=n)
                seen.append(bid_idx[bw > 0])
            raw[name] = acc
            seen = np.unique(np.concatenate(seen)) if seen else np.empty(0, dtype=np.int64)
            facts[f"{name}_bids"] = np.bincount(self.bid_sup[seen], minlength=n)
            facts[f"{name}_wins"] = np.bincount(self.bid_sup[seen], weights=self.bid_win[seen], minlength=n)

        raw["customer"] = np.zeros(n)
        if q.cust >= 0:
            bid_idx = self.cust_data[self.cust_ptr[q.cust]:self.cust_ptr[q.cust + 1]]
            bw = self._weights(bid_idx, day)
            raw["customer"] = np.bincount(self.bid_sup[bid_idx], weights=bw, minlength=n)
            live = bid_idx[bw > 0]
            facts["customer_bids"] = np.bincount(self.bid_sup[live], minlength=n)
            facts["customer_wins"] = np.bincount(self.bid_sup[live], weights=self.bid_win[live], minlength=n)

        rel = {k: np.log1p(raw[k]) for k in REL_WEIGHTS}

        mod = {k: np.zeros(n) for k in MOD_WEIGHTS}
        mod["region"] = self.sup_local
        p = self.profiles(day)
        mod["spec"] = np.minimum(facts["okpd2_bids"] / np.maximum(p.total, 1), 1.0)
        if not np.isnan(q.logprice):
            z = (q.logprice - p.price_mean) / p.price_std
            mod["price"] = np.where(p.price_n > 0, np.exp(-0.5 * z**2), 0.0)
        if q.is_ais is not None:
            mod["source"] = p.ais_share if q.is_ais else 1 - p.ais_share
        if q.is_smp:
            mod["smp"] = p.smp.astype(float)
        return Features(rel=rel, mod=mod, facts=facts, codes=codes, sim_bids=sim_bids)

    def score(self, q: Query, as_of_day: int | None = None, include_persons: bool = False) -> Scored:
        f = self.features(q, as_of_day)
        parts = {k: w * f.rel[k] for k, w in self.rel_w.items()}
        rel = sum(parts.values())
        for k, w in self.mod_w.items():
            parts[k] = rel * w * f.mod[k]
        score = sum(parts.values())
        if not include_persons:
            score = np.where(self.sup_person, 0.0, score)
        return Scored(score=score, parts=parts, facts=f.facts, mods=f.mod, codes=f.codes, sim_bids=f.sim_bids)

    # ---------- выдача ----------

    def recommend(self, q: Query, top_n: int = 20, as_of_day: int | None = None,
                  include_persons: bool = False) -> dict:
        s = self.score(q, as_of_day, include_persons)
        p = self.profiles(q.day if as_of_day is None else as_of_day)
        k = min(top_n, int((s.score > 0).sum()))
        top = np.argsort(-s.score)[:k]
        items = []
        for i in top:
            similar = []
            if s.sim_bids is not None:
                bid_idx, sim = s.sim_bids
                mine = np.flatnonzero(self.bid_sup[bid_idx] == i)
                mine = mine[np.argsort(-sim[mine])][:3]
                similar = [
                    {"lot_id": int(self.lot_id[self.bid_lot[bid_idx[j]]]), "sim": round(float(sim[j]), 3),
                     "won": bool(self.bid_win[bid_idx[j]])}
                    for j in mine
                ]
            items.append({
                "inn": self.sup_inn[i],
                "score": round(float(s.score[i]), 4),
                "region": self.sup_region[i],
                "total_bids": int(p.total[i]),
                "parts": {k: round(float(v[i]), 4) for k, v in s.parts.items() if v[i] > 0},
                "facts": {k: int(v[i]) for k, v in s.facts.items() if v[i] > 0},
                "mods": {k: round(float(v[i]), 3) for k, v in s.mods.items() if v[i] > 0},
                "typical_price": float(np.exp(p.price_mean[i])) if p.price_n[i] > 0 else None,
                "similar_lots": similar,
            })
        return {"codes": s.codes, "items": items}
