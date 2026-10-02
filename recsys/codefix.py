"""Восстановление испорченного класса ОКПД2 в позициях закупки.

В части входных файлов первые две цифры кода заменены (например, все коды начинаются с «02»:
катетеры — 02.50.13.110 вместо 32.50.13.110). Остаток кода цел, поэтому класс восстанавливается:
кандидаты — классы, с которыми такой же остаток кода встречается в истории, выбор между ними —
голосованием закупок с похожим текстом позиции. Код, известный по истории, не трогается; редкий
настоящий код тоже: его класс поддержан похожими закупками.
"""
from dataclasses import dataclass

import numpy as np
from scipy import sparse

from .recommender import Recommender

TOP_LOTS = 200  # сколько похожих закупок голосует
MIN_SIM = 0.1
LOT_WEIGHT = 0.5  # вес близости по тексту всей закупки рядом с близостью по названию позиции
KEEP_SHARE = 0.1  # класс считается настоящим, если набрал такую долю голосов лучшего класса
DEPTHS = (12, 8, 5)  # уровни кода: полный, категория, группа


@dataclass
class Fix:
    code: str  # итоговый код
    changed: bool
    how: str  # чем обоснован выбор — для показа и для отчёта


class CodeFixer:
    def __init__(self, rec: Recommender, exclude_lots: np.ndarray | None = None):
        self.rec = rec
        n_lots, n_codes = len(rec.lot_id), len(rec.code_list)
        lot_of = np.repeat(np.arange(n_lots), np.diff(rec.lot_code_ptr))
        keep = np.ones(len(lot_of), dtype=bool)
        if exclude_lots is not None and len(exclude_lots):  # лоты, чьи коды сами под вопросом
            keep = ~np.isin(lot_of, exclude_lots)
        lot_of, code_of = lot_of[keep], rec.lot_code_id[keep]
        self.lot_codes = sparse.csr_matrix(
            (np.ones(len(lot_of), dtype=np.float32), (lot_of, code_of)), shape=(n_lots, n_codes))
        self.freq = np.asarray(self.lot_codes.sum(axis=0)).ravel()  # в скольких лотах встречается код
        self.known = {c for c, n in zip(rec.code_list, self.freq) if n > 0}
        self.classes = sorted({c[:2] for c in self.known})
        # префикс кода -> номера кодов с таким префиксом
        self.by_prefix: dict[str, list[int]] = {}
        for i, c in enumerate(rec.code_list):
            if self.freq[i] > 0:
                for depth in (2, *DEPTHS):
                    if len(c) >= depth:
                        self.by_prefix.setdefault(c[:depth], []).append(i)

    def _votes(self, name: str, lot_text: str, skip_lot: int | None) -> np.ndarray:
        """Голоса кодов: сумма близости похожих закупок, в которых код встречается."""
        vec = self.rec.vectorizer.transform([name, lot_text])
        sims = np.asarray((vec @ self.rec.xt).todense())
        sims = sims[0] + LOT_WEIGHT * sims[1]
        if skip_lot is not None:
            sims[skip_lot] = 0
        top = np.argpartition(sims, -TOP_LOTS)[-TOP_LOTS:]
        top = top[sims[top] >= MIN_SIM]
        return sims[top] @ self.lot_codes[top] if len(top) else np.zeros(len(self.freq))

    def _sum(self, votes: np.ndarray, prefix: str) -> float:
        ids = self.by_prefix.get(prefix)
        return float(votes[ids].sum()) if ids else 0.0

    def fix(self, code: str, name: str, lot_text: str = "", skip_lot: int | None = None,
            suspect: bool = False) -> Fix:
        """suspect — класс заведомо под подозрением (см. suspect_classes): настоящим его не считать."""
        if not code or len(code) < 5 or (code in self.known and not suspect):
            return Fix(code, False, "код известен по истории")
        if not suspect and code[:8] in self.by_prefix:
            return Fix(code, False, "категория кода известна по истории")
        votes = self._votes(name or "", lot_text or name or "", skip_lot)
        by_class = {c: self._sum(votes, c) for c in self.classes}
        best = max(by_class.values(), default=0.0)
        if not suspect and best > 0 and by_class.get(code[:2], 0.0) >= KEEP_SHARE * best:
            return Fix(code, False, "класс подтверждён похожими закупками")

        rest = code[2:]
        classes = [c for c in self.classes if c != code[:2]]
        exact = [c for c in classes if c + rest in self.known]
        if exact:
            # Остаток кода встречается в истории целиком: выбираем класс по похожим закупкам —
            # сначала по самому коду, затем по классу, иначе берём самый частый код.
            for how, score in (("тот же код", lambda c: self._sum(votes, c + rest)),
                               ("тот же класс", lambda c: by_class[c])):
                top = max(exact, key=score)
                if score(top) > 0:
                    return Fix(top + rest, True, f"похожие закупки: {how} {top + rest if how == 'тот же код' else top}")
            top = max(exact, key=lambda c: self._code_freq(c + rest))
            return Fix(top + rest, True, "самый частый в истории код с таким же окончанием")
        for depth, level in ((8, "та же категория"), (5, "та же группа")):
            if len(code) < depth:
                continue
            scored = [(self._sum(votes, c + rest[:depth - 2]), c) for c in classes]
            scored = [x for x in scored if x[0] > 0]
            if scored:
                cls = max(scored)[1]
                return Fix(cls + rest, True, f"похожие закупки: {level} {cls + rest[:depth - 2]}")
        return Fix(code, False, "не удалось восстановить")

    def _code_freq(self, code: str) -> float:
        return float(sum(self.freq[i] for i in self.by_prefix.get(code, []) if self.rec.code_list[i] == code))

    def suspect_classes(self, codes: list[str], min_codes: int = 5, share: float = 0.5) -> set[str]:
        """Классы, испорченные в целом файле: большинства их кодов в истории нет."""
        by_class: dict[str, set[str]] = {}
        for c in set(codes):
            if c and len(c) >= 5:
                by_class.setdefault(c[:2], set()).add(c)
        return {cls for cls, cs in by_class.items()
                if len(cs) >= min_codes and sum(c not in self.known for c in cs) > share * len(cs)}
