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
import config
import price_sheet_logic as ps

GROUPS = ps.load_price_sheet(config.PRICE_SHEET_PATH)
FLAT_ITEMS = ps.flatten_items(GROUPS)

overrides: dict[int, int] = {}


def set_overrides(new_overrides: dict[int, int]) -> None:
    overrides.clear()
    overrides.update(new_overrides)


def current_prices() -> dict[int, int]:
    return ps.effective_prices(FLAT_ITEMS, overrides)
