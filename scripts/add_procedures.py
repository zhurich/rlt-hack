"""Добавить в базу процедуры без участников — тестовый набор организаторов.

    python scripts/add_procedures.py [извещения.csv потоварка.csv]

Без аргументов берёт data/raw/*извещения*.csv и data/raw/*потоварка*.csv. Формат файлов тот же,
что у notices.csv и tru.csv. Лоты дописываются в notices и tru, их номера — в таблицу test_lots.
Повторный запуск заменяет прежний тестовый набор. `scripts/load.py` тестовые лоты стирает.

После запуска пересобрать индексы: python -m recsys.build, затем python -m recsys.pool
(словарь TF-IDF общий), и только потом — python scripts/predict.py.
"""
import sys
from pathlib import Path

import duckdb

from load import DB, RAW, notices_select, tru_select


def find(pattern: str) -> Path:
    found = sorted(RAW.glob(pattern))
    if len(found) != 1:
        sys.exit(f"в {RAW} ожидался один файл {pattern}, найдено {len(found)}")
    return found[0]


def main() -> None:
    if len(sys.argv) == 3:
        notices, tru = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    else:
        notices, tru = find("*извещения*.csv"), find("*потоварка*.csv")

    con = duckdb.connect(str(DB))
    con.execute(f"create temp table new_notices as {notices_select(notices)}")
    con.execute(f"create temp table new_tru as {tru_select(tru)}")

    bad = con.execute("""
        select count(*) filter (lot_id is null), count(*) filter (publish_date is null),
            count(*) - count(distinct lot_id)
        from new_notices""").fetchone()
    if any(bad):
        sys.exit(f"битые строки в {notices.name}: без lot_id {bad[0]}, без даты {bad[1]}, дублей {bad[2]}")

    # Одной транзакцией: при отказе прежний тестовый набор остаётся на месте.
    con.execute("begin")
    con.execute("create table if not exists test_lots (lot_id bigint)")
    con.execute("delete from notices where lot_id in (select lot_id from test_lots)")
    con.execute("delete from tru where lot_id in (select lot_id from test_lots)")
    known = con.execute(
        "select count(*) from new_notices where lot_id in (select lot_id from notices)").fetchone()[0]
    if known:
        con.execute("rollback")
        sys.exit(f"{known} лотов из {notices.name} уже есть в истории — так добавлять нельзя")
    con.execute("insert into notices select * from new_notices")
    con.execute("insert into tru select * from new_tru where lot_id in (select lot_id from new_notices)")
    con.execute("delete from test_lots")
    con.execute("insert into test_lots select lot_id from new_notices")
    con.execute("commit")

    lots, first, last = con.execute(
        "select count(*), min(publish_date), max(publish_date) from new_notices").fetchone()
    rows, with_tru = con.execute("""
        select count(*), count(distinct lot_id) from new_tru
        where lot_id in (select lot_id from new_notices)""").fetchone()
    print(f"добавлено лотов: {lots} ({first} — {last}), позиций: {rows}, лотов с позициями: {with_tru}")
    con.close()


if __name__ == "__main__":
    main()
