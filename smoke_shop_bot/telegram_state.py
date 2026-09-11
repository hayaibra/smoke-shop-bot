# -*- coding: utf-8 -*-
"""
حل بديل عن قاعدة بيانات خارجية: منخزن لائحة المشتركين (لنشرة الأسعار اليومية) جوا
رسالة "مثبتة" (Pinned Message) بشات التاجر نفسه على تلغرام.

ليش؟ لأنه استضافات مجانية زي Render بتمسح أي ملف محلي كل ما السيرفر ينام من الخمول
(شوف README قسم "النشر على Render"). تلغرام نفسه ما بينسى شي، فمنستخدمه كـ"قاعدة بيانات"
صغيرة بدون ما نحتاج نفتح حساب بشركة تالتة ممكن ترفض حسابات من سوريا.

الدوال يلي بتبلش بـ "_" نقية (pure) ومُختبرة لحالها بدون الحاجة لمكتبة تلغرام إطلاقاً.
الدوال التانية (async) هيي يلي بتحكي فعلياً مع تلغرام.
"""
import json
import logging
from typing import TYPE_CHECKING, Optional

import config
import storage

if TYPE_CHECKING:
    from telegram import Bot

logger = logging.getLogger(__name__)

_STATE_MARKER = "SHOP_BOT_SUBSCRIBERS_V1"


def _build_state_text(subscribers: list[int]) -> str:
    payload = {"marker": _STATE_MARKER, "subscribers": subscribers}
    return json.dumps(payload, ensure_ascii=False)


def _parse_state_text(text: str) -> Optional[list[int]]:
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict) or payload.get("marker") != _STATE_MARKER:
        return None
    subs = payload.get("subscribers")
    if not isinstance(subs, list):
        return None
    return [int(x) for x in subs]


# ---------------------------------------------------------------------------
# الدوال الفعلية يلي بتحكي مع تلغرام
# ---------------------------------------------------------------------------

async def load_subscribers_from_telegram(bot: "Bot") -> list[int]:
    """
    بتنقرا وقت تشغيل البوت (post_init) — بترجع لائحة المشتركين من الرسالة المثبتة
    (إذا موجودة) وبتخزنها بالملف المحلي كمان (نسخة احتياطية سريعة أثناء تشغيل هالجلسة).
    """
    from telegram.error import BadRequest, Forbidden

    admin_id = config.get_admin_chat_id()
    try:
        chat = await bot.get_chat(admin_id)
    except (BadRequest, Forbidden) as exc:
        logger.warning("تعذر قراءة شات التاجر لاسترجاع لائحة المشتركين: %s", exc)
        return storage.get_subscribers(config.SUBSCRIBERS_PATH)

    pinned = chat.pinned_message
    if pinned and pinned.text:
        subs = _parse_state_text(pinned.text)
        if subs is not None:
            for chat_id in subs:
                storage.add_subscriber(config.SUBSCRIBERS_PATH, chat_id)
            logger.info("استرجعنا %d مشترك من الرسالة المثبتة بتلغرام.", len(subs))
            return subs

    return storage.get_subscribers(config.SUBSCRIBERS_PATH)


async def sync_subscribers_to_telegram(bot: "Bot") -> None:
    """بعد أي تغيير بلائحة المشتركين، منحدث (أو مننشئ) الرسالة المثبتة بشات التاجر."""
    from telegram.error import BadRequest, Forbidden

    admin_id = config.get_admin_chat_id()
    subscribers = storage.get_subscribers(config.SUBSCRIBERS_PATH)
    text = _build_state_text(subscribers)

    try:
        chat = await bot.get_chat(admin_id)
    except (BadRequest, Forbidden) as exc:
        logger.warning("تعذر تحديث لائحة المشتركين المثبتة: %s", exc)
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
        logger.warning("تعذر إنشاء/تثبيت رسالة لائحة المشتركين: %s", exc)
