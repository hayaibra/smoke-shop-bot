# -*- coding: utf-8 -*-
"""
منطق بث نشرة الأسعار اليومية — مفصول لحاله منشان يستخدمه بوت الـ Polling المحلي
(عبر job_queue الداخلي) وبوت الـ Webhook على Render (عبر رابط خارجي) سوا بدون تكرار كود.
"""
import logging

from telegram import Bot
from telegram.error import BadRequest, Forbidden

import config
import storage

logger = logging.getLogger(__name__)


async def send_daily_broadcast(bot: Bot) -> tuple[int, int]:
    """بترجع (عدد_وصلهم, عدد_انحذفوا_لأنهم_حظروا_البوت)."""
    if not config.PRICES_PATH.exists():
        logger.warning("prices.txt غير موجود — تخطينا البث اليومي.")
        return 0, 0

    text = config.PRICES_PATH.read_text(encoding="utf-8")
    subscribers = storage.get_subscribers(config.SUBSCRIBERS_PATH)
    sent, blocked = 0, 0

    for chat_id in subscribers:
        try:
            await bot.send_message(chat_id, text)
            sent += 1
        except Forbidden:
            storage.remove_subscriber(config.SUBSCRIBERS_PATH, chat_id)
            blocked += 1
        except BadRequest as exc:
            logger.warning("تعذر إرسال نشرة الأسعار لـ %s: %s", chat_id, exc)

    logger.info("بث الأسعار اليومي: وصل لـ %d، وحذفنا %d ما عادوا مشتركين.", sent, blocked)

    # حدّث النسخة المثبتة بتلغرام (مهم خصوصاً على Render، شوف telegram_state.py)
    try:
        import telegram_state

        await telegram_state.sync_subscribers_to_telegram(bot)
    except Exception:  # pragma: no cover - حماية إضافية بس، ما لازم يوقف البث
        logger.exception("تعذر تحديث لائحة المشتركين المثبتة بتلغرام.")

    return sent, blocked
