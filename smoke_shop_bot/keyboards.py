"""
بناء لوحات الأزرار (Inline Keyboards) — بيستخدم فهارس (indices) بالـ callback_data
بدل النص العربي نفسه، منشان ما نتجاوز حد الـ 64 بايت يلي تلغرام فارضه على callback_data
(نص عربي طويل زي 'قابلة لإعادة التعبئة' لحاله ممكن ياخد أكتر من 64 بايت لو تكرر بعدة مستويات).
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import catalog_logic as cl
import messages


def _rows_of_two(buttons: list[InlineKeyboardButton]) -> list[list[InlineKeyboardButton]]:
    rows = []
    for i in range(0, len(buttons), 2):
        rows.append(buttons[i:i + 2])
    return rows


def build_category_keyboard(catalog: dict) -> InlineKeyboardMarkup:
    categories = cl.get_categories(catalog)
    buttons = [
        InlineKeyboardButton(cl.category_button_label(catalog, cat), callback_data=f"cat:{i}")
        for i, cat in enumerate(categories)
    ]
    return InlineKeyboardMarkup(_rows_of_two(buttons))


def build_type_keyboard(catalog: dict, ci: int) -> InlineKeyboardMarkup:
    categories = cl.get_categories(catalog)
    category = categories[ci]
    types = cl.get_types(catalog, category)
    buttons = [
        InlineKeyboardButton(t, callback_data=f"type:{ci}:{ti}")
        for ti, t in enumerate(types)
    ]
    rows = _rows_of_two(buttons)
    rows.append([InlineKeyboardButton(messages.BTN_BACK, callback_data="back")])
    rows.append([InlineKeyboardButton(messages.BTN_ALL_CATEGORIES, callback_data="catlist")])
    return InlineKeyboardMarkup(rows)


def build_variant_keyboard(
    catalog: dict, ci: int, ti: int, selected: set[int] | None = None
) -> InlineKeyboardMarkup:
    """
    قائمة الأصناف — Multi-select: كل زر بيتحول لعلامة ✅ لما تختاريه (تدوسي عليه
    كمان مرة تلغي الاختيار)، وتحت في زر "➕ أضف المختار للسلة" منشان تأكدي
    الاختيار وتبلشي تحددي الكمية لكل صنف اخترتيه.
    """
    selected = selected or set()
    categories = cl.get_categories(catalog)
    category = categories[ci]
    types = cl.get_types(catalog, category)
    type_ = types[ti]
    variants = cl.get_variants(catalog, category, type_)
    buttons = [
        InlineKeyboardButton(
            f"✅ {v}" if vi in selected else f"▫️ {v}",
            callback_data=f"mvar:{ci}:{ti}:{vi}",
        )
        for vi, v in enumerate(variants)
    ]
    rows = _rows_of_two(buttons)
    rows.append([InlineKeyboardButton(messages.BTN_ADD_SELECTED, callback_data=f"mvardone:{ci}:{ti}")])
    rows.append([InlineKeyboardButton(messages.BTN_BACK, callback_data="back")])
    rows.append([InlineKeyboardButton(messages.BTN_ALL_CATEGORIES, callback_data="catlist")])
    return InlineKeyboardMarkup(rows)


def build_unit_keyboard(catalog: dict, ci: int, type_: str | None = None) -> InlineKeyboardMarkup:
    categories = cl.get_categories(catalog)
    category = categories[ci]
    units = cl.get_units(catalog, category, type_)
    buttons = [
        InlineKeyboardButton(u["name"], callback_data=f"unit:{ci}:{ui}")
        for ui, u in enumerate(units)
    ]
    rows = _rows_of_two(buttons)
    rows.append([InlineKeyboardButton(messages.BTN_BACK, callback_data="back")])
    return InlineKeyboardMarkup(rows)


def build_back_only_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(messages.BTN_BACK, callback_data="back")]])


def build_welcome_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(messages.WELCOME_BUTTON, callback_data="age:ok")]])


def build_cart_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(messages.BTN_ADD_MORE, callback_data="cart:add_more")],
        [InlineKeyboardButton(messages.BTN_UNDO, callback_data="cart:undo")],
        [InlineKeyboardButton(messages.BTN_CLEAR, callback_data="cart:clear")],
        [InlineKeyboardButton(messages.BTN_PRICE_INQUIRY, callback_data="cart:price_inquiry")],
        [InlineKeyboardButton(messages.BTN_CART_BACK_TO_TYPES, callback_data="cart:back_to_types")],
    ])


def build_idle_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(messages.WELCOME_BUTTON, callback_data="idle:continue")],
        [InlineKeyboardButton(messages.BTN_IDLE_CANCEL, callback_data="idle:cancel")],
    ])


def build_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(messages.BTN_CONFIRM_ORDER, callback_data="confirm:yes")],
        [InlineKeyboardButton(messages.BTN_CANCEL_ORDER, callback_data="confirm:no")],
    ])


def build_cash_service_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(messages.BTN_SHAMCASH, callback_data="cash:shamcash")],
        [InlineKeyboardButton(messages.BTN_SYRIATELCASH, callback_data="cash:syriatelcash")],
    ])


def build_payment_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(messages.BTN_PAY_PREPAID, callback_data="pay:prepaid")],
        [InlineKeyboardButton(messages.BTN_PAY_DEPOSIT, callback_data="pay:deposit")],
        [InlineKeyboardButton(messages.BTN_PAY_COD, callback_data="pay:cod")],
    ])
