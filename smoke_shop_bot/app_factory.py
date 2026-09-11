# -*- coding: utf-8 -*-
"""
بناء تطبيق تلغرام (Application) وتسجيل كل المعالجات — كود مشترك بين:
- bot.py          (تشغيل محلي بنمط Polling)
- bot_webhook.py   (نشر على Render بنمط Webhook)
منشان ما نكرر تسجيل ٢٠ هاندلر بملفين ونخاطر ننسى نحدث وحدة لما نعدل التانية.
"""
import logging

from telegram import BotCommand
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

import config
import handlers
import telegram_state

logger = logging.getLogger(__name__)


async def _post_init(application: Application) -> None:
    await application.bot.set_my_commands(
        [
            BotCommand("start", "🛒 ابدأ طلب جديد"),
            BotCommand("prices", "📋 شوف أسعار اليوم"),
            BotCommand("confirm", "✅ أكد الطلب بعد معرفة السعر"),
            BotCommand("cancel", "❌ تراجع عن الطلب"),
        ]
    )
    logger.info("تم تسجيل أوامر القائمة (☰) بنجاح.")

    # استرجاع لائحة المشتركين من الرسالة المثبتة بتلغرام (مهم بعد أي إعادة تشغيل
    # على استضافة بتمسح الملفات المحلية زي Render — شوف telegram_state.py)
    await telegram_state.load_subscribers_from_telegram(application.bot)


def _register_handlers(application: Application) -> None:
    # --- الأوامر (نسخة إنجليزية آمنة تظهر بقائمة ☰) ---
    application.add_handler(CommandHandler("start", handlers.cmd_start))
    application.add_handler(CommandHandler("confirm", handlers.cmd_confirm))
    application.add_handler(CommandHandler("cancel", handlers.cmd_cancel))
    application.add_handler(CommandHandler("prices", handlers.cmd_prices))

    # --- نفس الأوامر بالعربي (زي ما بالدليل تماماً) — تلغرام ما بيسجلها كأمر رسمي
    #     بقائمة ☰ (بس يقبل حروف إنجليزية/أرقام/underscore بأسماء الأوامر)، بس البوت
    #     لسا بيفهمها ويشتغل معها ١٠٠٪ إذا الزبون كتبها يدوياً بنفس الشات. ---
    application.add_handler(MessageHandler(filters.Regex(r"/تأكيد"), handlers.cmd_confirm))
    application.add_handler(MessageHandler(filters.Regex(r"/الغاء"), handlers.cmd_cancel))
    application.add_handler(MessageHandler(filters.Regex(r"/اسعار"), handlers.cmd_prices))

    # --- رد التاجر (Reply) على إشعار استفسار السعر — لازم تسجيلها قبل معالج
    #     النصوص العام، ومحصورة بشات التاجر بس ---
    admin_chat_id = config.get_admin_chat_id()
    application.add_handler(
        MessageHandler(
            filters.Chat(chat_id=admin_chat_id) & filters.REPLY & filters.TEXT,
            handlers.on_admin_price_reply,
        )
    )

    # --- أزرار الكيبورد الشفافة (Inline Keyboard) ---
    application.add_handler(CallbackQueryHandler(handlers.cb_age_ok, pattern=r"^age:ok$"))
    application.add_handler(CallbackQueryHandler(handlers.cb_category, pattern=r"^cat:\d+$"))
    application.add_handler(CallbackQueryHandler(handlers.cb_type, pattern=r"^type:\d+:\d+$"))
    application.add_handler(CallbackQueryHandler(handlers.cb_variant, pattern=r"^var:\d+:\d+:\d+$"))
    application.add_handler(CallbackQueryHandler(handlers.cb_unit, pattern=r"^unit:\d+:\d+$"))
    application.add_handler(CallbackQueryHandler(handlers.cb_back, pattern=r"^back$"))
    application.add_handler(CallbackQueryHandler(handlers.cb_cart_add_more, pattern=r"^cart:add_more$"))
    application.add_handler(CallbackQueryHandler(handlers.cb_cart_undo, pattern=r"^cart:undo$"))
    application.add_handler(CallbackQueryHandler(handlers.cb_cart_clear, pattern=r"^cart:clear$"))
    application.add_handler(CallbackQueryHandler(handlers.cb_cart_price_inquiry, pattern=r"^cart:price_inquiry$"))
    application.add_handler(CallbackQueryHandler(handlers.cb_idle_continue, pattern=r"^idle:continue$"))
    application.add_handler(CallbackQueryHandler(handlers.cb_idle_cancel, pattern=r"^idle:cancel$"))
    application.add_handler(CallbackQueryHandler(handlers.cb_confirm_yes, pattern=r"^confirm:yes$"))
    application.add_handler(CallbackQueryHandler(handlers.cb_confirm_no, pattern=r"^confirm:no$"))
    application.add_handler(CallbackQueryHandler(handlers.cb_pay_prepaid, pattern=r"^pay:prepaid$"))
    application.add_handler(CallbackQueryHandler(handlers.cb_pay_deposit, pattern=r"^pay:deposit$"))
    application.add_handler(
        CallbackQueryHandler(handlers.cb_cash_service, pattern=r"^cash:(shamcash|syriatelcash)$")
    )
    application.add_handler(CallbackQueryHandler(handlers.cb_pay_cod, pattern=r"^pay:cod$"))

    # --- صورة إشعار التحويل (الدفع المسبق) ---
    application.add_handler(MessageHandler(filters.PHOTO, handlers.on_payment_photo))

    # --- معالج النصوص العام (لازم يضل آخر واحد) ---
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.on_text))


def build_application(with_updater: bool = True) -> Application:
    """
    with_updater=True  → للتشغيل المحلي بنمط Polling (bot.py)
    with_updater=False → لنمط Webhook اليدوي (bot_webhook.py)، منشان ما ينشئ PTB
                          Updater داخلي بيتعارض مع سيرفر الـ Webhook يلي منشغله إحنا بنفسنا
    """
    token = config.validate_token()
    config.get_admin_chat_id()  # بيطلع خطأ واضح فوراً إذا ADMIN_CHAT_ID مو مضبوط

    builder = ApplicationBuilder().token(token).post_init(_post_init)
    if not with_updater:
        builder = builder.updater(None)
    application = builder.build()

    _register_handlers(application)
    return application
