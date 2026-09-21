# -*- coding: utf-8 -*-
"""
حساب سعر السلة تلقائياً من الأسعار يلي حاططا التاجر (price_sheet + overrides) —
دالة نقية (Pure)، بدون أي اعتماد على مكتبة تلغرام، متل catalog_logic.py و
price_sheet_logic.py تماماً.

الفكرة: كل صنف بالكتالوج (catalog.json) — النوع (type) هو اسم البراند بالظبط،
والصنف (variant) هو اسم الصنف بالظبط متل ما هوي بملف price_sheet.json. هيك
منقدر نلاقي سعر أي سطر بالسلة رجوع بسهولة (برند + اسم صنف) بدون أي تخمين.

لكل وحدة (unit) بالكتالوج "multiplier" (مضاعِف) — مثلاً "🎁 كروز" = 1 (سعر
الصنف نفسه)، و"🥡 نص كروز" = 0.5 (نص السعر، وحدة ثابتة يعني العدد مش مهم).
لصناف المعسل/الفحم/الإكسسوارات/الاراكيل الإلكترونية، الحجم/الوزن مبيّن أصلاً
جوا اسم الصنف نفسه (متلاً "مزايا ماكس 250 غ")، فوحدتهن الوحيدة "🧮 عدد" =
مضاعِف 1 (يعني السعر × العدد بس، بلا أي تحويل وحدات إضافي).

لو صنف واحد بالسلة ما إلو سعر محدد بعد (سعر 0 أو مش موجود إطلاقاً بقائمة
التاجر)، price_cart() بترجع None بالكامل — منشان نرجع للمسار اليدوي (نبعت
لاستفسار التاجر) بدل ما نعرض سعر ناقص أو غلط للزبون.
"""
from typing import Optional

import catalog_logic as cl


def build_price_lookup(flat_items: list[dict]) -> dict[tuple[str, str], int]:
    """(برند، اسم الصنف) → فهرس الصنف بـ price_sheet (لالتقاط سعرو الحالي رجوع)."""
    return {(item["brand"], item["name"]): item["index"] for item in flat_items}


def price_cart_item(
    item: dict,
    catalog: dict,
    price_lookup: dict[tuple[str, str], int],
    prices: dict[int, int],
) -> Optional[int]:
    """
    بترجع سعر سطر واحد بالسلة (ل.س)، أو None لو ما قدرنا نحسبو (الصنف مش موجود
    بقائمة أسعار التاجر أصلاً، أو موجود بس بلا سعر محدد لهلق).
    """
    variant = item.get("variant")
    key = (item.get("type"), variant if variant is not None else item.get("type"))
    idx = price_lookup.get(key)
    if idx is None:
        return None
    base_price = prices.get(idx)
    if not base_price:
        return None

    unit = cl.get_unit_by_name(
        catalog, item.get("category"), item.get("unit_name"), item.get("type"), variant
    )
    multiplier = (unit or {}).get("multiplier", 1)

    if item.get("unit_fixed"):
        return int(round(base_price * multiplier))

    count = item.get("count") or 1
    return int(round(base_price * multiplier * count))


def price_cart(
    cart: list[dict],
    catalog: dict,
    price_lookup: dict[tuple[str, str], int],
    prices: dict[int, int],
) -> Optional[tuple[list[int], int]]:
    """
    بترجع (أسعار كل سطر بالترتيب، المجموع الكلي) لو قدرنا نحسب سعر كل صنف
    بالسلة بلا استثناء، أو None لو صنف واحد عالأقل ما قدرنا نحسبلو سعر (بهالحالة
    لازم نرجع للمسار اليدوي — استفسار عادي للتاجر).
    """
    line_prices: list[int] = []
    for item in cart:
        price = price_cart_item(item, catalog, price_lookup, prices)
        if price is None:
            return None
        line_prices.append(price)
    return line_prices, sum(line_prices)
