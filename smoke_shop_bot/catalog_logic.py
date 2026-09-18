"""
منطق الكتالوج والسلة — دوال نقية (Pure functions)، ما بتحتاج شبكة ولا تلغرام إطلاقاً.
هيك منقدر نختبرها لحالها ونتأكد إنها ١٠٠٪ صحيحة قبل ما نوصلها لكود البوت.
"""
import json
import re
from pathlib import Path
from typing import Optional


def load_catalog(path: Path) -> dict:
    """بتحمّل catalog.json وبتشيل مفتاح الملاحظة (_ملاحظة) منه."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.pop("_ملاحظة", None)
    return data


def get_categories(catalog: dict) -> list[str]:
    """أسماء الأقسام الرئيسية بترتيبها بالملف (دخان، معسل، فحم، إكسسوارات، اراكيل الكترونية)."""
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


def get_units(catalog: dict, category: str, type_: Optional[str] = None) -> list[dict]:
    """
    كل وحدة عبارة عن {'name': ..., 'fixed': True/False}.
    لو النوع (type_) إلو وحدات خاصة فيه (مسجلة بقسم "type_units" جوا القسم بالكتالوج)،
    بترجع هديك بدل وحدات القسم العامة — هيك منقدر نعمل مثلاً براند معسل ما إلو "نص كيلو".
    لو type_ ما انبعت، أو ما إلو وحدات خاصة، بترجع وحدات القسم العامة (units) زي العادة.
    """
    category_data = catalog.get(category, {})
    if type_ is not None:
        type_units = category_data.get("type_units", {})
        if type_ in type_units:
            return list(type_units[type_])
    return list(category_data.get("units", []))


def get_unit_by_name(catalog: dict, category: str, unit_name: str, type_: Optional[str] = None) -> Optional[dict]:
    for u in get_units(catalog, category, type_):
        if u["name"] == unit_name:
            return u
    return None


def is_unit_fixed(catalog: dict, category: str, unit_name: str, type_: Optional[str] = None) -> bool:
    unit = get_unit_by_name(catalog, category, unit_name, type_)
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


def extract_amount(text: str) -> Optional[int]:
    """
    بتحاول تلاقي أول رقم واضح جوا نص (رد التاجر بالسعر مثلاً، حتى لو مكتوب وسط
    كلام تاني زي '70000 ل.س' أو '٧٠،٠٠٠ ليرة'). بتتجاهل فواصل الآلاف (, أو .)
    وبتحوّل الأرقام العربية لإنجليزية. بترجع None إذا ما لقت رقم صالح بالنص.
    """
    if not text:
        return None
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    translated = "".join(
        str(arabic_digits.index(ch)) if ch in arabic_digits else ch for ch in text
    )
    match = re.search(r"\d[\d,.]*\d|\d", translated)
    if not match:
        return None
    digits_only = re.sub(r"[,.]", "", match.group(0))
    if not digits_only.isdigit():
        return None
    value = int(digits_only)
    return value if value > 0 else None


def split_deposit_amount(total_amount: int) -> tuple[int, int]:
    """بترجع (مبلغ الرعبون، الباقي) — نص المبلغ بالضبط لكل وحدة، ومجموعهن = المبلغ الإجمالي تماماً."""
    deposit = total_amount // 2
    remaining = total_amount - deposit
    return deposit, remaining


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

def format_cart_line(
    section: str,
    type_: str,
    variant: Optional[str],
    unit_name: str,
    unit_fixed: bool,
    count: Optional[int],
    quantity: Optional[str] = None,
) -> dict:
    """
    سطر واحد بالسلة — بس هلق بشكل بنية (dict) مش نص بس، منشان نقدر نحسب سعرو
    تلقائياً بعدين (شوف cart_pricing.py) بدل ما نعيد تفكيك النص المنسق.

    - "display": نفس النص المنسق القديم بالضبط '▫️ القسم – النوع – [الصنف –] الكمية'
      (لعرضو بالسلة/الفاتورة متل ما كان دايماً).
    - باقي الحقول: القسم/النوع/الصنف/الوحدة/العدد الخام — منشان حساب السعر
      وأي استخدام تاني بالمستقبل، بدون ما نحتاج نفكّك نص "display" أبداً.

    إذا ما انبعت quantity (النص المنسق)، منبنيه تلقائياً من unit_name/unit_fixed/count.
    """
    if quantity is None:
        quantity = format_quantity(unit_name, unit_fixed, count)
    parts = [section, type_]
    if variant:
        parts.append(variant)
    parts.append(quantity)
    display = "▫️ " + " – ".join(parts)
    return {
        "display": display,
        "category": section,
        "type": type_,
        "variant": variant,
        "unit_name": unit_name,
        "unit_fixed": unit_fixed,
        "count": count,
    }


def format_added_summary(type_: str, variant: Optional[str], quantity: str) -> str:
    """نص 'ضفنالك: ...' يلي بيظهر فوق شاشة السلة — بدون اسم القسم."""
    parts = [type_]
    if variant:
        parts.append(variant)
    parts.append(quantity)
    return " – ".join(parts)


def add_to_cart(cart: list[dict], line: dict) -> tuple[list[dict], list[dict]]:
    """
    بترجع (سلة_جديدة، نسخة_احتياطية_قبل_الإضافة) — بالضبط متل ما بالدليل
    (cart و cart_backup). "cart" هلق لستة بُنى (dicts) من format_cart_line،
    مش نصوص مباشرة.
    """
    backup = list(cart)
    new_cart = list(cart) + [line]
    return new_cart, backup


def undo_last(backup: list[dict]) -> list[dict]:
    """بترجع السلة لآخر نسخة احتياطية (تراجع عن آخر إضافة بس)."""
    return list(backup)


def clear_cart() -> tuple[list[dict], list[dict]]:
    return [], []


def _line_display(item) -> str:
    """بيرجع نص السطر المنسق سواء كان الصنف بُنية (dict) جديدة أو نص (str)
    قديم — منشان التوافق مع أي بيانات طلبات قديمة محفوظة من قبل هالتحديث."""
    if isinstance(item, dict):
        return item.get("display", "")
    return str(item)


def format_cart_text(cart: list) -> str:
    if not cart:
        return "(السلة لسا فاضية)"
    return "\n".join(_line_display(item) for item in cart)


def format_priced_cart_text(cart: list[dict], line_prices: list[int]) -> str:
    """متل format_cart_text بس بيضيف سعر كل سطر جنبو — لعرض الفاتورة المحسوبة
    تلقائياً للزبون والتاجر سوا."""
    if not cart:
        return "(السلة لسا فاضية)"
    lines = [
        f"{_line_display(item)} — {price} ل.س" for item, price in zip(cart, line_prices)
    ]
    return "\n".join(lines)
