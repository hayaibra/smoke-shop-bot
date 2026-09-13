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


# ---------------------------------------------------------------------------
# تحميل البنية الثابتة (ماركات + أصناف + سعر افتراضي) من data/price_sheet.json
# ---------------------------------------------------------------------------

def load_price_sheet(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


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
# نص القائمة المرجعية للتاجر (بعد /setprices) — مقسومة لعدة رسائل لو لزم
# ---------------------------------------------------------------------------

def format_admin_reference(flat_items: list[dict], prices: dict[int, int]) -> list[str]:
    chunks: list[str] = []
    current = "📒 قائمة الأصناف الحالية (رقم الصنف — السعر):\n"
    current_brand = None

    for item in flat_items:
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
# نص "أسعار اليوم" يلي بيوصل للزبون (/prices والبث اليومي) — مقسوم لعدة رسائل
# ---------------------------------------------------------------------------

def format_customer_prices(
    flat_items: list[dict], prices: dict[int, int], shop_name: str, date_str: str
) -> list[str]:
    header = f"📋 أسعار اليوم — {shop_name}\n📅 محدثة بتاريخ: {date_str}\n"
    footer = (
        "⚠️ الأسعار قابلة للتغيير بدون إشعار مسبق. للتأكد النهائي، اطلب واستعمل "
        "زر \"💰 استعلام عن السعر\" جوا البوت."
    )

    chunks: list[str] = []
    current = header
    current_brand = None
    any_item = False

    for item in flat_items:
        idx = item["index"]
        price = prices.get(idx, item["default_price"])
        if not price:
            continue  # صنف بلا سعر محدد بعد — ما منعرضه للزبون
        any_item = True
        prefix = f"\n🔸 {item['brand']}\n" if item["brand"] != current_brand else ""
        current_brand = item["brand"]
        line = f"{prefix}- {item['name']}: {price} ل.س\n"

        if len(current) + len(line) > MAX_MESSAGE_CHARS:
            chunks.append(current.rstrip())
            current = line
        else:
            current += line

    if not any_item:
        return [header.rstrip() + "\n\nلسا ما في أسعار مضافة."]

    if current.strip():
        chunks.append(current.rstrip())

    chunks[-1] = chunks[-1] + "\n\n" + footer
    return chunks
