"""Открытые данные ФНС по юрлицам → таблицы fns_headcount, fns_revexp, fns_debt.

Берём только ИНН, которые уже есть среди поставщиков или в таблице rmsp (сначала enrich.rmsp).

    python -m enrich.fns
"""
import json
import time
import xml.etree.ElementTree as ET
import zipfile
from multiprocessing import Pool
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "rlt.duckdb"
EXT = ROOT / "data" / "ext"
WORKERS = 12

DATASETS = {
    "sshr": {
        "table": "fns_headcount", "source": "Среднесписочная численность работников (ФНС)",
        "url": "https://file.nalog.ru/opendata/7707329152-sshr2019/data-20260925-structure-20200408.zip",
    },
    "revexp": {
        "table": "fns_revexp", "source": "Доходы и расходы по бухгалтерской отчётности (ФНС)",
        "url": "https://file.nalog.ru/opendata/7707329152-revexp/data-20260925-structure-20180110.zip",
    },
    "debtam": {
        "table": "fns_debt", "source": "Задолженность по налогам и сборам (ФНС)",
        "url": "https://file.nalog.ru/opendata/7707329152-debtam/data-20260925-structure-20181201.zip",
    },
}

_known: frozenset[str] = frozenset()


def _init(known: frozenset[str]) -> None:
    global _known
    _known = known


def _values(kind: str, doc: ET.Element) -> dict:
    if kind == "sshr":
        return {"headcount": doc.find("СведССЧР").get("КолРаб")}
    if kind == "revexp":
        el = doc.find("СведДохРасх")
        return {"revenue": el.get("СумДоход"), "expense": el.get("СумРасход")}
    return {"debt": sum(float(el.get("ОбщСумНедоим") or 0) for el in doc.findall("СведНедоим"))}


def _work(task: tuple[str, int, list[str]]) -> int:
    kind, part, names = task
    kept = 0
    with zipfile.ZipFile(EXT / f"{kind}.zip") as z, \
            open(EXT / f"{kind}_parts" / f"{part:04d}.jsonl", "w", encoding="utf-8") as out:
        for name in names:
            with z.open(name) as f:
                for _, el in ET.iterparse(f, events=("end",)):
                    if el.tag != "Документ":
                        continue
                    np_ = el.find("СведНП")
                    inn = np_.get("ИННЮЛ") if np_ is not None else None
                    if inn in _known:
                        row = {"inn": inn, "name": np_.get("НаимОрг"), "state_date": el.get("ДатаСост")}
                        row.update(_values(kind, el))
                        out.write(json.dumps(row, ensure_ascii=False) + "\n")
                        kept += 1
                    el.clear()
    return kept


def main() -> None:
    con = duckdb.connect(str(DB))
    known = frozenset(r[0] for r in con.execute(
        "select supplier_inn from suppliers union select inn from rmsp").fetchall())
    for kind, meta in DATASETS.items():
        t0 = time.time()
        parts = EXT / f"{kind}_parts"
        parts.mkdir(exist_ok=True)
        for old in parts.glob("*.jsonl"):
            old.unlink()
        with zipfile.ZipFile(EXT / f"{kind}.zip") as z:
            names = [n for n in z.namelist() if n.lower().endswith(".xml")]
        chunk = max(1, len(names) // (WORKERS * 4))
        tasks = [(kind, i, names[a:a + chunk]) for i, a in enumerate(range(0, len(names), chunk))]
        with Pool(WORKERS, initializer=_init, initargs=(known,)) as pool:
            kept = sum(pool.imap_unordered(_work, tasks))
        con.execute(f"""
            create or replace table {meta['table']} as
            select * exclude (state_date), try_strptime(state_date, '%d.%m.%Y')::date as state_date,
                '{meta['source']}' as source, '{meta['url']}' as source_url
            from read_json('{(parts / '*.jsonl').as_posix()}', format='newline_delimited')
            qualify row_number() over (partition by inn order by state_date desc) = 1
        """)
        n = con.execute(f"select count(*) from {meta['table']}").fetchone()[0]
        print(f"{meta['table']}: отобрано {kept:,}, в таблице {n:,}, {time.time() - t0:.0f} с")


if __name__ == "__main__":
    main()
