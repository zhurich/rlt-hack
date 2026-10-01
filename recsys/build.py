"""Предрасчёт индекса подбора: python -m recsys.build → data/index.pkl.

В индексе нет агрегатов «на все времена»: только постинги заявок (по префиксам ОКПД2,
по заказчикам, по лотам) и TF-IDF матрица. Агрегаты считаются при запросе с отсечкой
по дате, поэтому один индекс годится и для подбора, и для метрики без утечек.
"""
import pickle
import time
from pathlib import Path

import duckdb
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from .text import analyze

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "rlt.duckdb"
INDEX = ROOT / "data" / "index.pkl"

EPOCH = "2020-01-01"
# Уровни иерархии ОКПД2 как длины префикса: класс, группа, категория, полный код.
LEVELS = (2, 5, 8, 12)
MAX_NAMES = 20  # позиций лота, попадающих в текст


def ptr_from_sorted(ids: np.ndarray, n: int) -> np.ndarray:
    return np.searchsorted(ids, np.arange(n + 1)).astype(np.int64)


def main() -> None:
    t0 = time.time()
    con = duckdb.connect()
    con.execute(f"attach '{DB.as_posix()}' as src (read_only)")

    con.execute(f"""
        create table lots as
        select (row_number() over (order by lot_id) - 1)::int as lot_idx, lot_id,
            datediff('day', date '{EPOCH}', publish_date)::int as day,
            case when start_price > 0 then ln(start_price) end as logprice,
            customer_inn, source = 'АИС ГЗ' as is_ais, is_smp, subject
        from src.notices
    """)
    con.execute("""
        create table customers as
        select (row_number() over (order by customer_inn) - 1)::int as cust_idx, customer_inn
        from (select distinct customer_inn from lots where customer_inn is not null)
    """)
    # Регион: КПП, а для ИП (КПП пуст или 000000000) — первые цифры ИНН.
    # is_person: физлица-преподаватели — 12-значный ИНН, только класс 85 и только АИС ГЗ.
    con.execute("""
        create table sup as
        with lc as (
            select lot_id, bool_and(okpd2_code like '85%') as only85 from src.tru group by all
        ), agg as (
            select s.supplier_inn,
                mode(substr(s.supplier_kpp, 1, 2))
                    filter (s.supplier_kpp is not null and s.supplier_kpp not like '00%') as kpp_region,
                bool_and(coalesce(lc.only85, false) and n.source = 'АИС ГЗ') as only_teaching
            from src.suppliers s join src.notices n using (lot_id) left join lc using (lot_id)
            group by all
        )
        select (row_number() over (order by supplier_inn) - 1)::int as sup_idx, supplier_inn,
            coalesce(kpp_region, substr(supplier_inn, 1, 2)) as region,
            length(supplier_inn) = 12 and only_teaching as is_person
        from agg
    """)
    con.execute("""
        create table bids as
        select (row_number() over (order by l.lot_idx, s.sup_idx) - 1)::int as bid_idx,
            l.lot_idx, s.sup_idx, b.is_winner
        from (
            select lot_id, supplier_inn, bool_or(is_winner) as is_winner
            from src.suppliers group by all
        ) b join lots l using (lot_id) join sup s using (supplier_inn)
    """)
    con.execute("""
        create table codes as
        select l.lot_idx, t.okpd2_code as code, count(*)::int as n
        from src.tru t join lots l using (lot_id)
        where t.okpd2_code is not null group by all
    """)

    idx: dict = {"epoch": EPOCH, "levels": LEVELS}

    lots = con.execute("""
        select lot_id, day, coalesce(logprice, 'nan'::double) as logprice,
            coalesce(c.cust_idx, -1) as cust, is_ais, is_smp
        from lots left join customers c using (customer_inn) order by lot_idx
    """).fetchnumpy()
    idx["lot_id"] = lots["lot_id"].astype(np.int64)
    idx["lot_day"] = lots["day"].astype(np.int32)
    idx["lot_logprice"] = lots["logprice"].astype(np.float32)
    idx["lot_cust"] = lots["cust"].astype(np.int32)
    idx["lot_ais"] = lots["is_ais"].astype(bool)
    idx["lot_smp"] = lots["is_smp"].astype(bool)
    n_lots = len(idx["lot_id"])

    idx["cust_inn"] = [r[0] for r in con.execute(
        "select customer_inn from customers order by cust_idx").fetchall()]

    sup = con.execute("select supplier_inn, region, is_person from sup order by sup_idx").fetchall()
    idx["sup_inn"] = [r[0] for r in sup]
    idx["sup_region"] = [r[1] for r in sup]
    idx["sup_person"] = np.array([r[2] for r in sup], dtype=bool)

    bids = con.execute("select lot_idx, sup_idx, is_winner from bids order by bid_idx").fetchnumpy()
    idx["bid_lot"] = bids["lot_idx"].astype(np.int32)
    idx["bid_sup"] = bids["sup_idx"].astype(np.int32)
    idx["bid_win"] = bids["is_winner"].astype(bool)
    idx["lot_ptr"] = ptr_from_sorted(idx["bid_lot"], n_lots)
    print(f"лоты {n_lots:,}, поставщики {len(sup):,}, заявки {len(idx['bid_lot']):,}")

    # Постинги: префикс ОКПД2 -> заявки в лотах с таким префиксом.
    post: dict[str, tuple[int, int]] = {}
    chunks, offset = [], 0
    for level in LEVELS:
        con.execute(f"""
            create or replace table post as
            select (dense_rank() over (order by p) - 1)::int as pid, p, bid_idx
            from (
                select distinct substr(c.code, 1, {level}) as p, b.bid_idx
                from codes c join bids b using (lot_idx) where length(c.code) >= {level}
            )
        """)
        keys = [r[1] for r in con.execute("select distinct pid, p from post order by pid").fetchall()]
        data = con.execute("select pid, bid_idx from post order by pid, bid_idx").fetchnumpy()
        ptr = ptr_from_sorted(data["pid"], len(keys))
        for i, key in enumerate(keys):
            post[key] = (offset + int(ptr[i]), offset + int(ptr[i + 1]))
        chunks.append(data["bid_idx"].astype(np.int32))
        offset += len(data["bid_idx"])
        print(f"уровень {level}: префиксов {len(keys):,}, записей {len(data['bid_idx']):,}")
    idx["post"] = post
    idx["post_data"] = np.concatenate(chunks)

    # Постинги: заказчик -> заявки.
    cust = con.execute("""
        select c.cust_idx, b.bid_idx
        from bids b join lots l using (lot_idx) join customers c using (customer_inn)
        order by c.cust_idx, b.bid_idx
    """).fetchnumpy()
    idx["cust_ptr"] = ptr_from_sorted(cust["cust_idx"], len(idx["cust_inn"]))
    idx["cust_data"] = cust["bid_idx"].astype(np.int32)

    # Коды лотов (для запроса по lot_id и для вывода кодов из похожих лотов).
    idx["code_list"] = [r[0] for r in con.execute(
        "select distinct code from codes order by code").fetchall()]
    lot_codes = con.execute("""
        select lot_idx, (dense_rank() over (order by code) - 1)::int as code_id, n
        from codes order by lot_idx, n desc
    """).fetchnumpy()
    idx["lot_code_ptr"] = ptr_from_sorted(lot_codes["lot_idx"], n_lots)
    idx["lot_code_id"] = lot_codes["code_id"].astype(np.int32)
    idx["lot_code_n"] = lot_codes["n"].astype(np.int32)

    # Тексты: предмет закупки + названия позиций.
    docs = [r[0] for r in con.execute(f"""
        select coalesce(l.subject, '') || ' ' || coalesce(t.names, '')
        from lots l left join (
            select lot_id, string_agg(product_name, ' ') as names from (
                select distinct lot_id, product_name from src.tru where product_name is not null
                qualify row_number() over (partition by lot_id order by product_name) <= {MAX_NAMES}
            ) group by all
        ) t using (lot_id)
        order by l.lot_idx
    """).fetchall()]
    print(f"тексты выгружены, {time.time() - t0:.0f} с")
    vectorizer = TfidfVectorizer(analyzer=analyze, min_df=2, sublinear_tf=True, dtype=np.float32)
    x = vectorizer.fit_transform(docs).tocsr()
    idx["vectorizer"] = vectorizer
    idx["x"] = x
    idx["xt"] = x.T.tocsr()
    print(f"TF-IDF: словарь {x.shape[1]:,}, ненулевых {x.nnz:,}")

    with open(INDEX, "wb") as f:
        pickle.dump(idx, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"готово: {INDEX.name}, {INDEX.stat().st_size / 2**20:.0f} МБ, {time.time() - t0:.0f} с")


if __name__ == "__main__":
    main()
