# -*- coding: utf-8 -*-
"""
كل معالجات (Handlers) البوت. هون بس مكان وصل منطق catalog_logic.py و storage.py
و messages.py بمكتبة تلغرام (python-telegram-bot).
"""
import datetime as dt
import logging

import pytz
from telegram import Update
from telegram.error import BadRequest, Forbidden
from telegram.ext import ContextTypes

import catalog_logic as cl
import config
import keyboards as kb
import messages
import storage
import telegram_state

CATALOG = cl.load_catalog(config.CATALOG_PATH)
TZ = pytz.timezone(config.TIMEZONE)

IDLE_REMINDER_SECONDS = 10 * 60  # ١٠ دقايق، متل ما ذكر بالدليل


# ---------------------------------------------------------------------------
# أدوات مساعدة عامة
# ---------------------------------------------------------------------------

def _now_str() -> str:
    return dt.datetime.now(TZ).strftime("%Y-%m-%d %H:%M")


def _customer_label(user) -> str:
    if user.username:
        return f"{user.full_name} (@{user.username})"
    return f"{user.full_name} (id:{user.id})"


def _idle_job_name(chat_id: int) -> str:
    return f"idle_{chat_id}"


def _cancel_idle_reminder(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    if context.job_queue is None:
        return
    for job in context.job_queue.get_jobs_by_name(_idle_job_name(chat_id)):
        job.schedule_removal()


def _schedule_idle_reminder(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    if context.job_queue is None:
        return
    _cancel_idle_reminder(context, chat_id)
    context.job_queue.run_once(
        _idle_reminder_job, when=IDLE_REMINDER_SECONDS, chat_id=chat_id, name=_idle_job_name(chat_id)
    )


async def _idle_reminder_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = context.job.chat_id
    try:
        await context.bot.send_message(chat_id, messages.IDLE_REMINDER)
    except (Forbidden, BadRequest):
        pass


def _reset_cart_fields(user_data: dict) -> None:
    user_data["cart"] = []
    user_data["cart_backup"] = []
    user_data["awaiting_price_confirmation"] = False
    user_data["state"] = None
    user_data["section"] = None
    user_data["type"] = None
    user_data["variant"] = None
    user_data["category_index"] = None
    user_data["type_index"] = None
    user_data["had_variant"] = False
    user_data["unit_name"] = None
    user_data["unit_fixed"] = None
    user_data["payment_method"] = None
    user_data["customer_name"] = None
    user_data["customer_address"] = None
    user_data["customer_phone"] = None
    user_data["payment_photo_file_id"] = None


async def _answer(update: Update) -> None:
    if update.callback_query is not None:
        await update.callback_query.answer()


async def _sync_subscribers_best_effort(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    بعد أي تغيير بلائحة المشتركين، منحدث النسخة المثبتة بشات التاجر بتلغرام (مهم خصوصاً
    على استضافات زي Render يلي بتمسح الملفات المحلية). لو صار خطأ، ما منوقف الزبون —
    بس منسجل الخطأ ومنكمل عادي.
    """
    try:
        await telegram_state.sync_subscribers_to_telegram(context.bot)
    except Exception:
        logging.getLogger(__name__).exception("تعذر تحديث لائحة المشتركين المثبتة.")


# ---------------------------------------------------------------------------
# شاشات العرض (يستخدمها التنقل للأمام وزر الرجوع سوا)
# ---------------------------------------------------------------------------

async def _render_welcome(context, chat_id):
    await context.bot.send_message(chat_id, messages.welcome(), reply_markup=kb.build_welcome_keyboard())


async def _render_category(context, chat_id, user_data):
    user_data["nav"] = "category"
    await context.bot.send_message(chat_id, messages.MAIN_MENU_PROMPT, reply_markup=kb.build_category_keyboard(CATALOG))


async def _render_type(context, chat_id, user_data, ci):
    categories = cl.get_categories(CATALOG)
    category = categories[ci]
    emoji = cl.get_category_emoji(CATALOG, category)
    user_data["nav"] = "type"
    user_data["category_index"] = ci
    user_data["section"] = category
    await context.bot.send_message(
        chat_id, messages.choose_type_prompt(category, emoji), reply_markup=kb.build_type_keyboard(CATALOG, ci)
    )


async def _render_variant(context, chat_id, user_data, ci, ti):
    categories = cl.get_categories(CATALOG)
    category = categories[ci]
    types_ = cl.get_types(CATALOG, category)
    type_ = types_[ti]
    user_data["nav"] = "variant"
    user_data["type_index"] = ti
    user_data["type"] = type_
    await context.bot.send_message(
        chat_id, messages.choose_variant_prompt(category, type_), reply_markup=kb.build_variant_keyboard(CATALOG, ci, ti)
    )


async def _render_unit(context, chat_id, user_data, ci, product_name, had_variant):
    user_data["nav"] = "unit"
    user_data["had_variant"] = had_variant
    await context.bot.send_message(
        chat_id, messages.choose_unit_prompt(product_name), reply_markup=kb.build_unit_keyboard(CATALOG, ci)
    )


async def _render_count_prompt(context, chat_id, user_data, unit_name):
    user_data["nav"] = "count"
    user_data["state"] = "awaiting_count"
    await context.bot.send_message(
        chat_id, messages.enter_count_prompt(unit_name), reply_markup=kb.build_back_only_keyboard()
    )


async def _render_cart(context, chat_id, user_data, header_line, added_summary=None):
    cart_text = cl.format_cart_text(user_data.get("cart", []))
    user_data["nav"] = "cart"
    if added_summary is not None:
        text = messages.cart_screen(added_summary, cart_text)
    else:
        text = f"{header_line}\n\n🛒 هيدي سلتك لهلق:\n{cart_text}\n\nشو حابب تعمل؟"
    await context.bot.send_message(chat_id, text, reply_markup=kb.build_cart_keyboard())


# ---------------------------------------------------------------------------
# /start — البداية، الترحيب (بلا شرط تأكيد عمر، بناءً على طلب صاحبة المحل)
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    storage.add_subscriber(config.SUBSCRIBERS_PATH, chat_id)
    await _sync_subscribers_best_effort(context)
    context.user_data.clear()
    _reset_cart_fields(context.user_data)
    _cancel_idle_reminder(context, chat_id)
    await context.bot.send_message(chat_id, messages.welcome())
    await _render_category(context, chat_id, context.user_data)
    _schedule_idle_reminder(context, chat_id)


async def cb_age_ok(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _answer(update)
    chat_id = update.effective_chat.id
    context.user_data["age_confirmed"] = True
    await _render_category(context, chat_id, context.user_data)
    _schedule_idle_reminder(context, chat_id)


# ---------------------------------------------------------------------------
# اختيار القسم → النوع → الصنف → الوحدة → العدد
# ---------------------------------------------------------------------------

async def cb_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _answer(update)
    chat_id = update.effective_chat.id
    ci = int(update.callback_query.data.split(":")[1])
    user_data = context.user_data
    user_data["variant"] = None
    await _render_type(context, chat_id, user_data, ci)
    _schedule_idle_reminder(context, chat_id)


async def cb_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _answer(update)
    chat_id = update.effective_chat.id
    _, ci_s, ti_s = update.callback_query.data.split(":")
    ci, ti = int(ci_s), int(ti_s)
    user_data = context.user_data

    categories = cl.get_categories(CATALOG)
    category = categories[ci]
    types_ = cl.get_types(CATALOG, category)
    type_ = types_[ti]
    user_data["category_index"] = ci
    user_data["type_index"] = ti
    user_data["type"] = type_

    if cl.has_variants(CATALOG, category, type_):
        await _render_variant(context, chat_id, user_data, ci, ti)
    else:
        user_data["variant"] = None
        await _render_unit(context, chat_id, user_data, ci, product_name=type_, had_variant=False)
    _schedule_idle_reminder(context, chat_id)


async def cb_variant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _answer(update)
    chat_id = update.effective_chat.id
    _, ci_s, ti_s, vi_s = update.callback_query.data.split(":")
    ci, ti, vi = int(ci_s), int(ti_s), int(vi_s)
    user_data = context.user_data

    categories = cl.get_categories(CATALOG)
    category = categories[ci]
    types_ = cl.get_types(CATALOG, category)
    type_ = types_[ti]
    variants = cl.get_variants(CATALOG, category, type_)
    variant = variants[vi]
    user_data["variant"] = variant

    await _render_unit(context, chat_id, user_data, ci, product_name=variant, had_variant=True)
    _schedule_idle_reminder(context, chat_id)


async def cb_unit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _answer(update)
    chat_id = update.effective_chat.id
    _, ci_s, ui_s = update.callback_query.data.split(":")
    ci, ui = int(ci_s), int(ui_s)
    user_data = context.user_data

    categories = cl.get_categories(CATALOG)
    category = categories[ci]
    units = cl.get_units(CATALOG, category)
    unit = units[ui]
    user_data["unit_name"] = unit["name"]
    user_data["unit_fixed"] = unit["fixed"]

    if unit["fixed"]:
        quantity = cl.format_quantity(unit["name"], True)
        await _finalize_add_to_cart(update, context, quantity)
    else:
        await _render_count_prompt(context, chat_id, user_data, unit["name"])
    _schedule_idle_reminder(context, chat_id)


async def _finalize_add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE, quantity: str) -> None:
    chat_id = update.effective_chat.id
    user_data = context.user_data
    section = user_data["section"]
    type_ = user_data["type"]
    variant = user_data.get("variant")

    line = cl.format_cart_line(section, type_, variant, quantity)
    new_cart, backup = cl.add_to_cart(user_data.get("cart", []), line)
    user_data["cart"] = new_cart
    user_data["cart_backup"] = backup
    user_data["state"] = None

    summary = cl.format_added_summary(type_, variant, quantity)
    await _render_cart(context, chat_id, user_data, header_line="", added_summary=summary)


# ---------------------------------------------------------------------------
# زر الرجوع — بيعتمد على user_data['nav'] لمعرفة وين نرجع بالضبط
# ---------------------------------------------------------------------------

async def cb_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _answer(update)
    chat_id = update.effective_chat.id
    user_data = context.user_data
    nav = user_data.get("nav")

    if nav == "type":
        await _render_category(context, chat_id, user_data)
    elif nav == "variant":
        ci = user_data["category_index"]
        await _render_type(context, chat_id, user_data, ci)
    elif nav in ("unit", "count"):
        ci = user_data["category_index"]
        ti = user_data.get("type_index")
        if user_data.get("had_variant") and ti is not None:
            await _render_variant(context, chat_id, user_data, ci, ti)
        else:
            await _render_type(context, chat_id, user_data, ci)
    else:
        await _render_category(context, chat_id, user_data)
    _schedule_idle_reminder(context, chat_id)


# ---------------------------------------------------------------------------
# شاشة السلة: ضيف صنف تاني / تراجع / امسح / استعلام عن السعر
# ---------------------------------------------------------------------------

async def cb_cart_add_more(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _answer(update)
    chat_id = update.effective_chat.id
    user_data = context.user_data
    user_data["type"] = None
    user_data["variant"] = None
    user_data["unit_name"] = None
    user_data["state"] = None
    await _render_category(context, chat_id, user_data)
    _schedule_idle_reminder(context, chat_id)


async def cb_cart_undo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _answer(update)
    chat_id = update.effective_chat.id
    user_data = context.user_data
    backup = user_data.get("cart_backup", [])
    new_cart = cl.undo_last(backup)
    user_data["cart"] = new_cart
    user_data["cart_backup"] = list(new_cart)  # تراجع وحيد بس، متل ما بالدليل بالضبط
    await _render_cart(context, chat_id, user_data, header_line="↩️ تراجعنا عن آخر إضافة ✅")
    _schedule_idle_reminder(context, chat_id)


async def cb_cart_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _answer(update)
    chat_id = update.effective_chat.id
    user_data = context.user_data
    cart, backup = cl.clear_cart()
    user_data["cart"] = cart
    user_data["cart_backup"] = backup
    user_data["awaiting_price_confirmation"] = False
    await context.bot.send_message(chat_id, "🗑️ تمام، مسحنا السلة بالكامل.")
    await _render_category(context, chat_id, user_data)
    _schedule_idle_reminder(context, chat_id)


async def cb_cart_price_inquiry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _answer(update)
    chat_id = update.effective_chat.id
    user_data = context.user_data
    cart = user_data.get("cart", [])

    if not cart:
        await context.bot.send_message(chat_id, messages.EMPTY_CART_WARNING)
        return

    await context.bot.send_message(chat_id, messages.PRICE_INQUIRY_RECEIVED)

    cart_text = cl.format_cart_text(cart)
    customer_label = _customer_label(update.effective_user)
    admin_text = messages.admin_price_inquiry_notice(customer_label, cart_text, _now_str())

    admin_chat_id = config.get_admin_chat_id()
    sent = await context.bot.send_message(admin_chat_id, admin_text)
    storage.save_pending_reply(config.PENDING_REPLIES_PATH, admin_message_id=sent.message_id, customer_chat_id=chat_id)

    user_data["awaiting_price_confirmation"] = True
    _cancel_idle_reminder(context, chat_id)


# ---------------------------------------------------------------------------
# رد التاجر على إشعار استفسار السعر (Reply على رسالة البوت) — التوجيه التلقائي
# ---------------------------------------------------------------------------

async def on_admin_price_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    replied = message.reply_to_message
    if replied is None:
        return

    customer_chat_id = storage.pop_pending_reply(config.PENDING_REPLIES_PATH, replied.message_id)
    if customer_chat_id is None:
        await message.reply_text(
            "ما لقيت طلب استفسار مرتبط بهالرسالة 🤔\n"
            "تأكد إنك عم تعمل Reply مباشرة على رسالة \"💰 استفسار سعر جديد!\"."
        )
        return

    admin_text = message.text or ""
    storage.save_last_quote(config.QUOTES_PATH, customer_chat_id, admin_text)
    full_text = messages.price_reply_footer(admin_text)

    try:
        await context.bot.send_message(customer_chat_id, full_text, reply_markup=kb.build_confirm_keyboard())
    except (Forbidden, BadRequest):
        await message.reply_text("⚠️ ما قدرت أوصل الرد للزبون (يمكن يكون حظر البوت أو مسح المحادثة).")
        return

    customer_data = context.application.user_data[customer_chat_id]
    customer_data["awaiting_price_confirmation"] = True

    await message.reply_text("✅ تم إرسال السعر للزبون. منتظرين يأكد أو يلغي.")


# ---------------------------------------------------------------------------
# /تأكيد و /الغاء — وكمان أزرار "✅ تأكيد الطلب" / "❌ إلغاء الطلب" (نفس المنطق بالضبط،
# بس اختصار للزبون لأنه أوامر عربي ما بتنسجل بقائمة ☰ الرسمية تبع تلغرام)
# ---------------------------------------------------------------------------

async def _do_confirm_order(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = context.user_data

    if not user_data.get("cart"):
        await context.bot.send_message(chat_id, messages.NOTHING_TO_CONFIRM)
        return

    if not user_data.get("awaiting_price_confirmation"):
        await context.bot.send_message(chat_id, messages.NEED_PRICE_INQUIRY_FIRST)
        return

    user_data["awaiting_price_confirmation"] = False
    await context.bot.send_message(chat_id, messages.CONFIRM_ORDER_MESSAGE)
    user_data["nav"] = "payment"
    await context.bot.send_message(chat_id, messages.PAYMENT_METHOD_PROMPT, reply_markup=kb.build_payment_keyboard())
    _schedule_idle_reminder(context, chat_id)


async def _do_cancel_order(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = context.user_data
    _reset_cart_fields(user_data)
    await context.bot.send_message(chat_id, messages.CANCEL_ORDER_MESSAGE)
    _cancel_idle_reminder(context, chat_id)


async def cmd_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _do_confirm_order(update.effective_chat.id, context)


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _do_cancel_order(update.effective_chat.id, context)


async def cb_confirm_yes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _answer(update)
    await _do_confirm_order(update.effective_chat.id, context)


async def cb_confirm_no(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _answer(update)
    await _do_cancel_order(update.effective_chat.id, context)


async def cmd_prices(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    text = config.PRICES_PATH.read_text(encoding="utf-8") if config.PRICES_PATH.exists() else "لسا ما في أسعار مضافة."
    await context.bot.send_message(chat_id, text)


# ---------------------------------------------------------------------------
# اختيار طريقة الدفع
# ---------------------------------------------------------------------------

async def cb_pay_prepaid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _answer(update)
    chat_id = update.effective_chat.id
    user_data = context.user_data
    user_data["payment_method"] = "prepaid"
    user_data["state"] = "awaiting_payment_photo"
    amount_text = storage.get_last_quote(config.QUOTES_PATH, chat_id) or "المبلغ يلي تأكدلك ياه قبل شوي"
    await context.bot.send_message(chat_id, messages.prepaid_instructions(amount_text))
    _schedule_idle_reminder(context, chat_id)


async def cb_pay_cod(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _answer(update)
    chat_id = update.effective_chat.id
    user_data = context.user_data
    user_data["payment_method"] = "cod"
    user_data["state"] = "awaiting_name"
    await context.bot.send_message(chat_id, messages.COD_INTRO)
    _schedule_idle_reminder(context, chat_id)


# ---------------------------------------------------------------------------
# استقبال صورة إشعار التحويل (الدفع المسبق)
# ---------------------------------------------------------------------------

async def on_payment_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = context.user_data
    if user_data.get("state") != "awaiting_payment_photo":
        return
    photo = update.message.photo[-1]
    user_data["payment_photo_file_id"] = photo.file_id
    await _finalize_order(update, context, payment_proof=True)


# ---------------------------------------------------------------------------
# معالج النصوص العام: العدد، اسم/عنوان/هاتف الدفع عند الاستلام
# ---------------------------------------------------------------------------

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = context.user_data
    state = user_data.get("state")
    text = update.message.text or ""
    chat_id = update.effective_chat.id

    if state == "awaiting_count":
        count = cl.parse_count(text)
        if count is None:
            await context.bot.send_message(chat_id, messages.INVALID_COUNT_MESSAGE)
            return
        unit_name = user_data["unit_name"]
        quantity = cl.format_quantity(unit_name, False, count)
        await _finalize_add_to_cart(update, context, quantity)
        _schedule_idle_reminder(context, chat_id)

    elif state == "awaiting_name":
        user_data["customer_name"] = text.strip()
        user_data["state"] = "awaiting_address"
        await context.bot.send_message(chat_id, messages.COD_ASK_ADDRESS)
        _schedule_idle_reminder(context, chat_id)

    elif state == "awaiting_address":
        user_data["customer_address"] = text.strip()
        user_data["state"] = "awaiting_phone"
        await context.bot.send_message(chat_id, messages.COD_ASK_PHONE)
        _schedule_idle_reminder(context, chat_id)

    elif state == "awaiting_phone":
        user_data["customer_phone"] = text.strip()
        await _finalize_order(update, context, payment_proof=False)

    elif state == "awaiting_payment_photo":
        await context.bot.send_message(chat_id, messages.INVALID_PAYMENT_PROOF)

    # غير هيك، ما في حالة نشطة — البوت ما بيرد (الزبون شغّال بالأزرار عادةً)


# ---------------------------------------------------------------------------
# إتمام الطلب — إشعار التاجر + رسالة تثبيت للزبون + تسجيل الطلب
# ---------------------------------------------------------------------------

async def _finalize_order(update: Update, context: ContextTypes.DEFAULT_TYPE, payment_proof: bool) -> None:
    chat_id = update.effective_chat.id
    user_data = context.user_data
    cart_text = cl.format_cart_text(user_data.get("cart", []))

    await context.bot.send_message(chat_id, messages.order_confirmation(cart_text))

    user = update.effective_user
    customer_label = _customer_label(user)
    payment_method = user_data.get("payment_method")

    if payment_method == "prepaid":
        phone = messages.NOT_APPLICABLE
        address = messages.NOT_APPLICABLE
        payment_label = messages.PAYMENT_LABEL_PREPAID
    else:
        phone = user_data.get("customer_phone") or messages.NOT_APPLICABLE
        address = user_data.get("customer_address") or messages.NOT_APPLICABLE
        payment_label = messages.PAYMENT_LABEL_COD

    admin_text = messages.admin_final_order_notice(
        customer_label=customer_label,
        phone=phone,
        address=address,
        cart_text=cart_text,
        payment_method_label=payment_label,
        has_payment_proof=payment_proof,
        timestamp=_now_str(),
    )

    admin_chat_id = config.get_admin_chat_id()
    if payment_proof and user_data.get("payment_photo_file_id"):
        await context.bot.send_photo(admin_chat_id, photo=user_data["payment_photo_file_id"], caption=admin_text)
    else:
        await context.bot.send_message(admin_chat_id, admin_text)

    storage.append_order_log(
        config.ORDERS_LOG_PATH,
        {
            "timestamp": _now_str(),
            "customer_chat_id": chat_id,
            "customer_label": customer_label,
            "cart": user_data.get("cart", []),
            "payment_method": payment_method,
            "customer_name": user_data.get("customer_name"),
            "customer_address": user_data.get("customer_address"),
            "customer_phone": user_data.get("customer_phone"),
        },
    )

    _reset_cart_fields(user_data)
    _cancel_idle_reminder(context, chat_id)
