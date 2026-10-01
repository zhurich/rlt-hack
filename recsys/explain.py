"""Объяснения рекомендаций человеческим языком.

На входе — позиция выдачи (вклады факторов и сырые числа) и карточка компании из таблицы
companies. На выходе — список причин и разбивка балла по факторам в процентах.
"""
from .recommender import MOD_WEIGHTS

FACTOR_LABELS = {
    "text": "Похожие закупки",
    "okpd9": "Код ОКПД2", "okpd6": "Код ОКПД2", "okpd4": "Код ОКПД2", "okpd2": "Код ОКПД2",
    "customer": "История с заказчиком",
    "price": "Ценовой диапазон",
    "spec": "Специализация",
    "source": "Площадка",
    "smp": "Опыт закупок для СМП",
    "region": "Регион",
}
NEW_FACTOR_LABELS = {
    "affinity": "Профиль деятельности (ОКВЭД)", "affinity_class": "Профиль деятельности (ОКВЭД)",
    "okved_main": "ОКВЭД совпадает с кодом закупки", "okved_extra": "ОКВЭД совпадает с кодом закупки",
    "text": "Описание деятельности",
}
OKPD_LEVELS = (
    ("okpd9", "по тому же коду ОКПД2"),
    ("okpd6", "в той же категории ОКПД2"),
    ("okpd4", "в той же группе ОКПД2"),
    ("okpd2", "в том же классе ОКПД2"),
)
MSP_CATEGORY = {1: "микропредприятие", 2: "малое предприятие", 3: "среднее предприятие"}


def plural(n: int, one: str, few: str, many: str) -> str:
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        word = one
    elif 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        word = few
    else:
        word = many
    return f"{n:,} {word}".replace(",", " ")


def money(x: float) -> str:
    if x >= 1e9:
        return f"{x / 1e9:.1f} млрд руб.".replace(".", ",", 1)
    if x >= 1e6:
        return f"{x / 1e6:.1f} млн руб.".replace(".", ",", 1)
    if x >= 1e3:
        return f"{x / 1e3:.0f} тыс. руб."
    return f"{x:.0f} руб."


def factors(parts: dict[str, float], labels: dict[str, str] = FACTOR_LABELS) -> dict:
    """Разбивка балла.

    relevance — из чего складывается релевантность, доли в процентах (в сумме 100).
    boosts — на сколько процентов релевантность увеличена каждым множителем.
    Множители показаны отдельно: они почти одинаковы у всех кандидатов и в общей сумме
    заслоняли бы настоящие причины.
    """
    rel = {k: v for k, v in parts.items() if k not in MOD_WEIGHTS}
    total = sum(rel.values()) or 1.0
    grouped: dict[str, float] = {}
    for key, value in rel.items():
        grouped[labels.get(key, key)] = grouped.get(labels.get(key, key), 0.0) + value
    relevance = [{"label": k, "share": round(100 * v / total)} for k, v in grouped.items()]
    boosts = [{"label": labels.get(k, k), "pct": round(100 * v / total)}
              for k, v in parts.items() if k in MOD_WEIGHTS]
    return {
        "relevance": sorted((f for f in relevance if f["share"] > 0), key=lambda f: -f["share"]),
        "boosts": sorted((b for b in boosts if b["pct"] > 0), key=lambda b: -b["pct"]),
    }


def wins_note(wins: int) -> str:
    return f", из них {plural(wins, 'победа', 'победы', 'побед')}" if wins else ""


def explain_known(item: dict, lot: dict, similar_subjects: dict[int, str]) -> list[str]:
    """Причины для поставщика из истории закупок."""
    facts, mods = item["facts"], item["mods"]
    reasons = []

    if facts.get("text_lots"):
        text = f"Участвовал в {plural(facts['text_lots'], 'закупке', 'закупках', 'закупках')} с похожим предметом"
        if item["similar_lots"]:
            best = item["similar_lots"][0]
            subject = similar_subjects.get(best["lot_id"])
            if subject:
                won = "победил" if best["won"] else "участвовал"
                text += f", например «{subject[:110]}» ({won})"
        reasons.append(text)

    for key, where in OKPD_LEVELS:
        bids = facts.get(f"{key}_bids")
        if bids:
            reasons.append(f"{plural(bids, 'заявка', 'заявки', 'заявок').capitalize()} {where}"
                           f"{wins_note(facts.get(f'{key}_wins', 0))}")
            break

    if facts.get("customer_bids"):
        n = facts["customer_bids"]
        reasons.append(f"Уже работал с этим заказчиком: {plural(n, 'закупка', 'закупки', 'закупок')}"
                       f"{wins_note(facts.get('customer_wins', 0))}")

    if mods.get("spec", 0) >= 0.3:
        reasons.append(f"Специализируется на этой категории: {round(100 * mods['spec'])}% его заявок — в том же классе ОКПД2")
    elif item["total_bids"] >= 1000 and mods.get("spec", 0) < 0.1:
        reasons.append(f"Универсальный участник: {plural(item['total_bids'], 'заявка', 'заявки', 'заявок')} в самых "
                       f"разных категориях, на эту приходится {max(round(100 * mods.get('spec', 0)), 1)}%")

    if item.get("typical_price") and lot.get("price"):
        fit = mods.get("price", 0)
        typical = money(item["typical_price"])
        if fit >= 0.6:
            reasons.append(f"Цена закупки в привычном для него диапазоне (типичная — около {typical})")
        elif fit < 0.15:
            reasons.append(f"Цена закупки нетипична для него (обычно около {typical})")

    if lot.get("source") and "source" in mods:
        share = round(100 * mods["source"])
        if share >= 70:
            reasons.append(f"Работает в основном на этой площадке ({share}% заявок — {lot['source']})")
        elif share <= 10:
            reasons.append(f"На этой площадке почти не участвует ({share}% заявок — {lot['source']})")

    if lot.get("is_smp") and mods.get("smp"):
        reasons.append("Побеждал в закупках для субъектов малого предпринимательства")
    return reasons


def explain_new(item: dict, card: dict, codes: dict[str, float]) -> list[str]:
    """Причины для новой компании из реестров."""
    raw = item["raw"]
    reasons = []
    okved = f"{card['okved_main']} «{card['okved_main_name']}»"
    group = max(codes, key=codes.get)[:5] if codes else None

    if raw.get("okved_main"):
        reasons.append(f"Основной ОКВЭД {okved} совпадает с группой ОКПД2 закупки")
    elif raw.get("affinity") and group:
        share = str(round(100 * raw["affinity"], 1)).replace(".", ",")
        reasons.append(f"Основной ОКВЭД {okved}: у поставщиков с таким ОКВЭД {share}% заявок — "
                       f"в группе ОКПД2 {group}")
    else:
        reasons.append(f"Основной ОКВЭД {okved}")
    if raw.get("okved_extra") and not raw.get("okved_main"):
        reasons.append("Среди дополнительных ОКВЭД есть совпадающий с группой ОКПД2 закупки")
    if raw.get("text", 0) >= 0.15:
        reasons.append("Описание деятельности близко к предмету закупки")

    proof = []
    if card.get("revenue"):
        proof.append(f"выручка за 2025 год — {money(card['revenue'])}")
    if card.get("headcount"):
        proof.append(plural(card["headcount"], "работник", "работника", "работников"))
    if card.get("msp_since"):
        proof.append(f"в реестре МСП с {card['msp_since'].year} года"
                     + (f" ({MSP_CATEGORY[card['msp_category']]})" if card.get("msp_category") in MSP_CATEGORY else ""))
    if card.get("licenses"):
        proof.append(f"есть лицензии ({len(card['licenses'])})")
    if proof:
        reasons.append("Достоверность: " + ", ".join(proof))
    return reasons
