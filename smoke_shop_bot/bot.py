# -*- coding: utf-8 -*-
"""
تشغيل محلي (Polling) — للتجربة على جهازك أو أي سيرفر/جهاز يضل شغال بنفسك.
شغّلها بـ: python3 bot.py    (شوف README.md خطوة ٥)

لنشر البوت على Render استخدم bot_webhook.py بدل هاد الملف — شوف README قسم "النشر على Render".
"""
import datetime as dt
import logging

import pytz

import app_factory
import broadcast
import config

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


async def _daily_broadcast_job(context) -> None:
    await broadcast.send_daily_broadcast(context.bot)


def _register_daily_broadcast(application) -> None:
    tz = pytz.timezone(config.TIMEZONE)
    broadcast_time = dt.time(hour=config.DAILY_BROADCAST_HOUR, minute=config.DAILY_BROADCAST_MINUTE, tzinfo=tz)
    application.job_queue.run_daily(_daily_broadcast_job, time=broadcast_time, name="daily_price_broadcast")
    logger.info(
        "تسجيل بث الأسعار اليومي — كل يوم الساعة %02d:%02d بتوقيت %s",
        config.DAILY_BROADCAST_HOUR,
        config.DAILY_BROADCAST_MINUTE,
        config.TIMEZONE,
    )


def main() -> None:
    application = app_factory.build_application(with_updater=True)
    _register_daily_broadcast(application)

    logger.info("البوت شغّال (Polling)... (Ctrl+C للإيقاف)")
    application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
