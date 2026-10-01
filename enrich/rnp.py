"""Реестр недобросовестных поставщиков (ЕИС, открытый поиск) → таблица rnp.

Постранично читает результаты поиска по действующим записям. Запросы идут по одному,
с паузой, чтобы не нагружать сайт.

    python -m enrich.rnp
"""
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "rlt.duckdb"
OUT = ROOT / "data" / "ext" / "rnp.jsonl"
BASE = "https://zakupki.gov.ru/epz/dishonestsupplier/search/results.html"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"
LAWS = {"fz44": "44-ФЗ", "fz223": "223-ФЗ", "ppRf615": "ПП РФ 615"}
PAUSE = 1.0
MAX_PAGES = 400


def fetch(law: str, page: int, ascending: bool) -> str:
    params = {
        "searchString": "", "morphology": "on", "sortBy": "UPDATE_DATE",
        "sortDirection": "true" if ascending else "false",
        "pageNumber": page, "recordsPerPage": "_50", law: "on",
    }
    req = urllib.request.Request(f"{BASE}?{urllib.parse.urlencode(params)}", headers={"User-Agent": UA})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", errors="replace")
        except Exception as e:  # сеть ЕИС нестабильна — повторяем
            print(f"    повтор {attempt + 1}: {e}")
            time.sleep(5 * (attempt + 1))
    return ""


def field(text: str, label: str) -> str | None:
    m = re.search(re.escape(label) + r"[\s|]+([^|]+?)\s*\|", text)
    return m.group(1).strip() if m else None


def parse(html: str, law: str) -> list[dict]:
    html = re.sub(r"<script.*?</script>|<style.*?</style>", "", html, flags=re.S)
    rows = []
    for block in html.split("search-registry-entry-block box-shadow-search-input")[1:]:
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " | ", block)).replace("&quot;", '"')
        number = re.search(r"№\s*([^\s|]+)", text)
        rows.append({
            "law": LAWS[law], "number": number.group(1) if number else None,
            "name": field(text, "Наименование (ФИО) недобросовестного поставщика"),
            "inn": field(text, "ИНН (аналог ИНН)"),
            "included": field(text, "Включено"), "updated": field(text, "Обновлено"),
        })
    return rows


def main() -> None:
    rows: dict[tuple, dict] = {}
    # ЕИС отдаёт не больше 100 страниц на запрос, поэтому идём с двух концов сортировки.
    for law in LAWS:
        for ascending in (False, True):
            for page in range(1, MAX_PAGES + 1):
                got = parse(fetch(law, page, ascending), law)
                new = sum((r["law"], r["number"]) not in rows for r in got)
                for r in got:
                    rows[(r["law"], r["number"])] = r
                if page % 10 == 0 or not new:
                    print(f"  {LAWS[law]} {'↑' if ascending else '↓'}, стр. {page}: "
                          f"на странице {len(got)}, новых {new}, всего {len(rows)}", flush=True)
                if not new:
                    break
                time.sleep(PAUSE)
            if page < 100:  # дошли до конца без ограничения — второй проход не нужен
                break
    OUT.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows.values()), encoding="utf-8")

    con = duckdb.connect(str(DB))
    con.execute(f"""
        create or replace table rnp as
        select law, number, name, inn,
            try_strptime(included, '%d.%m.%Y')::date as included,
            try_strptime(updated, '%d.%m.%Y')::date as updated,
            'Реестр недобросовестных поставщиков (ЕИС)' as source, '{BASE}' as source_url,
            current_date as fetched
        from read_json('{OUT.as_posix()}', format='newline_delimited',
            columns={{law: 'varchar', number: 'varchar', name: 'varchar', inn: 'varchar',
                      included: 'varchar', updated: 'varchar'}})
    """)
    print(con.execute("""
        select count(*) as records, count(distinct inn) as inns,
            count(distinct inn) filter (inn in (select supplier_inn from suppliers)) as among_suppliers
        from rnp
    """).fetchall())


if __name__ == "__main__":
    main()
