# -*- coding: utf-8 -*-
"""
منطق بث نشرة الأسعار اليومية — مفصول لحاله منشان يستخدمه بوت الـ Polling المحلي
(عبر job_queue الداخلي) وبوت الـ Webhook على Render (عبر رابط خارجي) سوا بدون تكرار كود.
"""
import datetime as dt
import logging

import pytz
from telegram import Bot
from telegram.error import BadRequest, Forbidden

import config
import price_sheet_logic as ps_logic
import prices_state
import storage

logger = logging.getLogger(__name__)

_TZ = pytz.timezone(config.TIMEZONE)


async def send_daily_broadcast(bot: Bot) -> tuple[int, int]:
    """بترجع (عدد_وصلهم, عدد_انحذفوا_لأنهم_حظروا_البوت). النشرة ممكن توصل بأكتر
    من رسالة متتالية إذا كانت قائمة الأسعار طويلة (شوف price_sheet_logic.py)."""
    date_str = dt.datetime.now(_TZ).strftime("%Y-%m-%d %H:%M")
    chunks = ps_logic.format_customer_prices(
        prices_state.FLAT_ITEMS,
        prices_state.current_prices(),
        config.SHOP_NAME,
        date_str,
        category_of_brand=prices_state.CATEGORY_OF_BRAND,
    )

    subscribers = storage.get_subscribers(config.SUBSCRIBERS_PATH)
    sent, blocked = 0, 0

    for chat_id in subscribers:
        try:
            for chunk in chunks:
                await bot.send_message(chat_id, chunk)
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

        subscribers_now = storage.get_subscribers(config.SUBSCRIBERS_PATH)
        await telegram_state.sync_state_to_telegram(bot, subscribers_now, prices_state.overrides)
    except Exception:  # pragma: no cover - حماية إضافية بس، ما لازم يوقف البث
        logger.exception("تعذر تحديث الحالة المثبتة بتلغرام.")

    return sent, blocked
