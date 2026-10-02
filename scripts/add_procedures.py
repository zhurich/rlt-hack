"""Добавить в базу процедуры без участников — наборы организаторов (тестовый, предзащита).

    python scripts/add_procedures.py

Берёт из data/raw все пары файлов «…звещения….csv» / «…отоварка….csv» (формат — как у notices.csv
и tru.csv, имя набора — имя файла без этого слова). Лоты дописываются в notices и tru, номера —
в test_lots (lot_id, dataset). Запуск заменяет все прежние наборы; `scripts/load.py` их стирает.

Что чинится по дороге:
- битый заголовок (имена колонок слиты) — колонки читаются по порядку, заголовок только сверяется;
- испорченный класс ОКПД2 (в файле все коды начинаются, например, с «02») — восстанавливается
  по похожим закупкам, см. recsys/codefix.py; что на что заменено — в таблице code_fixes;
- лот в нескольких наборах — позиции берутся из того набора, где коды чинить не пришлось.

Нужен готовый data/index.pkl (по нему восстанавливаются коды). Сервер на время запуска остановить.
После запуска пересобрать индексы: python -m recsys.build, затем python -m recsys.pool
(словарь TF-IDF общий), и только потом — python scripts/predict.py.
"""
import re
import sys
from pathlib import Path

import duckdb
import numpy as np

from load import DB, NOTICE_COLUMNS, RAW, TRU_COLUMNS, notices_select, tru_select

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from recsys.codefix import CodeFixer  # noqa: E402
from recsys.recommender import Recommender  # noqa: E402

NOTICES_WORD = re.compile("извещени[яе]", re.IGNORECASE)


def datasets() -> list[tuple[str, Path, Path]]:
    """Пары файлов в порядке появления (по времени изменения): (имя набора, извещения, потоварка)."""
    found = []
    for notices in sorted(RAW.glob("*.csv"), key=lambda p: (p.stat().st_mtime, p.name)):
        if not NOTICES_WORD.search(notices.name):
            continue
        tru = [notices.with_name(NOTICES_WORD.sub(w, notices.name)) for w in ("потоварка", "Потоварка")]
        tru = [p for p in tru if p.exists()]
        if not tru:
            sys.exit(f"для {notices.name} нет файла с позициями («потоварка»)")
        name = " ".join(NOTICES_WORD.sub(" ", notices.stem).replace("_", " ").split())
        found.append((name, notices, tru[0]))
    if not found:
        sys.exit(f"в {RAW} нет файлов «…извещения….csv»")
    return found


def check_header(path: Path, columns: tuple[str, ...]) -> str | None:
    """Заголовок должен называть те же колонки в том же порядке; кавычки могут стоять как угодно."""
    with open(path, encoding="utf-8-sig") as f:
        line = f.readline().strip()
    if tuple(line.replace('"', "").split(";")) != columns:
        sys.exit(f"{path.name}: другой набор колонок: {line}")
    quoted = ";".join(f'"{c}"' for c in columns)
    return None if line in (quoted, ";".join(columns)) else line


def main() -> None:
    sets = datasets()
    rec = Recommender()
    con = duckdb.connect(str(DB))
    con.execute("create table if not exists test_lots (lot_id bigint)")
    old = np.array([r[0] for r in con.execute("select distinct lot_id from test_lots").fetchall()], dtype=np.int64)
    # Прежние тестовые лоты могут быть в индексе — их коды в восстановлении не участвуют.
    pos = np.searchsorted(rec.lot_id, old)
    pos = pos[pos < len(rec.lot_id)]
    pos = pos[np.isin(rec.lot_id[pos], old)]
    fixer = CodeFixer(rec, exclude_lots=pos)

    con.execute("begin")
    con.execute("delete from notices where lot_id in (select lot_id from test_lots)")
    con.execute("delete from tru where lot_id in (select lot_id from test_lots)")
    con.execute("create or replace table test_lots (lot_id bigint, dataset varchar)")
    con.execute("""create or replace table code_fixes
        (lot_id bigint, original varchar, fixed varchar, how varchar, positions integer)""")
    fixes_of: dict[int, int] = {}  # лот -> сколько позиций пришлось чинить в загруженной версии

    for name, notices_path, tru_path in sets:
        print(f"\n{name}")
        for path, columns in ((notices_path, NOTICE_COLUMNS), (tru_path, TRU_COLUMNS)):
            broken = check_header(path, columns)
            if broken:
                print(f"  {path.name}: битый заголовок, колонки взяты по порядку: {broken}")
        con.execute(f"create or replace temp table new_notices as {notices_select(notices_path)}")
        con.execute(f"create or replace temp table new_tru as {tru_select(tru_path)}")
        bad = con.execute("""
            select count(*) filter (lot_id is null), count(*) filter (publish_date is null),
                count(*) - count(distinct lot_id)
            from new_notices""").fetchone()
        if any(bad):
            con.execute("rollback")
            sys.exit(f"{notices_path.name}: без lot_id {bad[0]}, без даты {bad[1]}, дублей {bad[2]}")
        known = con.execute("""
            select count(*) from new_notices
            where lot_id in (select lot_id from notices) and lot_id not in (select lot_id from test_lots)
        """).fetchone()[0]
        if known:
            con.execute("rollback")
            sys.exit(f"{notices_path.name}: {known} лотов уже есть в истории — так добавлять нельзя")

        # Восстановление класса ОКПД2.
        rows = con.execute("""
            select t.lot_id, t.product_name, t.okpd2_code, n.subject, count(*)
            from new_tru t join new_notices n using (lot_id)
            where t.okpd2_code is not null group by all""").fetchall()
        suspect = fixer.suspect_classes([r[2] for r in rows])
        if suspect:
            print(f"  испорченные классы ОКПД2: {', '.join(sorted(suspect))} — восстанавливаются по похожим закупкам")
        fixed: dict[tuple, tuple[str, str, int]] = {}
        failed = 0
        for lot_id, product, code, subject, n in rows:
            fix = fixer.fix(code, product or "", f"{subject or ''} {product or ''}", suspect=code[:2] in suspect)
            if fix.changed:
                fixed[(lot_id, product, code)] = (fix.code, fix.how, n)
            elif code[:2] in suspect:
                failed += n
        per_lot: dict[int, int] = {}
        for (lot_id, _, _), (_, _, n) in fixed.items():
            per_lot[lot_id] = per_lot.get(lot_id, 0) + n
        if fixed or failed:
            print(f"  позиций с восстановленным кодом: {sum(per_lot.values())}, не удалось восстановить: {failed}")

        # Лот уже загружен из другого набора: позиции оставляем те, где чинить пришлось меньше.
        lots = [r[0] for r in con.execute("select lot_id from new_notices").fetchall()]
        seen = [lot for lot in lots if lot in fixes_of]
        replace = [lot for lot in lots if lot not in fixes_of or per_lot.get(lot, 0) < fixes_of[lot]]
        if seen:
            kept = len(seen) - len([lot for lot in seen if lot in replace])
            print(f"  лотов, уже загруженных из другого набора: {len(seen)}"
                  + (f" (у {kept} оставлены прежние позиции — там коды целые)" if kept else ""))
        con.execute("create or replace temp table take (lot_id bigint)")
        con.executemany("insert into take values (?)", [(lot,) for lot in replace])
        con.execute("delete from notices where lot_id in (select lot_id from take)")
        con.execute("delete from tru where lot_id in (select lot_id from take)")
        con.execute("delete from code_fixes where lot_id in (select lot_id from take)")
        con.execute("insert into notices select * from new_notices where lot_id in (select lot_id from take)")
        con.execute("create or replace temp table fix (lot_id bigint, product_name varchar, original varchar, "
                    "fixed varchar, how varchar, n integer)")
        if fixed:
            con.executemany("insert into fix values (?, ?, ?, ?, ?, ?)",
                            [(k[0], k[1], k[2], v[0], v[1], v[2]) for k, v in fixed.items()])
        con.execute("""
            insert into tru
            select t.lot_id, t.product_name, coalesce(f.fixed, t.okpd2_code)
            from new_tru t left join fix f
                on f.lot_id = t.lot_id and f.original = t.okpd2_code
                and f.product_name is not distinct from t.product_name
            where t.lot_id in (select lot_id from take)""")
        con.execute("""
            insert into code_fixes
            select lot_id, original, fixed, min(how), sum(n) from fix
            where lot_id in (select lot_id from take) group by all""")
        con.execute("insert into test_lots select lot_id, ? from new_notices", [name])
        for lot in replace:
            fixes_of[lot] = per_lot.get(lot, 0)

        first, last = con.execute("select min(publish_date), max(publish_date) from new_notices").fetchone()
        n_tru, with_tru = con.execute("""
            select count(*), count(distinct lot_id) from new_tru
            where lot_id in (select lot_id from new_notices)""").fetchone()
        print(f"  лотов: {len(lots)} ({first} — {last}), позиций: {n_tru}, лотов с позициями: {with_tru}")

    con.execute("commit")
    total, in_sets = con.execute("select count(distinct lot_id), count(*) from test_lots").fetchone()
    print(f"\nвсего тестовых лотов: {total} (строк по наборам: {in_sets}), "
          f"исправлений кодов: {con.execute('select coalesce(sum(positions), 0) from code_fixes').fetchone()[0]}")
    con.close()


if __name__ == "__main__":
    main()
