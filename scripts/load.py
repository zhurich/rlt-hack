"""Загрузка исходных CSV в DuckDB (data/rlt.duckdb).

Всё читается строками, типы приводятся через try_cast: битые значения становятся NULL,
а не роняют загрузку. ИНН/КПП остаются строками.
"""
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
DB = ROOT / "data" / "rlt.duckdb"


def read_csv(name: str) -> str:
    path = (RAW / name).as_posix()
    return (
        f"read_csv('{path}', delim=';', quote='\"', escape='\"', header=true, "
        "all_varchar=true, strict_mode=false, null_padding=true)"
    )


def main() -> None:
    con = duckdb.connect(str(DB))

    con.execute(f"""
        create or replace table notices as
        select
            try_cast(publish_date as date) as publish_date,
            try_cast(procedure_id as bigint) as procedure_id,
            try_cast(lot_id as bigint) as lot_id,
            try_cast(start_price as double) as start_price,
            nullif(trim(reqnum), '') as reqnum,
            nullif(trim(procedure_name), '') as procedure_name,
            nullif(trim(subject), '') as subject,
            try_cast(is_smp as boolean) as is_smp,
            nullif(trim(customer_inn), '') as customer_inn,
            nullif(trim(customer_kpp), '') as customer_kpp,
            nullif(trim(is_eshop_or_aisgz), '') as source
        from {read_csv('notices.csv')}
    """)

    con.execute(f"""
        create or replace table tru as
        select
            try_cast(lot_id as bigint) as lot_id,
            nullif(trim(product_name), '') as product_name,
            nullif(trim(okpd2_code), '') as okpd2_code
        from {read_csv('tru.csv')}
    """)

    con.execute(f"""
        create or replace table suppliers as
        select
            try_cast(lot_id as bigint) as lot_id,
            nullif(trim(supplier_inn), '') as supplier_inn,
            nullif(trim(supplier_kpp), '') as supplier_kpp,
            try_cast(is_winner as boolean) as is_winner
        from {read_csv('suppliers.csv')}
    """)

    for table in ("notices", "tru", "suppliers"):
        rows = con.execute(f"select count(*) from {table}").fetchone()[0]
        print(f"{table}: {rows:,}")

    con.close()


if __name__ == "__main__":
    main()
