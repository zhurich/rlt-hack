"""Единый реестр субъектов МСП (ФНС, открытые данные) → таблица rmsp в data/rlt.duckdb.

Из ~6,5 млн записей оставляем: всех, кто уже есть среди поставщиков, и всех из
Санкт-Петербурга и Ленинградской области (кандидаты в новые поставщики).

    python -m enrich.rmsp
"""
import json
import sys
import time
import xml.etree.ElementTree as ET
import zipfile
from multiprocessing import Pool
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "rlt.duckdb"
ZIP = ROOT / "data" / "ext" / "rsmp.zip"
PARTS = ROOT / "data" / "ext" / "rmsp_parts"
SOURCE_URL = "https://file.nalog.ru/opendata/7707329152-rsmp/data-10092026-structure-12052026.zip"
REGIONS = {"78", "47"}
WORKERS = 12

_known: frozenset[str] = frozenset()


def _init(known: frozenset[str]) -> None:
    global _known
    _known = known


def _place(mn: ET.Element) -> str:
    parts = []
    for tag in ("Регион", "Район", "Город", "НаселПункт"):
        el = mn.find(tag)
        if el is not None:
            parts.append(f"{el.get('Тип', '')} {el.get('Наим', '')}".strip())
    return ", ".join(parts)


def _parse(doc: ET.Element) -> dict | None:
    mn = doc.find("СведМН")
    region = mn.get("КодРегион") if mn is not None else None
    org, ip = doc.find("ОргВклМСП"), doc.find("ИПВклМСП")
    if org is not None:
        inn, kind = org.get("ИННЮЛ"), "ЮЛ"
        name, short, ogrn = org.get("НаимОрг"), org.get("НаимОргСокр"), org.get("ОГРН")
    elif ip is not None:
        inn, kind, ogrn = ip.get("ИННФЛ"), "ИП", ip.get("ОГРНИП")
        fio = ip.find("ФИОИП")
        short = "ИП " + " ".join(filter(None, (fio.get("Фамилия"), fio.get("Имя"), fio.get("Отчество"))))
        name = short
    else:
        return None
    if inn not in _known and region not in REGIONS:
        return None
    okved = doc.find("СвОКВЭД")
    main = okved.find("СвОКВЭДОсн") if okved is not None else None
    extra = okved.findall("СвОКВЭДДоп") if okved is not None else []
    return {
        "inn": inn, "kind": kind, "name": name, "short_name": short, "ogrn": ogrn,
        "region": region, "place": _place(mn) if mn is not None else None,
        "category": doc.get("КатСубМСП"), "date_included": doc.get("ДатаВклМСП"),
        "is_new": doc.get("ПризНовМСП") == "1", "is_social": doc.get("СведСоцПред") == "1",
        "headcount": doc.get("ССЧР"),
        "okved_main": main.get("КодОКВЭД") if main is not None else None,
        "okved_main_name": main.get("НаимОКВЭД") if main is not None else None,
        "okved_extra": [e.get("КодОКВЭД") for e in extra],
        "products": [{"code": p.get("КодПрод"), "name": p.get("НаимПрод")} for p in doc.findall("СвПрод")],
        "licenses": sorted({n.text for lic in doc.findall("СвЛиценз") for n in lic.findall("НаимЛицВД") if n.text}),
        "state_date": doc.get("ДатаСост"),
    }


def _work(task: tuple[int, list[str]]) -> tuple[int, int]:
    part, names = task
    seen = kept = 0
    with zipfile.ZipFile(ZIP) as z, open(PARTS / f"{part:04d}.jsonl", "w", encoding="utf-8") as out:
        for name in names:
            with z.open(name) as f:
                for _, el in ET.iterparse(f, events=("end",)):
                    if el.tag != "Документ":
                        continue
                    seen += 1
                    row = _parse(el)
                    if row:
                        kept += 1
                        out.write(json.dumps(row, ensure_ascii=False) + "\n")
                    el.clear()
    return seen, kept


def main() -> None:
    t0 = time.time()
    con = duckdb.connect(str(DB))
    known = frozenset(r[0] for r in con.execute("select distinct supplier_inn from suppliers").fetchall())
    with zipfile.ZipFile(ZIP) as z:
        names = [n for n in z.namelist() if n.lower().endswith(".xml")]
    PARTS.mkdir(parents=True, exist_ok=True)
    for old in PARTS.glob("*.jsonl"):
        old.unlink()
    chunk = max(1, len(names) // (WORKERS * 8))
    tasks = [(i, names[a:a + chunk]) for i, a in enumerate(range(0, len(names), chunk))]
    print(f"файлов в архиве: {len(names):,}, заданий: {len(tasks)}")

    seen = kept = 0
    with Pool(WORKERS, initializer=_init, initargs=(known,)) as pool:
        for i, (s, k) in enumerate(pool.imap_unordered(_work, tasks), 1):
            seen, kept = seen + s, kept + k
            if i % 10 == 0:
                print(f"  {i}/{len(tasks)}: просмотрено {seen:,}, отобрано {kept:,}, {time.time() - t0:.0f} с")
                sys.stdout.flush()

    con.execute(f"""
        create or replace table rmsp as
        select inn, kind, name, short_name, ogrn, region, place,
            try_cast(category as int) as category,
            try_strptime(date_included, '%d.%m.%Y')::date as date_included,
            is_new, is_social, try_cast(headcount as int) as headcount,
            okved_main, okved_main_name, okved_extra, products, licenses,
            try_strptime(state_date, '%d.%m.%Y')::date as state_date,
            'Единый реестр субъектов МСП (ФНС)' as source, '{SOURCE_URL}' as source_url
        from read_json('{(PARTS / '*.jsonl').as_posix()}', format='newline_delimited',
            columns={{inn: 'varchar', kind: 'varchar', name: 'varchar', short_name: 'varchar', ogrn: 'varchar',
                region: 'varchar', place: 'varchar', category: 'varchar', date_included: 'varchar',
                is_new: 'boolean', is_social: 'boolean', headcount: 'varchar', okved_main: 'varchar',
                okved_main_name: 'varchar', okved_extra: 'varchar[]',
                products: 'struct(code varchar, name varchar)[]', licenses: 'varchar[]', state_date: 'varchar'}})
        qualify row_number() over (partition by inn order by state_date desc) = 1
    """)
    n = con.execute("select count(*) from rmsp").fetchone()[0]
    print(f"всего в реестре {seen:,}, в таблице rmsp {n:,}, {time.time() - t0:.0f} с")


if __name__ == "__main__":
    main()
