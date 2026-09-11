"""
إعدادات البوت — بتقرأ القيم من ملف .env
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_CHAT_ID_RAW = os.getenv("ADMIN_CHAT_ID", "")
SHOP_NAME = os.getenv("SHOP_NAME", "[اسم المحل]")
PAYMENT_ACCOUNT_NUMBER = os.getenv("PAYMENT_ACCOUNT_NUMBER", "[رقم الحساب]")
PAYMENT_ACCOUNT_NAME = os.getenv("PAYMENT_ACCOUNT_NAME", "[اسم صاحب الحساب]")
DAILY_BROADCAST_HOUR = int(os.getenv("DAILY_BROADCAST_HOUR", "9"))
DAILY_BROADCAST_MINUTE = int(os.getenv("DAILY_BROADCAST_MINUTE", "0"))
TIMEZONE = "Asia/Damascus"

# --- إعدادات خاصة بنشر البوت على Render (وضع Webhook) ---
# رابط سري لتشغيل نشرة الأسعار اليومية من خدمة تنبيه خارجية (cron-job.org مثلاً)
# لازم يكون نص عشوائي صعب التخمين — شوف README قسم "النشر على Render"
BROADCAST_SECRET = os.getenv("BROADCAST_SECRET", "")
# الرابط العام يلي Render بيعطيه تلقائياً لخدمتك (بيتعبى لحاله، ما تلمسه)
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "")

CATALOG_PATH = BASE_DIR / "data" / "catalog.json"
PRICES_PATH = BASE_DIR / "data" / "prices.txt"
SUBSCRIBERS_PATH = BASE_DIR / "data" / "subscribers.json"
PENDING_REPLIES_PATH = BASE_DIR / "data" / "pending_price_replies.json"
QUOTES_PATH = BASE_DIR / "data" / "last_quotes.json"
ORDERS_LOG_PATH = BASE_DIR / "data" / "orders_log.jsonl"


def get_admin_chat_id() -> int:
    """بيرجع آيدي شات التاجر كرقم. بيطلع خطأ واضح إذا ما كان معبّى صح بـ .env"""
    if not ADMIN_CHAT_ID_RAW or ADMIN_CHAT_ID_RAW == "REPLACE_ME":
        raise RuntimeError(
            "لازم تعبي ADMIN_CHAT_ID بملف .env قبل ما تشغل البوت. "
            "شوف دليل التشغيل (README) خطوة ٢."
        )
    try:
        return int(ADMIN_CHAT_ID_RAW)
    except ValueError:
        raise RuntimeError("ADMIN_CHAT_ID لازم يكون رقم صحيح (مثال: 123456789).")


def validate_token() -> str:
    if not BOT_TOKEN or BOT_TOKEN == "REPLACE_ME":
        raise RuntimeError(
            "لازم تعبي BOT_TOKEN بملف .env قبل ما تشغل البوت. "
            "شوف دليل التشغيل (README) خطوة ١."
        )
    return BOT_TOKEN


def validate_render_webhook_settings() -> tuple[str, str]:
    """يستخدمها bot_webhook.py بس (نشر Render). بيرجع (RENDER_EXTERNAL_URL, BROADCAST_SECRET)."""
    if not RENDER_EXTERNAL_URL:
        raise RuntimeError(
            "متغير RENDER_EXTERNAL_URL مو موجود. هاد المفروض Render يعبيه تلقائياً — "
            "تأكد إنك عم تشغل bot_webhook.py فعلاً من جوا Render (مو من جهازك الشخصي)."
        )
    if not BROADCAST_SECRET or len(BROADCAST_SECRET) < 8:
        raise RuntimeError(
            "لازم تعبي BROADCAST_SECRET بمتغيرات البيئة على Render (نص عشوائي طويل، ٨ محارف عالأقل). "
            "شوف README قسم \"النشر على Render\"."
        )
    return RENDER_EXTERNAL_URL, BROADCAST_SECRET
