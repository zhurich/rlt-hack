"""Единый справочник компаний → таблица companies в data/rlt.duckdb.

Одна строка на ИНН: поставщики из истории закупок + компании СПб и Ленобласти из реестра МСП.
Роль определяется правилами по ОКВЭД; для каждого блока сведений записан источник.

    python -m enrich.companies
"""
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "rlt.duckdb"
OUT = ROOT / "data" / "out" / "companies.csv"

HISTORY_SOURCE = "История закупок АИС ГЗ и электронного магазина СПб, 2024–2025"
DEBT_LIMIT = 100_000  # руб. налоговой задолженности, выше — «требует проверки»
PROVEN_WINS = 3  # побед для статуса «проверенный»
OLD_ENOUGH = "2024-10-01"  # в реестре МСП раньше этой даты — больше двух лет

SQL = f"""
create or replace table companies as
with hist as (
    select s.supplier_inn as inn, count(distinct lot_id) as bids,
        count(distinct lot_id) filter (s.is_winner) as wins,
        min(n.publish_date) as first_bid, max(n.publish_date) as last_bid,
        mode(substr(s.supplier_kpp, 1, 2))
            filter (s.supplier_kpp is not null and s.supplier_kpp not like '00%') as kpp_region
    from suppliers s join notices n using (lot_id) group by all
), ids as (
    select inn from hist union select inn from rmsp where region in ('78', '47')
), bad as (
    select inn, count(*) as rnp_records, max(included) as rnp_last,
        string_agg(distinct law, ', ') as rnp_laws
    from rnp where inn is not null group by all
), base as (
    select i.inn,
        coalesce(r.kind, case length(i.inn) when 10 then 'ЮЛ' when 12 then 'ИП или физлицо' end) as kind,
        coalesce(r.short_name, r.name, hc.name, re.name) as raw_name,
        coalesce(r.region, h.kpp_region, substr(i.inn, 1, 2)) as region, r.place,
        h.inn is not null as in_history, coalesce(h.bids, 0) as bids, coalesce(h.wins, 0) as wins,
        h.first_bid, h.last_bid,
        r.okved_main, r.okved_main_name, coalesce(r.okved_extra, []) as okved_extra,
        coalesce(r.products, []) as products, coalesce(r.licenses, []) as licenses,
        r.inn is not null as in_rmsp, r.category as msp_category, r.date_included as msp_since,
        coalesce(r.is_new, false) as msp_new,
        coalesce(hc.headcount::int, r.headcount) as headcount,
        re.revenue::double as revenue, re.expense::double as expense, re.state_date as finance_date,
        d.debt::double as tax_debt,
        coalesce(b.rnp_records, 0) as rnp_records, b.rnp_last, b.rnp_laws,
        try_cast(substr(r.okved_main, 1, 2) as int) as okved_class,
        len(list_filter(coalesce(r.okved_extra, []), x -> try_cast(substr(x, 1, 2) as int) between 10 and 32)) > 0
            as has_production_extra,
        len(list_filter(coalesce(r.products, []), x -> try_cast(substr(x.code, 1, 2) as int) between 1 and 32)) > 0
            as has_goods_products,
        list_filter([
            case when h.inn is not null then '{HISTORY_SOURCE}' end,
            r.source, hc.source, re.source, d.source,
            case when b.inn is not null then 'Реестр недобросовестных поставщиков (ЕИС)' end
        ], x -> x is not null) as sources
    from ids i
    left join hist h using (inn) left join rmsp r using (inn)
    left join fns_headcount hc using (inn) left join fns_revexp re using (inn)
    left join fns_debt d using (inn) left join bad b using (inn)
)
select * exclude (raw_name, okved_class, has_goods_products, h_missing, is_wholesale),
    -- Короткая форма для названий, пришедших из выгрузок ФНС с полной правовой формой.
    replace(replace(replace(replace(raw_name,
        'ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ', 'ООО'),
        'ПУБЛИЧНОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО', 'ПАО'),
        'ЗАКРЫТОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО', 'ЗАО'),
        'АКЦИОНЕРНОЕ ОБЩЕСТВО', 'АО') as name,
    -- Класс 33 (ремонт и монтаж оборудования) формально в разделе C, но это услуги, не производство.
    case
        when okved_class between 1 and 32 then 'производитель'
        when has_goods_products then 'производитель'
        when is_wholesale then 'дистрибьютор'
        else 'поставщик'
    end as role,
    case
        when okved_class between 1 and 32
            then 'основной ОКВЭД ' || okved_main || ' — производство (' || okved_main_name || ')'
        when has_goods_products then 'в реестре МСП заявлена производимая продукция'
        when is_wholesale
            then 'основной ОКВЭД ' || okved_main || ' — оптовая торговля (' || okved_main_name || ')'
                || case when has_production_extra then '; среди дополнительных ОКВЭД есть производственные' else '' end
        when okved_class = 47
            then 'основной ОКВЭД ' || okved_main || ' — розничная торговля (' || okved_main_name || ')'
        when okved_main is not null
            then 'основной ОКВЭД ' || okved_main || ' — работы и услуги (' || okved_main_name || ')'
        else 'ОКВЭД в открытых реестрах не найден; роль по умолчанию — участник закупок'
    end as role_reason,
    case
        when okved_main is not null then 'Единый реестр субъектов МСП (ФНС)'
        else '{HISTORY_SOURCE}'
    end as role_source,
    -- Статус: насколько контрагент проверен. Негативные признаки важнее истории.
    case
        when rnp_records > 0 then 'риск'
        when coalesce(tax_debt, 0) > {DEBT_LIMIT} then 'требует проверки'
        when h_missing then 'требует проверки'
        when in_history and wins >= {PROVEN_WINS} then 'проверенный'
        when in_history then 'участник'
        when coalesce(revenue, 0) > 0 and msp_since < date '{OLD_ENOUGH}' then 'новый, подтверждён'
        else 'новый'
    end as status,
    case
        when rnp_records > 0
            then 'числится в реестре недобросовестных поставщиков (' || rnp_laws || ', запись от '
                || strftime(rnp_last, '%d.%m.%Y') || ')'
        when coalesce(tax_debt, 0) > {DEBT_LIMIT}
            then 'налоговая задолженность ' || round(tax_debt / 1000)::bigint || ' тыс. руб. на 01.09.2026'
        when h_missing
            then 'юрлицо не найдено ни в реестре МСП, ни в отчётности ФНС за 2025 год'
        when in_history and wins >= {PROVEN_WINS}
            then 'побед: ' || wins || ' из ' || bids || ' участий за 2024–2025 годы, негативных сведений нет'
        when in_history
            then 'участий: ' || bids || ', побед: ' || wins || ' за 2024–2025 годы, негативных сведений нет'
        when coalesce(revenue, 0) > 0 and msp_since < date '{OLD_ENOUGH}'
            then 'в закупках не участвовал; в реестре МСП с ' || strftime(msp_since, '%Y') || ' года, сдаёт отчётность'
        else 'в закупках не участвовал; найден в реестре МСП, подтверждений деятельности мало'
    end as status_reason
from (
    select *, in_history and kind = 'ЮЛ' and raw_name is null as h_missing,
        -- 46 — опт; в 45 торговля автомобилями и запчастями, но 45.2 — ремонт, это услуги.
        okved_class = 46 or (okved_class = 45 and okved_main not like '45.2%') as is_wholesale
    from base
)
"""


def main() -> None:
    con = duckdb.connect(str(DB))
    con.execute(SQL)
    # Выгрузка в том же формате, что исходные файлы: CSV, UTF-8, разделитель «;».
    OUT.parent.mkdir(parents=True, exist_ok=True)
    con.execute(f"""
        copy (
            select inn, kind, name, region, place, in_history, bids, wins, status, status_reason,
                role, role_reason, role_source,
                okved_main, okved_main_name, array_to_string(okved_extra, ',') as okved_extra,
                msp_category, msp_since, headcount, revenue, expense, tax_debt, rnp_records, rnp_laws,
                array_to_string(sources, ' | ') as sources
            from companies order by in_history desc, bids desc, inn
        ) to '{OUT.as_posix()}' (header, delimiter ';', quote '"', force_quote (inn))
    """)
    print(f"выгрузка: {OUT.relative_to(ROOT)}")
    for title, sql in {
        "компаний": "select in_history, count(*) n, count(name) named, count(okved_main) with_okved, "
                    "count(revenue) with_finance, count(*) filter (rnp_records > 0) in_rnp, "
                    "count(*) filter (tax_debt > 100000) big_debt from companies group by all",
        "статусы": "select status, count(*) n, sum(bids) bids from companies group by all order by 2 desc",
        "роли": "select in_history, role, count(*) n from companies group by all order by 1, 3 desc",
        "новые компании: признаки достоверности":
            "select count(*) n, count(*) filter (revenue > 0) with_revenue, "
            "count(*) filter (headcount > 0) with_staff, count(*) filter (msp_since < date '2024-10-01') over_2y, "
            "count(*) filter (msp_category >= 2) small_or_medium, count(*) filter (len(licenses) > 0) licensed, "
            "count(*) filter (kind = 'ЮЛ') legal, "
            "count(*) filter (revenue > 0 and msp_since < date '2024-10-01' and coalesce(tax_debt, 0) <= 100000 "
            "and rnp_records = 0) solid from companies where not in_history",
        "поставщики из истории": "select count(*) n, count(name) named, count(okved_main) with_okved, "
            "round(100.0 * sum(bids) filter (name is not null) / sum(bids), 1) pct_bids_named, "
            "count(*) filter (rnp_records > 0) in_rnp, count(*) filter (tax_debt > 100000) big_debt "
            "from companies where in_history",
    }.items():
        print(f"\n{title}")
        cur = con.execute(sql)
        print("  " + " | ".join(d[0] for d in cur.description))
        for row in cur.fetchall():
            print("  " + " | ".join(str(v) for v in row))


if __name__ == "__main__":
    main()
