"""
اختبارات منطق الكتالوج والسلة — تشغيل: python -m unittest discover tests
ما بتحتاج توكن ولا شبكة إطلاقاً.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import catalog_logic as cl

CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "catalog.json"


class TestCatalogLoading(unittest.TestCase):
    def setUp(self):
        self.catalog = cl.load_catalog(CATALOG_PATH)

    def test_categories_order(self):
        self.assertEqual(
            cl.get_categories(self.catalog), ["دخان", "معسل", "قداحات", "فيبات"]
        )

    def test_category_button_label(self):
        self.assertEqual(cl.category_button_label(self.catalog, "دخان"), "🚬 دخان")
        self.assertEqual(cl.category_button_label(self.catalog, "معسل"), "💨 معسل")

    def test_types_of_section(self):
        self.assertIn("ماستر", cl.get_types(self.catalog, "دخان"))
        self.assertIn("حمراء", cl.get_types(self.catalog, "دخان"))

    def test_variants_present(self):
        variants = cl.get_variants(self.catalog, "دخان", "ماستر")
        self.assertIn("ماستر طويل", variants)
        self.assertEqual(len(variants), 8)

    def test_variants_empty_for_type_without_subitems(self):
        variants = cl.get_variants(self.catalog, "دخان", "حمراء")
        self.assertEqual(variants, [])
        self.assertFalse(cl.has_variants(self.catalog, "دخان", "حمراء"))

    def test_units_fixed_flag(self):
        units = cl.get_units(self.catalog, "دخان")
        names = {u["name"]: u["fixed"] for u in units}
        self.assertTrue(names["🥡 نص كروز"])
        self.assertFalse(names["📦 باكيت"])

    def test_is_unit_fixed_helper(self):
        self.assertTrue(cl.is_unit_fixed(self.catalog, "دخان", "🥡 نص كروز"))
        self.assertFalse(cl.is_unit_fixed(self.catalog, "دخان", "📦 باكيت"))


class TestParseCount(unittest.TestCase):
    def test_valid_western_digits(self):
        self.assertEqual(cl.parse_count("3"), 3)
        self.assertEqual(cl.parse_count("  12 "), 12)

    def test_valid_arabic_digits(self):
        self.assertEqual(cl.parse_count("٣"), 3)
        self.assertEqual(cl.parse_count("١٢"), 12)

    def test_invalid_inputs_return_none(self):
        self.assertIsNone(cl.parse_count("ثلاثة"))
        self.assertIsNone(cl.parse_count(""))
        self.assertIsNone(cl.parse_count("0"))
        self.assertIsNone(cl.parse_count("-5"))
        self.assertIsNone(cl.parse_count("3.5"))
        self.assertIsNone(cl.parse_count(None))


class TestQuantityFormatting(unittest.TestCase):
    def test_countable_unit(self):
        self.assertEqual(cl.format_quantity("باكيت", False, 3), "3 باكيت")

    def test_fixed_unit_ignores_count(self):
        self.assertEqual(cl.format_quantity("نص كروز", True), "نص كروز")

    def test_countable_unit_without_count_raises(self):
        with self.assertRaises(ValueError):
            cl.format_quantity("باكيت", False, None)


class TestCartOperations(unittest.TestCase):
    def test_add_to_cart_with_variant(self):
        line = cl.format_cart_line("دخان", "ماستر", "ماستر طويل", "3 باكيت")
        self.assertEqual(line, "▫️ دخان – ماستر – ماستر طويل – 3 باكيت")
        cart, backup = cl.add_to_cart([], line)
        self.assertEqual(cart, [line])
        self.assertEqual(backup, [])

    def test_add_to_cart_without_variant(self):
        line = cl.format_cart_line("قداحات", "زيبو", None, "قطعة مفردة")
        self.assertEqual(line, "▫️ قداحات – زيبو – قطعة مفردة")

    def test_added_summary_without_variant(self):
        summary = cl.format_added_summary("زيبو", None, "قطعة مفردة")
        self.assertEqual(summary, "زيبو – قطعة مفردة")

    def test_undo_last_reverts_one_step_only(self):
        line1 = cl.format_cart_line("دخان", "ماستر", "ماستر طويل", "3 باكيت")
        cart1, backup1 = cl.add_to_cart([], line1)
        line2 = cl.format_cart_line("معسل", "الفاخر", "تفاحتين", "2 علبة ٥٠غ")
        cart2, backup2 = cl.add_to_cart(cart1, line2)

        self.assertEqual(cart2, [line1, line2])
        reverted = cl.undo_last(backup2)
        self.assertEqual(reverted, [line1])

    def test_clear_cart(self):
        cart, backup = cl.clear_cart()
        self.assertEqual(cart, [])
        self.assertEqual(backup, [])

    def test_format_cart_text_empty(self):
        self.assertEqual(cl.format_cart_text([]), "(السلة لسا فاضية)")

    def test_format_cart_text_joins_lines(self):
        text = cl.format_cart_text(["▫️ أ", "▫️ ب"])
        self.assertEqual(text, "▫️ أ\n▫️ ب")


if __name__ == "__main__":
    unittest.main()
