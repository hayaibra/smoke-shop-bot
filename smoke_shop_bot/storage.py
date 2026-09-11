"""
تخزين بسيط بملفات JSON — بدون قاعدة بيانات، وبدون أي اعتماد على مكتبة تلغرام.
هيك منقدر نختبرها لحالها.
"""
import json
from pathlib import Path
from typing import Optional


def _load(path: Path, default):
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()
        if not content:
            return default
        return json.loads(content)


def _save(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# المشتركين (لنشرة الأسعار اليومية) — كل زبون بدأ محادثة مع البوت بينضاف تلقائياً
# ---------------------------------------------------------------------------

def add_subscriber(path: Path, chat_id: int) -> None:
    subs = set(_load(path, []))
    subs.add(chat_id)
    _save(path, sorted(subs))


def remove_subscriber(path: Path, chat_id: int) -> None:
    subs = set(_load(path, []))
    subs.discard(chat_id)
    _save(path, sorted(subs))


def get_subscribers(path: Path) -> list[int]:
    return list(_load(path, []))


# ---------------------------------------------------------------------------
# ربط رسالة إشعار "استفسار سعر" (يلي بتوصل للتاجر) بآيدي شات الزبون تبعها.
# منشان لما التاجر يعمل Reply على الإشعار، منعرف نوجه ردو للزبون الصحيح.
# ---------------------------------------------------------------------------

def save_pending_reply(path: Path, admin_message_id: int, customer_chat_id: int) -> None:
    data = _load(path, {})
    data[str(admin_message_id)] = customer_chat_id
    _save(path, data)


def pop_pending_reply(path: Path, admin_message_id: int) -> Optional[int]:
    data = _load(path, {})
    value = data.pop(str(admin_message_id), None)
    _save(path, data)
    return value


def peek_pending_reply(path: Path, admin_message_id: int) -> Optional[int]:
    data = _load(path, {})
    return data.get(str(admin_message_id))


# ---------------------------------------------------------------------------
# آخر سعر رد فيه التاجر على كل زبون — منستخدمه برسالة "حوّل مبلغ ..." وقت الدفع المسبق
# ---------------------------------------------------------------------------

def save_last_quote(path: Path, customer_chat_id: int, quote_text: str) -> None:
    data = _load(path, {})
    data[str(customer_chat_id)] = quote_text
    _save(path, data)


def get_last_quote(path: Path, customer_chat_id: int) -> Optional[str]:
    data = _load(path, {})
    return data.get(str(customer_chat_id))


# ---------------------------------------------------------------------------
# سجل الطلبات المؤكدة (بونص بسيط — سطر JSON لكل طلب، تقدر تفتحو بإكسل لاحقاً)
# ---------------------------------------------------------------------------

def append_order_log(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
