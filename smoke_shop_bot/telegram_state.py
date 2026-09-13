# -*- coding: utf-8 -*-
"""
حل بديل عن قاعدة بيانات خارجية: منخزن لائحة المشتركين (لنشرة الأسعار اليومية)
+ تعديلات الأسعار يلي حفظها التاجر (شوف price_sheet_logic.py) سوا، جوا رسالة
"مثبتة" (Pinned Message) بشات التاجر نفسه على تلغرام.

ليش؟ لأنه استضافات مجانية زي Render بتمسح أي ملف محلي كل ما السيرفر ينام من الخمول
(شوف README قسم "النشر على Render"). تلغرام نفسه ما بينسى شي، فمنستخدمه كـ"قاعدة بيانات"
صغيرة بدون ما نحتاج نفتح حساب بشركة تالتة ممكن ترفض حسابات من سوريا.

ملاحظة: تلغرام (Bot API) ما بيعطي إمكانية نقرا أكتر من رسالة مثبتة وحدة بنفس
الوقت (get_chat بيرجع بس آخر وحدة)، فلازم كل الحالة (subscribers + prices) تنحط
سوا برسالة وحدة — لهيك في هامش أمان بالحجم (شوف price_sheet_logic.MAX_MESSAGE_CHARS
وتعليق _build_state_text تحت).

الدوال يلي بتبلش بـ "_" نقية (pure) ومُختبرة لحالها بدون الحاجة لمكتبة تلغرام إطلاقاً.
الدوال التانية (async) هيي يلي بتحكي فعلياً مع تلغرام.
"""
import json
import logging
from typing import TYPE_CHECKING, Optional

import config
import price_sheet_logic
import storage

if TYPE_CHECKING:
    from telegram import Bot

logger = logging.getLogger(__name__)

_STATE_MARKER_V1 = "SHOP_BOT_SUBSCRIBERS_V1"  # نسخة قديمة (مشتركين بس) — لسا لازم نقدر نقراها
_STATE_MARKER_V2 = "SHOP_BOT_STATE_V2"  # النسخة الحالية: مشتركين + تعديلات أسعار


def _build_state_text(subscribers: list[int], price_overrides: dict[int, int]) -> str:
    payload = {
        "marker": _STATE_MARKER_V2,
        "subscribers": subscribers,
        "prices": price_sheet_logic.encode_prices_compact(price_overrides),
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _parse_state_text(text: str) -> Optional[dict]:
    """بترجع {"subscribers": [...], "prices": {index: price}} أو None لو النص
    مش تابع لنا إطلاقاً (يعني مش رسالة الحالة المثبتة تبعنا)."""
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None

    marker = payload.get("marker")
    if marker == _STATE_MARKER_V2:
        subs = payload.get("subscribers")
        if not isinstance(subs, list):
            return None
        prices = price_sheet_logic.decode_prices_compact(payload.get("prices", ""))
        return {"subscribers": [int(x) for x in subs], "prices": prices}

    if marker == _STATE_MARKER_V1:
        # نسخة قديمة، قبل ما نضيف الأسعار — مشتركين بس، ما في تعديلات أسعار محفوظة.
        subs = payload.get("subscribers")
        if not isinstance(subs, list):
            return None
        return {"subscribers": [int(x) for x in subs], "prices": {}}

    return None


# ---------------------------------------------------------------------------
# الدوال الفعلية يلي بتحكي مع تلغرام
# ---------------------------------------------------------------------------

async def load_state_from_telegram(bot: "Bot") -> tuple[list[int], dict[int, int]]:
    """
    بتنقرا وقت تشغيل البوت (post_init) — بترجع (subscribers, price_overrides) من
    الرسالة المثبتة (إذا موجودة)، وبتخزن المشتركين بالملف المحلي كمان (نسخة
    احتياطية سريعة أثناء تشغيل هالجلسة).
    """
    from telegram.error import BadRequest, Forbidden

    admin_id = config.get_admin_chat_id()
    try:
        chat = await bot.get_chat(admin_id)
    except (BadRequest, Forbidden) as exc:
        logger.warning("تعذر قراءة شات التاجر لاسترجاع الحالة المحفوظة: %s", exc)
        return storage.get_subscribers(config.SUBSCRIBERS_PATH), {}

    pinned = chat.pinned_message
    if pinned and pinned.text:
        state = _parse_state_text(pinned.text)
        if state is not None:
            for chat_id in state["subscribers"]:
                storage.add_subscriber(config.SUBSCRIBERS_PATH, chat_id)
            logger.info(
                "استرجعنا %d مشترك و %d تعديل سعر من الرسالة المثبتة بتلغرام.",
                len(state["subscribers"]),
                len(state["prices"]),
            )
            return state["subscribers"], state["prices"]

    return storage.get_subscribers(config.SUBSCRIBERS_PATH), {}


async def sync_state_to_telegram(
    bot: "Bot", subscribers: list[int], price_overrides: dict[int, int]
) -> None:
    """بعد أي تغيير (مشترك جديد/انحذف، أو تعديل سعر)، منحدث (أو مننشئ) الرسالة
    المثبتة بشات التاجر بالحالة الكاملة الحالية."""
    from telegram.error import BadRequest, Forbidden

    admin_id = config.get_admin_chat_id()
    text = _build_state_text(subscribers, price_overrides)

    if len(text) > 4096:
        # ما لازم يصير عادةً (شوف هامش الأمان بـ price_sheet_logic)، بس منحمي حالنا
        # منشان ما نرمي خطأ لتلغرام ونوقف تحديث المشتركين كمان.
        logger.error(
            "نص الحالة المثبتة تجاوز حد تلغرام (%d محرف) — تخطينا هالتحديث.", len(text)
        )
        return

    try:
        chat = await bot.get_chat(admin_id)
    except (BadRequest, Forbidden) as exc:
        logger.warning("تعذر تحديث الحالة المثبتة: %s", exc)
        return

    pinned = chat.pinned_message
    if pinned and pinned.text and _parse_state_text(pinned.text) is not None:
        try:
            await bot.edit_message_text(chat_id=admin_id, message_id=pinned.message_id, text=text)
            return
        except BadRequest as exc:
            if "not modified" not in str(exc).lower():
                logger.warning("تعذر تعديل الرسالة المثبتة: %s", exc)
                return
            return  # النص نفسه، ما في داعي تعديل

    try:
        sent = await bot.send_message(admin_id, text)
        await bot.pin_chat_message(chat_id=admin_id, message_id=sent.message_id, disable_notification=True)
    except (BadRequest, Forbidden) as exc:
        logger.warning("تعذر إنشاء/تثبيت رسالة الحالة: %s", exc)
