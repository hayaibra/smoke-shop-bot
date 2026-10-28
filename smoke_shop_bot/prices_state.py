# -*- coding: utf-8 -*-
"""
حالة الأسعار أثناء التشغيل (runtime) — مشتركة بين handlers.py (تحديث الأسعار عبر
/setprices) و broadcast.py (البث اليومي)، منشان الاتنين يشوفوا نفس آخر تعديل،
بدون ما نخلي وحدة تستورد التانية (تجنباً لأي import دائري).

GROUPS/FLAT_ITEMS: البنية الثابتة (ماركات + أصناف + سعر افتراضي) من data/price_sheet.json
— بتتحمل مرة وحدة وقت تشغيل البوت، متل CATALOG بـ handlers.py بالضبط.

overrides: أي تعديل سعر حفظه التاجر لاحقاً عبر تلغرام — بيتعبى وقت تشغيل البوت من
الرسالة المثبتة بشات التاجر (شوف telegram_state.load_state_from_telegram)، وبيتحدث
مباشرة كل ما التاجر يبعت تحديث سعر جديد.
"""
import catalog_logic as cl
import config
import price_sheet_logic as ps

GROUPS = ps.load_price_sheet(config.PRICE_SHEET_PATH)
FLAT_ITEMS = ps.flatten_items(GROUPS)

overrides: dict[int, int] = {}

# نشرة الأسعار بالدولار (/usdprices — للتاجرة بس): أسعار منفصلة كلياً عن
# overrides فوق (يلي بالليرة)، محفوظة بملف عادي (data/usd_prices.json) مش
# برسالة مثبتة متل أسعار الليرة — لأنو هالأسعار منحدّثها نحن (عبر ملف إكسل
# التاجرة) مش عبر تعديل مباشر جوا تلغرام، فمافي داعي لآلية المزامنة
# والاستعادة من الرسالة المثبتة. نفس أرقام الفهرس (index) تبع FLAT_ITEMS.
USD_PRICES_PATH = config.PRICE_SHEET_PATH.parent / "usd_prices.json"
USD_PRICES: dict[int, float] = ps.load_usd_prices(USD_PRICES_PATH)

# سعر تصريف اليوم (ليرة مقابل ١ دولار) — بيحطو التاجرة بأمر /usdrate، ومحفوظ
# بشكل دائم عبر GitHub (data/usd_rate.json) بنفس آلية أسعار الدولار فوق.
# قاموس بقيمة وحدة (مش متغير عادي) منشان handlers.py يعدّل عليه مباشرة.
USD_RATE_PATH = config.PRICE_SHEET_PATH.parent / "usd_rate.json"
USD_RATE: dict[str, "float | None"] = {"rate": ps.load_usd_rate(USD_RATE_PATH)}

# {اسم البرند: "إيموجي اسم القسم"} (متلاً "ماستر" → "🚬 دخان") — مبني من نفس
# data/catalog.json يلي بيستخدمه مسار الطلب، منشان قائمة "/prices" للزبون تنعرض
# منظمة هرمياً (قسم ← برند ← صنف) بدل ما تطلع كل البرندات ورا بعض بلا تقسيم.
_CATALOG_FOR_CATEGORIES = cl.load_catalog(config.CATALOG_PATH)
CATEGORY_OF_BRAND: dict[str, str] = {
    brand: cl.category_button_label(_CATALOG_FOR_CATEGORIES, category)
    for category in cl.get_categories(_CATALOG_FOR_CATEGORIES)
    for brand in cl.get_types(_CATALOG_FOR_CATEGORIES, category)
}

# (برند، اسم) لكل صنف موجود فعلياً بالكتالوج هلق (قابل للاختيار عبر البوت). لما
# التاجرة بتحذف صنف (أو ماركة كاملة) من الكتالوج، منسيبو هو نفسه بمكانه بملف
# price_sheet.json (بلا حذف/تحريك) منشان ترقيم باقي الأصناف ما يتأثر — بس هيك
# لازم نصفّيه من أي قائمة أسعار بتوصل الزبون (وإلا ضل يظهر إلها سعر بالنشرة
# اليومية أو "/prices" رغم إنه محذوف وما منقدر نبيعه إطلاقاً عبر البوت). شوف
# visible_flat_items() تحت.
_CATALOG_VARIANT_KEYS = {
    (type_, variant)
    for category in cl.get_categories(_CATALOG_FOR_CATEGORIES)
    for type_ in cl.get_types(_CATALOG_FOR_CATEGORIES, category)
    for variant in cl.get_variants(_CATALOG_FOR_CATEGORIES, category, type_)
}


def set_overrides(new_overrides: dict[int, int]) -> None:
    overrides.clear()
    overrides.update(new_overrides)


def current_prices() -> dict[int, int]:
    """الأسعار بالليرة يلي بتنعرض للزبون وبتنحسب فيها السلة: السعر الافتراضي
    (أو تعديل /setprices) — ولأي صنف إلو سعر دولار بيتحسب دولار × سعر التصريف
    (/usdrate) مقرّب لأقرب ١٠، وبيكسب على سعر الليرة. بنحسبهم وقت الطلب (مش
    مخزّنين) منشان ما نتخطى حد حجم الرسالة المثبتة بتلغرام."""
    return ps.apply_usd_rate(ps.effective_prices(FLAT_ITEMS, overrides), USD_PRICES, USD_RATE["rate"])


def visible_flat_items() -> list[dict]:
    """FLAT_ITEMS بس الأصناف يلي لسا موجودة فعلياً بالكتالوج (يعني مش محذوفة) —
    هاد يلي لازم يستخدم لأي قائمة أسعار بتوصل الزبون ("/prices" والنشرة
    اليومية)، منشان صنف محذوف ما يضل يظهر إلها سعر وكأنو لسا للبيع. القائمة
    المرجعية للتاجر (/setprices) لسا بتستخدم FLAT_ITEMS الكاملة (بكل الأرقام)،
    منشان تبقى مرجع تقني دقيق لكل رقم صنف بالملف."""
    return [item for item in FLAT_ITEMS if (item["brand"], item["name"]) in _CATALOG_VARIANT_KEYS]
