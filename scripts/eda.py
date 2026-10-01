"""Разведка данных: объёмы, пропуски, битые ИНН, ОКПД2, участники на лот, даты.

Запуск: python scripts/eda.py > docs/eda_output.txt
"""
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
con = duckdb.connect(str(ROOT / "data" / "rlt.duckdb"), read_only=True)


def show(title: str, sql: str) -> None:
    print(f"\n=== {title} ===")
    try:
        cur = con.execute(sql)
    except duckdb.Error as e:
        print(f"ОШИБКА: {e}")
        return
    cols = [d[0] for d in cur.description]
    n_rows = [[("" if v is None else str(v)) for v in r] for r in cur.fetchall()]
    widths = [max(len(c), *(len(r[i]) for r in n_rows)) if n_rows else len(c) for i, c in enumerate(cols)]
    print(" | ".join(c.ljust(w) for c, w in zip(cols, widths)))
    for r in n_rows:
        print(" | ".join(v.ljust(w) for v, w in zip(r, widths)))


# Контрольная сумма ИНН: 10 знаков — юрлицо, 12 — ИП/физлицо.
con.execute("""
create temp macro inn_digit(inn, weights) as
    (list_sum(list_transform(weights, (w, i) -> w * try_cast(substr(inn, i, 1) as int))) % 11) % 10
""")
con.execute("""
create temp macro inn_valid(inn) as case
    when inn is null or not regexp_full_match(inn, '\\d{10}|\\d{12}') then false
    when length(inn) = 10 then
        inn_digit(inn, [2,4,10,3,5,9,4,6,8]) = try_cast(substr(inn, 10, 1) as int)
    else
        inn_digit(inn, [7,2,4,10,3,5,9,4,6,8]) = try_cast(substr(inn, 11, 1) as int)
        and inn_digit(inn, [3,7,2,4,10,3,5,9,4,6,8]) = try_cast(substr(inn, 12, 1) as int)
end
""")

# ---------- объёмы и ключи ----------
show("Объёмы", """
select 'notices' t, count(*) n, count(distinct lot_id) lots from notices
union all select 'tru', count(*), count(distinct lot_id) from tru
union all select 'suppliers', count(*), count(distinct lot_id) from suppliers
""")

show("Уникальность ключей", """
select
    (select count(*) - count(distinct lot_id) from notices) as notices_dup_lot_id,
    (select count(distinct procedure_id) from notices) as procedures,
    (select count(*) from (select lot_id, product_name, okpd2_code from tru group by all having count(*) > 1)) as tru_dup_rows,
    (select count(*) from (select lot_id, supplier_inn from suppliers group by all having count(*) > 1)) as supplier_dup_pairs
""")

show("Покрытие связей по lot_id", """
with n as (select distinct lot_id from notices),
     t as (select distinct lot_id from tru),
     s as (select distinct lot_id from suppliers)
select
    (select count(*) from n) as lots,
    (select count(*) from n semi join t using (lot_id)) as with_tru,
    (select count(*) from n semi join s using (lot_id)) as with_suppliers,
    (select count(*) from n semi join t using (lot_id) semi join s using (lot_id)) as with_both,
    (select count(*) from t anti join n using (lot_id)) as tru_orphans,
    (select count(*) from s anti join n using (lot_id)) as suppliers_orphans
""")

# ---------- пропуски ----------
show("Пропуски: notices", """
select count(*) as n_rows,
    count(*) - count(publish_date) as publish_date, count(*) - count(procedure_id) as procedure_id,
    count(*) - count(lot_id) as lot_id, count(*) - count(start_price) as start_price,
    count(*) - count(reqnum) as reqnum, count(*) - count(procedure_name) as procedure_name,
    count(*) - count(subject) as subject, count(*) - count(is_smp) as is_smp,
    count(*) - count(customer_inn) as customer_inn, count(*) - count(customer_kpp) as customer_kpp,
    count(*) - count(source) as source
from notices
""")
show("Пропуски: tru", """
select count(*) n_rows, count(*) - count(lot_id) lot_id,
    count(*) - count(product_name) product_name, count(*) - count(okpd2_code) okpd2_code
from tru
""")
show("Пропуски: suppliers", """
select count(*) n_rows, count(*) - count(lot_id) lot_id,
    count(*) - count(supplier_inn) supplier_inn, count(*) - count(supplier_kpp) supplier_kpp,
    count(*) - count(is_winner) is_winner
from suppliers
""")

# ---------- извещения ----------
show("Площадка и СМП", """
select source, is_smp, count(*) lots, round(100.0 * count(*) / sum(count(*)) over (), 1) pct,
    round(median(start_price)) median_price
from notices group by all order by lots desc
""")

show("Даты: диапазон", "select min(publish_date) min_date, max(publish_date) max_date from notices")
show("Даты: лоты по месяцам", """
select strftime(publish_date, '%Y-%m') ym, count(*) lots,
    count(*) filter (source = 'ЭМ') em, count(*) filter (source = 'АИС ГЗ') aisgz
from notices group by all order by ym
""")

show("Цена: квантили", """
select source, count(*) lots,
    count(*) filter (start_price is null or start_price <= 0) non_positive,
    round(quantile_cont(start_price, 0.05)) p05, round(quantile_cont(start_price, 0.25)) p25,
    round(median(start_price)) p50, round(quantile_cont(start_price, 0.75)) p75,
    round(quantile_cont(start_price, 0.95)) p95, round(max(start_price)) p100
from notices group by all
""")

show("Текст: subject и procedure_name", """
select
    count(*) filter (subject = procedure_name) same_as_procedure_name,
    round(avg(length(subject))) avg_len, median(length(subject)) median_len,
    count(*) filter (length(subject) < 10) shorter_10,
    count(distinct subject) distinct_subjects
from notices
""")

show("Лотов на процедуру", """
select lots_in_procedure, count(*) procedures from (
    select least(count(*), 6) lots_in_procedure from notices group by procedure_id
) group by all order by 1
""")

show("Заказчики", """
select count(distinct customer_inn) customers,
    count(*) filter (not inn_valid(customer_inn)) invalid_inn_rows,
    count(*) filter (customer_kpp is not null and not regexp_full_match(customer_kpp, '\\d{9}')) bad_kpp_rows
from notices
""")
show("Заказчики: регион по КПП (топ-5)", """
select substr(customer_kpp, 1, 2) region, count(*) lots, count(distinct customer_inn) customers
from notices group by all order by lots desc limit 5
""")
show("Заказчики: концентрация", """
with c as (select customer_inn, count(*) n from notices group by all)
select count(*) customers, median(n) median_lots, max(n) max_lots,
    round(100.0 * (select sum(n) from (select n from c order by n desc limit 100)) / sum(n), 1) top100_share_pct
from c
""")

# ---------- ТРУ и ОКПД2 ----------
show("ОКПД2: формат кода", """
select regexp_replace(okpd2_code, '\\d', '9', 'g') pattern, count(*) n_rows,
    round(100.0 * count(*) / sum(count(*)) over (), 2) pct
from tru group by all order by n_rows desc limit 12
""")

show("ОКПД2: число уникальных значений по уровням", """
select count(distinct okpd2_code) full_code,
    count(distinct substr(okpd2_code, 1, 2)) class_2,
    count(distinct substr(okpd2_code, 1, 5)) group_4,
    count(distinct substr(okpd2_code, 1, 8)) cat_6,
    count(distinct product_name) product_names
from tru
""")

show("ОКПД2: топ-25 классов (2 знака) по числу лотов", """
select substr(okpd2_code, 1, 2) okpd_class, count(distinct lot_id) lots, count(*) positions,
    round(100.0 * count(distinct lot_id) / (select count(distinct lot_id) from tru), 1) pct_lots
from tru group by all order by lots desc limit 25
""")

show("ОКПД2: концентрация полных кодов", """
with c as (select okpd2_code, count(distinct lot_id) n from tru group by all)
select count(*) codes,
    count(*) filter (n = 1) codes_1_lot, count(*) filter (n < 5) codes_lt5_lots,
    count(*) filter (n >= 100) codes_ge100_lots, median(n) median_lots
from c
""")

show("Позиций и разных кодов на лот", """
with l as (
    select lot_id, count(*) positions, count(distinct okpd2_code) codes,
        count(distinct substr(okpd2_code, 1, 2)) classes
    from tru group by all
)
select round(avg(positions), 2) avg_positions, median(positions) median_positions,
    quantile_cont(positions, 0.95) p95_positions, max(positions) max_positions,
    round(100.0 * count(*) filter (codes > 1) / count(*), 1) pct_multi_code,
    round(100.0 * count(*) filter (classes > 1) / count(*), 1) pct_multi_class
from l
""")

# ---------- участники ----------
show("ИНН поставщиков: длина и валидность (по уникальным)", """
with s as (select distinct supplier_inn from suppliers)
select length(supplier_inn) len, count(*) inns,
    count(*) filter (inn_valid(supplier_inn)) inn_ok,
    count(*) filter (not inn_valid(supplier_inn)) inn_bad
from s group by all order by inns desc
""")
show("ИНН поставщиков: заявки с битым ИНН", """
select count(*) bids, count(*) filter (not inn_valid(supplier_inn)) bad_inn_bids,
    count(distinct supplier_inn) filter (not inn_valid(supplier_inn)) bad_inns
from suppliers
""")
show("ИНН поставщиков: примеры битых", """
select supplier_inn, count(*) n_rows from suppliers
where not inn_valid(supplier_inn) group by all order by n_rows desc limit 15
""")
show("КПП поставщиков", """
select
    count(*) filter (supplier_kpp is null) kpp_null,
    count(*) filter (supplier_kpp is null and length(supplier_inn) = 12) kpp_null_ip,
    count(*) filter (supplier_kpp is not null and not regexp_full_match(supplier_kpp, '\\d{9}')) kpp_bad,
    (select count(*) from (select supplier_inn from suppliers group by all
        having count(distinct supplier_kpp) > 1)) inns_with_several_kpp
from suppliers
""")
show("Поставщики: регион по КПП (топ-10)", """
select substr(supplier_kpp, 1, 2) region, count(distinct supplier_inn) suppliers, count(*) bids,
    round(100.0 * count(*) / sum(count(*)) over (), 1) pct_bids
from suppliers group by all order by bids desc limit 10
""")

show("Участников на лот", """
with l as (select lot_id, count(*) n, count(*) filter (is_winner) winners from suppliers group by all)
select least(n, 8) participants, count(*) lots,
    round(100.0 * count(*) / sum(count(*)) over (), 1) pct
from l group by all order by 1
""")
show("Победителей на лот", """
with l as (select lot_id, count(*) filter (is_winner) winners from suppliers group by all)
select least(winners, 3) winners, count(*) lots from l group by all order by 1
""")
show("Участников на лот по площадкам", """
with l as (select lot_id, count(*) n from suppliers group by all)
select n.source, count(*) lots_with_suppliers, round(avg(l.n), 2) avg_participants,
    round(100.0 * count(*) filter (l.n = 1) / count(*), 1) pct_single
from l join notices n using (lot_id) group by all
""")

show("Активность поставщиков", """
with s as (
    select supplier_inn, count(distinct lot_id) bids, count(distinct lot_id) filter (is_winner) wins
    from suppliers group by all
)
select count(*) suppliers,
    count(*) filter (bids = 1) one_bid, count(*) filter (bids between 2 and 4) bids_2_4,
    count(*) filter (bids between 5 and 19) bids_5_19, count(*) filter (bids >= 20) bids_ge20,
    count(*) filter (wins = 0) never_won, median(bids) median_bids, max(bids) max_bids
from s
""")
show("Доля заявок у топ-поставщиков", """
with s as (select supplier_inn, count(*) bids from suppliers group by all),
     r as (select bids, row_number() over (order by bids desc) rn, sum(bids) over () total from s)
select
    round(100.0 * sum(bids) filter (rn <= 100) / any_value(total), 1) top100_pct,
    round(100.0 * sum(bids) filter (rn <= 1000) / any_value(total), 1) top1000_pct,
    round(100.0 * sum(bids) filter (rn <= 10000) / any_value(total), 1) top10000_pct
from r
""")
show("Специализация: классов ОКПД2 на поставщика (bids >= 5)", """
with s as (
    select s.supplier_inn, count(distinct s.lot_id) bids, count(distinct substr(t.okpd2_code, 1, 2)) classes
    from suppliers s join tru t using (lot_id) group by all having bids >= 5
)
select count(*) suppliers, median(classes) median_classes,
    round(100.0 * count(*) filter (classes <= 2) / count(*), 1) pct_le2_classes,
    round(100.0 * count(*) filter (classes >= 10) / count(*), 1) pct_ge10_classes
from s
""")
show("Повторные пары заказчик-поставщик", """
with p as (
    select n.customer_inn, s.supplier_inn, count(distinct lot_id) lots
    from suppliers s join notices n using (lot_id) group by all
)
select count(*) pairs, count(*) filter (lots >= 2) repeat_pairs,
    round(100.0 * sum(lots) filter (lots >= 2) / sum(lots), 1) pct_bids_in_repeat_pairs
from p
""")

# ---------- аномалии, найденные по ходу ----------
show("Лоты без участников: по площадкам", """
select n.source, count(*) lots, count(*) filter (s.lot_id is null) without_suppliers,
    round(100.0 * count(*) filter (s.lot_id is null) / count(*), 1) pct
from notices n left join (select distinct lot_id from suppliers) s using (lot_id) group by all
""")
show("Лоты без заказчика: по площадкам", """
select source, count(*) lots, min(publish_date) min_date, max(publish_date) max_date
from notices where customer_inn is null group by all
""")
show("АИС ГЗ: is_winner у единственного участника", """
with l as (select lot_id, count(*) n, bool_or(is_winner) has_winner from suppliers group by all)
select n.source, l.n = 1 single, l.has_winner, count(*) lots
from l join notices n using (lot_id) group by all order by lots desc
""")
show("ЭМ: распределение числа участников", """
with l as (select lot_id, count(*) n from suppliers group by all)
select least(l.n, 8) participants, count(*) lots, round(100.0 * count(*) / sum(count(*)) over (), 1) pct
from l join notices n using (lot_id) where n.source = 'ЭМ' group by all order by 1
""")
show("Поставщики: пересечение площадок", """
with s as (
    select s.supplier_inn, bool_or(n.source = 'ЭМ') em, bool_or(n.source = 'АИС ГЗ') aisgz
    from suppliers s join notices n using (lot_id) group by all
)
select em, aisgz, count(*) suppliers from s group by all order by suppliers desc
""")
show("КПП поставщика с регионом 00: примеры", """
select supplier_inn, supplier_kpp, count(*) bids from suppliers
where supplier_kpp like '00%' group by all order by bids desc limit 8
""")
show("Дубли пар лот-поставщик: примеры", """
select lot_id, supplier_inn, count(*) n, count(distinct supplier_kpp) kpps, count(distinct is_winner) winner_flags
from suppliers group by all having count(*) > 1 order by n desc limit 5
""")
show("Цена: самые дорогие лоты", """
select lot_id, source, start_price, left(subject, 70) subject from notices order by start_price desc limit 8
""")
show("Самые частые subject", """
select left(subject, 80) subject, count(*) lots from notices group by all order by lots desc limit 12
""")
show("Топ поставщиков по заявкам", """
select supplier_inn, count(*) bids, count(*) filter (is_winner) wins,
    count(distinct n.customer_inn) customers, count(distinct substr(t.okpd2_code, 1, 2)) classes
from suppliers s join notices n using (lot_id)
    left join (select lot_id, min(okpd2_code) okpd2_code from tru group by all) t using (lot_id)
group by all order by bids desc limit 10
""")

# ---------- к шагу 3: насколько история предсказывает будущее ----------
show("Холодный старт: последние 2 месяца против истории", """
with cut as (select max(publish_date) - interval 2 month d from notices),
     test as (
        select s.lot_id, s.supplier_inn from suppliers s join notices n using (lot_id), cut
        where n.publish_date > cut.d
     ),
     seen as (
        select distinct s.supplier_inn from suppliers s join notices n using (lot_id), cut
        where n.publish_date <= cut.d
     )
select (select d from cut) cutoff, count(distinct lot_id) test_lots, count(*) test_bids,
    round(100.0 * count(*) filter (supplier_inn in (select supplier_inn from seen)) / count(*), 1) pct_bids_by_known_supplier
from test
""")
