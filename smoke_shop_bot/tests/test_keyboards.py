"""
اختبار لوحات الأزرار (keyboards.py) بدون تنصيب مكتبة python-telegram-bot فعلياً —
منعمل "stub" بسيط لصفي InlineKeyboardButton / InlineKeyboardMarkup بنفس الشكل تماماً،
منشان نتأكد إن الـ callback_data قصير وصحيح، وبنية الأزرار مضبوطة، قبل ما نوصل الكود
لجهاز فيه إنترنت وفيه المكتبة الحقيقية.
"""
import sys
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class _FakeInlineKeyboardButton:
    def __init__(self, text, callback_data=None, **kwargs):
        self.text = text
        self.callback_data = callback_data


class _FakeInlineKeyboardMarkup:
    def __init__(self, inline_keyboard):
        self.inline_keyboard = inline_keyboard


def _install_fake_telegram_module():
    """بنحقن نسخة مزيفة بس كافية من مكتبة telegram جوا sys.modules."""
    fake_telegram = types.ModuleType("telegram")
    fake_telegram.InlineKeyboardButton = _FakeInlineKeyboardButton
    fake_telegram.InlineKeyboardMarkup = _FakeInlineKeyboardMarkup
    sys.modules["telegram"] = fake_telegram


_install_fake_telegram_module()

import catalog_logic as cl  # noqa: E402
import keyboards as kb  # noqa: E402

CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "catalog.json"


class TestCallbackDataSafety(unittest.TestCase):
    """أهم شي: كل callback_data لازم يكون ≤ 64 بايت (حد تلغرام)."""

    def setUp(self):
        self.catalog = cl.load_catalog(CATALOG_PATH)

    def _all_buttons(self, markup):
        for row in markup.inline_keyboard:
            for btn in row:
                yield btn

    def test_category_keyboard_callback_data_short_and_correct(self):
        markup = kb.build_category_keyboard(self.catalog)
        categories = cl.get_categories(self.catalog)
        seen = []
        for btn in self._all_buttons(markup):
            self.assertLessEqual(len(btn.callback_data.encode("utf-8")), 64)
            seen.append(btn.callback_data)
        expected = [f"cat:{i}" for i in range(len(categories))]
        self.assertEqual(sorted(seen), sorted(expected))

    def test_type_keyboard_has_back_button_and_short_callback_data(self):
        for ci, category in enumerate(cl.get_categories(self.catalog)):
            markup = kb.build_type_keyboard(self.catalog, ci)
            all_data = [b.callback_data for b in self._all_buttons(markup)]
            self.assertIn("back", all_data)
            self.assertIn("catlist", all_data)
            for data in all_data:
                self.assertLessEqual(len(data.encode("utf-8")), 64)

    def test_variant_keyboard_worst_case_long_arabic_text_still_short_callback_data(self):
        # منلاقي أطول اسم صنف بكامل الكتالوج الحقيقي، ومنتأكد إن الزر نفسه بيحمل
        # النص الطويل كامل (مع بادئة ▫️ لأنه مش مختار)، بس الـ callback_data قصير
        # ومبني على أرقام بس (نمط الـ multi-select: mvar:).
        longest = ("", None, None)
        for ci, category in enumerate(cl.get_categories(self.catalog)):
            for ti, type_ in enumerate(cl.get_types(self.catalog, category)):
                for variant in cl.get_variants(self.catalog, category, type_):
                    if len(variant) > len(longest[0]):
                        longest = (variant, ci, ti)
        variant_text, ci, ti = longest
        self.assertTrue(variant_text)

        markup = kb.build_variant_keyboard(self.catalog, ci, ti)
        found_long_label = False
        for btn in self._all_buttons(markup):
            if variant_text in btn.text:
                found_long_label = True
            if btn.callback_data:
                self.assertLessEqual(len(btn.callback_data.encode("utf-8")), 64)
        self.assertTrue(found_long_label)
        all_data = [b.callback_data for b in self._all_buttons(markup)]
        self.assertIn("catlist", all_data)
        self.assertIn(f"mvardone:{ci}:{ti}", all_data)

    def test_variant_keyboard_marks_selected_items_with_checkmark(self):
        categories = cl.get_categories(self.catalog)
        ci = categories.index("دخان")
        types_ = cl.get_types(self.catalog, "دخان")
        ti = types_.index("ماستر")
        markup = kb.build_variant_keyboard(self.catalog, ci, ti, selected={0})
        texts_by_data = {
            b.callback_data: b.text for b in self._all_buttons(markup) if b.callback_data.startswith("mvar:")
        }
        self.assertTrue(texts_by_data[f"mvar:{ci}:{ti}:0"].startswith("✅"))
        self.assertTrue(texts_by_data[f"mvar:{ci}:{ti}:1"].startswith("▫️"))

    def test_unit_keyboard_indices_match_catalog_order(self):
        categories = cl.get_categories(self.catalog)
        ci = categories.index("دخان")
        markup = kb.build_unit_keyboard(self.catalog, ci)
        units = cl.get_units(self.catalog, "دخان")
        data_to_label = {
            b.callback_data: b.text for b in self._all_buttons(markup) if b.callback_data != "back"
        }
        for ui, unit in enumerate(units):
            self.assertEqual(data_to_label[f"unit:{ci}:{ui}"], unit["name"])

    def test_all_callback_data_across_full_catalog_under_limit(self):
        """فحص شامل: كل شاشة نوع/صنف/وحدة بكل قسم — كلهم لازم يكونوا تحت الحد."""
        for ci, category in enumerate(cl.get_categories(self.catalog)):
            type_markup = kb.build_type_keyboard(self.catalog, ci)
            for btn in self._all_buttons(type_markup):
                self.assertLessEqual(len(btn.callback_data.encode("utf-8")), 64)

            for ti, type_ in enumerate(cl.get_types(self.catalog, category)):
                if cl.has_variants(self.catalog, category, type_):
                    variant_markup = kb.build_variant_keyboard(self.catalog, ci, ti)
                    for btn in self._all_buttons(variant_markup):
                        self.assertLessEqual(len(btn.callback_data.encode("utf-8")), 64)

            unit_markup = kb.build_unit_keyboard(self.catalog, ci)
            for btn in self._all_buttons(unit_markup):
                self.assertLessEqual(len(btn.callback_data.encode("utf-8")), 64)


class TestCartAndPaymentKeyboards(unittest.TestCase):
    def test_cart_keyboard_has_five_actions(self):
        markup = kb.build_cart_keyboard()
        data = [b.callback_data for row in markup.inline_keyboard for b in row]
        self.assertEqual(
            data,
            [
                "cart:add_more",
                "cart:undo",
                "cart:clear",
                "cart:price_inquiry",
                "cart:back_to_types",
            ],
        )

    def test_payment_keyboard_has_three_options(self):
        markup = kb.build_payment_keyboard()
        data = [b.callback_data for row in markup.inline_keyboard for b in row]
        self.assertEqual(data, ["pay:prepaid", "pay:deposit", "pay:cod"])

    def test_confirm_keyboard_has_confirm_and_cancel(self):
        markup = kb.build_confirm_keyboard()
        data = [b.callback_data for row in markup.inline_keyboard for b in row]
        self.assertEqual(data, ["confirm:yes", "confirm:no"])

    def test_cash_service_keyboard_has_shamcash_and_syriatelcash(self):
        markup = kb.build_cash_service_keyboard()
        data = [b.callback_data for row in markup.inline_keyboard for b in row]
        self.assertEqual(data, ["cash:shamcash", "cash:syriatelcash"])

    def test_idle_keyboard_has_continue_and_cancel(self):
        markup = kb.build_idle_keyboard()
        data = [b.callback_data for row in markup.inline_keyboard for b in row]
        self.assertEqual(data, ["idle:continue", "idle:cancel"])


if __name__ == "__main__":
    unittest.main()
