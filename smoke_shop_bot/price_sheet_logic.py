# -*- coding: utf-8 -*-
"""
منطق قائمة الأسعار الكاملة (كل الماركات/الأصناف من ملف Excel التاجر، محفوظين
بـ data/price_sheet.json) — مفصول لحاله ومُختبر بدون أي اعتماد على مكتبة تلغرام،
تماماً متل catalog_logic.py.

الفكرة: كل صنف إله "فهرس" (index) ثابت حسب ترتيبه بالملف. التاجر بيقدر يحدث
سعر أي صنف من جوا تلغرام (عبر أمر /setprices) بس بيبعت "رقم_الصنف سعر_جديد"،
بدل ما يحتاج يرفع ملفات لگيت هب في كل مرة. التعديلات (overrides) بتنحفظ
برسالة مثبتة بشات التاجر (شوف telegram_state.py) منشان ما تضيع لما Render
يعيد تشغيل السيرفر من الخمول.
"""
import json
import re
from pathlib import Path
from typing import Optional

# هامش أمان تحت حد تلغرام لطول الرسالة الواحدة (٤٠٩٦ محرف) — منقسم أي عرض أطول
# منو لعدة رسائل متتالية.
MAX_MESSAGE_CHARS = 3500

_UPDATE_LINE_PATTERN = re.compile(r"^\d+\s+\d+$")

# تحديث سعر الدولار: "رقم_الصنف $سعر_جديد" — لازم علامة $ قبل السعر منشان ما
# يتلخبط مع تحديث سعر الليرة فوق (يلي رقمين بس بلا أي علامة). لو كتبنا "213 11"
# بلا $، ما منعرف إذا قصدها 11 ل.س (غير منطقي بس تقنياً ممكن) أو 11$ — فالـ $
# هو الفيصل الوحيد الموثوق.
_USD_UPDATE_LINE_PATTERN = re.compile(r"^\d+\s+\$\d+(\.\d+)?$")


# ---------------------------------------------------------------------------
# تحميل البنية الثابتة (ماركات + أصناف + سعر افتراضي) من data/price_sheet.json
# ---------------------------------------------------------------------------

def load_price_sheet(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_usd_prices(path: Path) -> dict[int, float]:
    """بترجع {index: سعر بالدولار} من data/usd_prices.json. لو الملف مش موجود
    بعد (لسا ما انحط أي سعر دولار)، بترجع قاموس فاضي بدل ما ترمي خطأ."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError:
        return {}
    return {int(idx): price for idx, price in raw.items()}


def load_usd_rate(path: Path) -> Optional[float]:
    """بترجع سعر تصريف اليوم (ليرة مقابل ١ دولار) من data/usd_rate.json، أو None
    لو لسا ما انحط (الملف مش موجود، أو فاضي/تالف)."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    rate = raw.get("rate") if isinstance(raw, dict) else None
    if isinstance(rate, (int, float)) and rate > 0:
        return float(rate)
    return None


_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩٫٬،", "0123456789.,,")


def parse_usd_rate(text: str) -> Optional[float]:
    """بتحوّل نص زي "15000" أو "15,000" أو "١٥٠٠٠" أو "14950.5" لرقم موجب، أو None
    إذا مش رقم صالح (فاضي، صفر، سالب، أو فيه حروف)."""
    cleaned = (text or "").strip().translate(_ARABIC_DIGITS).replace(",", "").replace(" ", "")
    if not re.fullmatch(r"\d+(\.\d+)?", cleaned):
        return None
    value = float(cleaned)
    return value if value > 0 else None


def flatten_items(groups: list[dict]) -> list[dict]:
    """بترجع لستة مسطحة بترتيب الملف: كل عنصر {"index", "brand", "name", "default_price"}."""
    flat = []
    idx = 0
    for group in groups:
        brand = group.get("brand")
        for item in group.get("items", []):
            flat.append(
                {
                    "index": idx,
                    "brand": brand,
                    "name": item["name"],
                    "default_price": item.get("default_price", 0),
                }
            )
            idx += 1
    return flat


# ---------------------------------------------------------------------------
# دمج السعر الافتراضي مع أي تعديل حفظه التاجر (overrides) — وترميزها بشكل مضغوط
# منشان تنحفظ برسالة تلغرام مثبتة (حد ٤٠٩٦ محرف).
# ---------------------------------------------------------------------------

def effective_prices(flat_items: list[dict], overrides: dict[int, int]) -> dict[int, int]:
    return {item["index"]: overrides.get(item["index"], item["default_price"]) for item in flat_items}


def encode_prices_compact(prices: dict[int, int]) -> str:
    if not prices:
        return ""
    return ",".join(f"{idx}:{price}" for idx, price in sorted(prices.items()))


def decode_prices_compact(text: Optional[str]) -> dict[int, int]:
    result: dict[int, int] = {}
    if not text:
        return result
    for part in text.split(","):
        part = part.strip()
        if not part or ":" not in part:
            continue
        idx_s, price_s = part.split(":", 1)
        try:
            result[int(idx_s)] = int(price_s)
        except ValueError:
            continue
    return result


# ---------------------------------------------------------------------------
# فهم رسالة التاجر لتحديث الأسعار: سطر لكل صنف "رقم_الصنف سعر_جديد"
# ---------------------------------------------------------------------------

def looks_like_price_update(text: str) -> bool:
    """بيتأكد إنو كل سطر بالرسالة شكلو "رقم رقم" — منشان نعرف نميز رسالة تحديث
    أسعار عن أي حكي عادي تاني بشات التاجر، بدون ما ناخد قرار خاطئ."""
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if not lines:
        return False
    return all(_UPDATE_LINE_PATTERN.match(ln) for ln in lines)


def parse_price_update_lines(
    text: str, flat_items: list[dict]
) -> tuple[dict[int, int], list[str]]:
    """بترجع (updates, errors). updates: {index: new_price} للأسطر السليمة بس.
    errors: رسائل توضيح لأي سطر رقم الصنف فيه مش موجود بالقائمة."""
    updates: dict[int, int] = {}
    errors: list[str] = []
    by_index = {item["index"]: item for item in flat_items}

    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    for line in lines:
        idx_s, price_s = line.split()
        idx, price = int(idx_s), int(price_s)
        if idx not in by_index:
            errors.append(f"⚠️ رقم الصنف {idx} مش موجود بالقائمة — تجاهلته.")
            continue
        updates[idx] = price

    return updates, errors


# ---------------------------------------------------------------------------
# فهم رسالة التاجرة لتحديث أسعار الدولار (/usdprices): سطر لكل صنف
# "رقم_الصنف $سعر_جديد" — نفس فكرة looks_like_price_update/parse_price_update_lines
# فوق تماماً، بس بالدولار (يسمح بفاصلة عشرية) وبعلامة $ إلزامية قبل السعر.
# ---------------------------------------------------------------------------

def looks_like_usd_price_update(text: str) -> bool:
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if not lines:
        return False
    return all(_USD_UPDATE_LINE_PATTERN.match(ln) for ln in lines)


def parse_usd_price_update_lines(
    text: str, flat_items: list[dict]
) -> tuple[dict[int, float], list[str]]:
    """بترجع (updates, errors). updates: {index: سعر دولار جديد} للأسطر السليمة
    بس. errors: رسائل توضيح لأي سطر رقم الصنف فيه مش موجود بالقائمة."""
    updates: dict[int, float] = {}
    errors: list[str] = []
    by_index = {item["index"]: item for item in flat_items}

    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    for line in lines:
        idx_s, price_s = line.split()
        idx = int(idx_s)
        price = float(price_s.lstrip("$"))
        if idx not in by_index:
            errors.append(f"⚠️ رقم الصنف {idx} مش موجود بالقائمة — تجاهلته.")
            continue
        updates[idx] = price

    return updates, errors


# ---------------------------------------------------------------------------
# ترتيب العرض: تجميع الأصناف حسب البرند (أول ظهور لهالبرند بالملف) — منشان
# لو نفس اسم البرند موجود بأكتر من مجموعة متفرقة بـ price_sheet.json (صار هيك
# لما إضافات لاحقة ضلت تلحق بآخر الملف بدل ما تندمج بمكان البرند الأصلي، منشان
# ما نحرك مواقع/أرقام (index) أصناف موجودة أصلاً وما نخرب أسعار محفوظة سابقاً
# عبر /setprices)، ما يطلعلنا عنوان البرند مكرر أكتر من مرة بالقائمة المعروضة
# للتاجر أو للزبون. رقم الصنف (index) نفسه ما بيتغير إطلاقاً — بس ترتيب العرض
# هو يلي بينجمع.
# ---------------------------------------------------------------------------

def _grouped_by_brand(flat_items: list[dict]) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    for item in flat_items:
        groups.setdefault(item["brand"], []).append(item)
    ordered: list[dict] = []
    for items in groups.values():
        ordered.extend(items)
    return ordered


# ---------------------------------------------------------------------------
# نص القائمة المرجعية للتاجر (بعد /setprices) — مقسومة لعدة رسائل لو لزم
# ---------------------------------------------------------------------------

def format_admin_reference(flat_items: list[dict], prices: dict[int, int]) -> list[str]:
    chunks: list[str] = []
    current = "📒 قائمة الأصناف الحالية (رقم الصنف — السعر):\n"
    current_brand = None

    for item in _grouped_by_brand(flat_items):
        idx = item["index"]
        price = prices.get(idx, item["default_price"])
        price_text = f"{price} ل.س" if price else "⚠️ ما انحط سعر بعد"
        prefix = f"\n🔸 {item['brand']}\n" if item["brand"] != current_brand else ""
        current_brand = item["brand"]
        line = f"{prefix}{idx}. {item['name']} — {price_text}\n"

        if len(current) + len(line) > MAX_MESSAGE_CHARS:
            chunks.append(current.rstrip())
            current = line
        else:
            current += line

    if current.strip():
        chunks.append(current.rstrip())
    return chunks


# ---------------------------------------------------------------------------
# نشرة الأسعار بالدولار — للتاجر بس (مش للزبون ولا للبث اليومي). منبنية من
# نفس أرقام الأصناف (index) تبع price_sheet.json، بس بسعر منفصل كلياً عن
# الأسعار بالليرة (usd_prices: {index: سعر بالدولار}). بتورّي كل الأصناف
# (حتى يلي لسا بلا سعر دولار) منشان التاجرة تشوف وين وصلت بتعبئة الفورم،
# تماماً متل format_admin_reference مع السعر بالليرة.
# ---------------------------------------------------------------------------

def format_usd_admin_reference(
    flat_items: list[dict],
    usd_prices: dict[int, float],
    category_of_brand: Optional[dict[str, str]] = None,
) -> list[str]:
    chunks: list[str] = []
    header = "💵 نشرة الأسعار بالدولار (خاصة فيكِ بس):\n"
    current = header
    current_category = None
    current_brand = None

    def _append(line: str) -> None:
        nonlocal current
        if len(current) + len(line) > MAX_MESSAGE_CHARS:
            chunks.append(current.rstrip())
            current = line
        else:
            current += line

    for item in _grouped_by_brand(flat_items):
        idx = item["index"]
        price = usd_prices.get(idx)
        price_text = f"${price:,.2f}" if price else "⚠️ ما انحط سعر دولار بعد"
        brand = item["brand"]

        category = (category_of_brand or {}).get(brand)
        if category is not None and category != current_category:
            _append(f"\n{category}\n{'─' * 14}\n")
            current_category = category
            current_brand = None

        if brand != current_brand:
            _append(f"🔸 {brand}\n")
            current_brand = brand

        _append(f"   {idx}. {item['name']} — {price_text}\n")

    if current.strip():
        chunks.append(current.rstrip())
    return chunks


# ---------------------------------------------------------------------------
# نص "أسعار اليوم" يلي بيوصل للزبون (/prices والبث اليومي) — مقسوم لعدة رسائل
# ---------------------------------------------------------------------------

def format_customer_prices(
    flat_items: list[dict],
    prices: dict[int, int],
    shop_name: str,
    date_str: str,
    category_of_brand: Optional[dict[str, str]] = None,
) -> list[str]:
    """
    category_of_brand (اختياري): {اسم البرند: "إيموجي اسم القسم"} — لو انبعت،
    القائمة بتنظم بشكل هرمي (قسم ← برند ← صنف) منشان تكون واضحة ومرتبة للزبون
    (بدل ما تطلع كل البرندات ورا بعض بلا أي تقسيم أعلى منها). لو ما انبعت،
    بترجع بس تقسيم برند ← صنف متل السابق.
    """
    header = f"📋 أسعار اليوم — {shop_name}\n📅 محدثة بتاريخ: {date_str}\n"
    footer = (
        "⚠️ الأسعار قابلة للتغيير بدون إشعار مسبق. للتأكد النهائي، اطلب واستعمل "
        "زر \"💰 استعلام عن السعر\" جوا البوت."
    )

    chunks: list[str] = []
    current = header
    current_category = None
    current_brand = None
    any_item = False

    def _append(line: str) -> None:
        nonlocal current
        if len(current) + len(line) > MAX_MESSAGE_CHARS:
            chunks.append(current.rstrip())
            current = line
        else:
            current += line

    for item in _grouped_by_brand(flat_items):
        idx = item["index"]
        price = prices.get(idx, item["default_price"])
        if not price:
            continue  # صنف بلا سعر محدد بعد — ما منعرضه للزبون
        any_item = True
        brand = item["brand"]

        category = (category_of_brand or {}).get(brand)
        if category is not None and category != current_category:
            _append(f"\n{category}\n{'─' * 14}\n")
            current_category = category
            current_brand = None  # منشان يطلع عنوان البرند من جديد تحت القسم الجديد

        if brand != current_brand:
            _append(f"🔸 {brand}\n")
            current_brand = brand

        _append(f"   • {item['name']} — {price} ل.س\n")

    if not any_item:
        return [header.rstrip() + "\n\nلسا ما في أسعار مضافة."]

    if current.strip():
        chunks.append(current.rstrip())

    chunks[-1] = chunks[-1] + "\n\n" + footer
    return chunks
