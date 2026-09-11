"""
منطق الكتالوج والسلة — دوال نقية (Pure functions)، ما بتحتاج شبكة ولا تلغرام إطلاقاً.
هيك منقدر نختبرها لحالها ونتأكد إنها ١٠٠٪ صحيحة قبل ما نوصلها لكود البوت.
"""
import json
from pathlib import Path
from typing import Optional


def load_catalog(path: Path) -> dict:
    """بتحمّل catalog.json وبتشيل مفتاح الملاحظة (_ملاحظة) منه."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.pop("_ملاحظة", None)
    return data


def get_categories(catalog: dict) -> list[str]:
    """أسماء الأقسام الرئيسية بترتيبها بالملف (دخان، معسل، قداحات، فيبات)."""
    return list(catalog.keys())


def get_category_emoji(catalog: dict, category: str) -> str:
    return catalog.get(category, {}).get("emoji", "")


def category_button_label(catalog: dict, category: str) -> str:
    """نص الزر متل ما بالدليل: 'الإيموجي مسافة اسم القسم' مثلاً '🚬 دخان'."""
    emoji = get_category_emoji(catalog, category)
    return f"{emoji} {category}".strip()


def get_types(catalog: dict, category: str) -> list[str]:
    return list(catalog.get(category, {}).get("types", {}).keys())


def get_variants(catalog: dict, category: str, type_: str) -> list[str]:
    """ممكن ترجع لائحة فاضية — يعني هالنوع ما إلو أصناف فرعية (متلاً 'حمراء')."""
    return list(catalog.get(category, {}).get("types", {}).get(type_, []))


def has_variants(catalog: dict, category: str, type_: str) -> bool:
    return len(get_variants(catalog, category, type_)) > 0


def get_units(catalog: dict, category: str) -> list[dict]:
    """كل وحدة عبارة عن {'name': ..., 'fixed': True/False}."""
    return list(catalog.get(category, {}).get("units", []))


def get_unit_by_name(catalog: dict, category: str, unit_name: str) -> Optional[dict]:
    for u in get_units(catalog, category):
        if u["name"] == unit_name:
            return u
    return None


def is_unit_fixed(catalog: dict, category: str, unit_name: str) -> bool:
    unit = get_unit_by_name(catalog, category, unit_name)
    return bool(unit and unit.get("fixed"))


# ---------------------------------------------------------------------------
# التعامل مع رقم العدد يلي الزبون بيكتبو (صندوق الكتابة، الخطوة هـ بالدليل)
# ---------------------------------------------------------------------------

def parse_count(text: str) -> Optional[int]:
    """
    بتحاول تحوّل نص الزبون لرقم صحيح موجب (١، ٢، ٣ عربي أو 1،2،3 إنجليزي).
    بترجع None إذا النص مش رقم صالح، منشان البوت يطلب من الزبون يعيد الكتابة.
    """
    if text is None:
        return None
    text = text.strip()
    if not text:
        return None
    # حوّل الأرقام العربية للإنجليزية
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    translated = "".join(
        str(arabic_digits.index(ch)) if ch in arabic_digits else ch for ch in text
    )
    if not translated.isdigit():
        return None
    value = int(translated)
    if value <= 0:
        return None
    return value


def format_quantity(unit_name: str, fixed: bool, count: Optional[int] = None) -> str:
    """
    بترجع نص الكمية النهائي يلي بينخزن بالسلة.
    - لو الوحدة ثابتة (متلاً 'نص كروز') → بترجع اسم الوحدة بس.
    - غير هيك → 'العدد + اسم الوحدة' متلاً '3 باكيت'.
    """
    if fixed:
        return unit_name
    if count is None:
        raise ValueError("لازم عدد (count) للوحدات غير الثابتة")
    return f"{count} {unit_name}"


# ---------------------------------------------------------------------------
# السلة: إضافة / تراجع / مسح / تنسيق
# ---------------------------------------------------------------------------

def format_cart_line(section: str, type_: str, variant: Optional[str], quantity: str) -> str:
    """
    سطر واحد بالسلة، بنفس شكل الدليل:
    '▫️ القسم – النوع – الصنف – الكمية'
    إذا ما في صنف فرعي (variant فاضي)، بيتحذف من السطر تلقائياً.
    """
    parts = [section, type_]
    if variant:
        parts.append(variant)
    parts.append(quantity)
    return "▫️ " + " – ".join(parts)


def format_added_summary(type_: str, variant: Optional[str], quantity: str) -> str:
    """نص 'ضفنالك: ...' يلي بيظهر فوق شاشة السلة — بدون اسم القسم."""
    parts = [type_]
    if variant:
        parts.append(variant)
    parts.append(quantity)
    return " – ".join(parts)


def add_to_cart(cart: list[str], line: str) -> tuple[list[str], list[str]]:
    """
    بترجع (سلة_جديدة، نسخة_احتياطية_قبل_الإضافة) — بالضبط متل ما بالدليل
    (cart و cart_backup).
    """
    backup = list(cart)
    new_cart = list(cart) + [line]
    return new_cart, backup


def undo_last(backup: list[str]) -> list[str]:
    """بترجع السلة لآخر نسخة احتياطية (تراجع عن آخر إضافة بس)."""
    return list(backup)


def clear_cart() -> tuple[list[str], list[str]]:
    return [], []


def format_cart_text(cart: list[str]) -> str:
    if not cart:
        return "(السلة لسا فاضية)"
    return "\n".join(cart)
