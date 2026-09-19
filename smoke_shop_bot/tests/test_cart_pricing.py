"""
اختبارات حساب سعر السلة تلقائياً — cart_pricing.py. ما بتحتاج مكتبة تلغرام
ولا شبكة إطلاقاً (منطق نقي متل باقي ملفات *_logic.py).
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cart_pricing as cp
import catalog_logic as cl
import price_sheet_logic as ps

CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "catalog.json"
PRICE_SHEET_PATH = Path(__file__).resolve().parent.parent / "data" / "price_sheet.json"


def _fake_catalog():
    return {
        "دخان": {
            "emoji": "🚬",
            "types": {"ماستر": ["ماستر طويل"]},
            "units": [
                {"name": "🎁 كروز", "fixed": False, "multiplier": 1},
                {"name": "🥡 نص كروز", "fixed": True, "multiplier": 0.5},
            ],
        },
        "معسل": {
            "emoji": "💨",
            "types": {"الفاخر": ["الفاخر علكة"]},
            "units": [{"name": "🧮 عدد", "fixed": False, "multiplier": 1}],
        },
    }


def _fake_flat_items():
    return [
        {"index": 0, "brand": "ماستر", "name": "ماستر طويل", "default_price": 60000},
        {"index": 1, "brand": "الفاخر", "name": "الفاخر علكة", "default_price": 100000},
        {"index": 2, "brand": "الفاخر", "name": "الفاخر بلا سعر", "default_price": 0},
    ]


class TestBuildPriceLookup(unittest.TestCase):
    def test_maps_brand_and_name_to_index(self):
        lookup = cp.build_price_lookup(_fake_flat_items())
        self.assertEqual(lookup[("ماستر", "ماستر طويل")], 0)
        self.assertEqual(lookup[("الفاخر", "الفاخر علكة")], 1)


class TestPriceCartItem(unittest.TestCase):
    def setUp(self):
        self.catalog = _fake_catalog()
        self.lookup = cp.build_price_lookup(_fake_flat_items())
        self.prices = {0: 60000, 1: 100000, 2: 0}

    def test_count_based_unit_multiplies_by_count(self):
        item = cl.format_cart_line("دخان", "ماستر", "ماستر طويل", "🎁 كروز", False, 3)
        price = cp.price_cart_item(item, self.catalog, self.lookup, self.prices)
        self.assertEqual(price, 180000)

    def test_fixed_half_unit_ignores_count_and_halves_price(self):
        item = cl.format_cart_line("دخان", "ماستر", "ماستر طويل", "🥡 نص كروز", True, None)
        price = cp.price_cart_item(item, self.catalog, self.lookup, self.prices)
        self.assertEqual(price, 30000)

    def test_quantity_only_category_multiplies_price_by_count_with_no_conversion(self):
        item = cl.format_cart_line("معسل", "الفاخر", "الفاخر علكة", "🧮 عدد", False, 2)
        price = cp.price_cart_item(item, self.catalog, self.lookup, self.prices)
        self.assertEqual(price, 200000)

    def test_unpriced_item_returns_none(self):
        item = cl.format_cart_line("معسل", "الفاخر", "الفاخر بلا سعر", "🧮 عدد", False, 1)
        price = cp.price_cart_item(item, self.catalog, self.lookup, self.prices)
        self.assertIsNone(price)

    def test_item_missing_from_price_sheet_returns_none(self):
        item = cl.format_cart_line("دخان", "ماستر", "صنف مش موجود إطلاقاً", "🎁 كروز", False, 1)
        price = cp.price_cart_item(item, self.catalog, self.lookup, self.prices)
        self.assertIsNone(price)


class TestHiddenCartonMultiplierPerBrand(unittest.TestCase):
    """
    كرتونة كوحدة اختيارية بس لماركات دخان محددة (حجم كرتونة معروف وثابت)، عن
    طريق "type_units" بالكتالوج — المضاعِف (مثلاً 40 كروز) بالخلفية بلا ما
    يظهر للزبون إطلاقاً، وماركات تانية (بلا type_units override) ما بيطلعلها
    خيار كرتونة أصلاً.
    """

    def setUp(self):
        self.catalog = {
            "دخان": {
                "emoji": "🚬",
                "types": {"ماستر": ["ماستر طويل"], "اليغانس": ["اليغانس سليم فضي"]},
                "units": [
                    {"name": "🎁 كروز", "fixed": False, "multiplier": 1},
                    {"name": "🥡 نص كروز", "fixed": True, "multiplier": 0.5},
                ],
                "type_units": {
                    "ماستر": [
                        {"name": "🎁 كروز", "fixed": False, "multiplier": 1},
                        {"name": "🥡 نص كروز", "fixed": True, "multiplier": 0.5},
                        {"name": "📦📦 كرتونة", "fixed": False, "multiplier": 40},
                    ]
                },
            }
        }
        self.lookup = cp.build_price_lookup(
            [
                {"index": 0, "brand": "ماستر", "name": "ماستر طويل", "default_price": 67000},
                {"index": 1, "brand": "اليغانس", "name": "اليغانس سليم فضي", "default_price": 50500},
            ]
        )
        self.prices = {0: 67000, 1: 50500}

    def test_brand_with_carton_override_computes_hidden_multiplier(self):
        item = cl.format_cart_line("دخان", "ماستر", "ماستر طويل", "📦📦 كرتونة", False, 2)
        price = cp.price_cart_item(item, self.catalog, self.lookup, self.prices)
        self.assertEqual(price, 67000 * 40 * 2)

    def test_brand_without_carton_override_has_no_carton_unit_available(self):
        units = cl.get_units(self.catalog, "دخان", "اليغانس")
        self.assertNotIn("📦📦 كرتونة", {u["name"] for u in units})


class TestPriceCart(unittest.TestCase):
    def setUp(self):
        self.catalog = _fake_catalog()
        self.lookup = cp.build_price_lookup(_fake_flat_items())
        self.prices = {0: 60000, 1: 100000, 2: 0}

    def test_all_priced_returns_line_prices_and_total(self):
        cart = [
            cl.format_cart_line("دخان", "ماستر", "ماستر طويل", "🎁 كروز", False, 3),
            cl.format_cart_line("معسل", "الفاخر", "الفاخر علكة", "🧮 عدد", False, 2),
        ]
        result = cp.price_cart(cart, self.catalog, self.lookup, self.prices)
        self.assertEqual(result, ([180000, 200000], 380000))

    def test_one_unpriced_item_makes_whole_cart_none(self):
        # منشان نرجع للمسار اليدوي (استفسار عادي للتاجر) بدل ما نعرض سعر ناقص.
        cart = [
            cl.format_cart_line("دخان", "ماستر", "ماستر طويل", "🎁 كروز", False, 3),
            cl.format_cart_line("معسل", "الفاخر", "الفاخر بلا سعر", "🧮 عدد", False, 1),
        ]
        result = cp.price_cart(cart, self.catalog, self.lookup, self.prices)
        self.assertIsNone(result)

    def test_empty_cart_returns_empty_lines_and_zero_total(self):
        self.assertEqual(cp.price_cart([], self.catalog, self.lookup, self.prices), ([], 0))


class TestRealCatalogAndPriceSheetConsistency(unittest.TestCase):
    """
    اختبار تكامل: كل (نوع، صنف) موجود فعلياً بـ data/catalog.json لازم يكون إلو
    (برند، اسم) مطابق تماماً بـ data/price_sheet.json — هاد أهم ضمانة إن حساب
    السعر التلقائي رح يلاقي كل صنف رجوع بالفعل، لأي زبون حقيقي بيستخدم البوت.
    """

    def setUp(self):
        self.catalog = cl.load_catalog(CATALOG_PATH)
        flat_items = ps.flatten_items(ps.load_price_sheet(PRICE_SHEET_PATH))
        self.lookup = cp.build_price_lookup(flat_items)
        self.flat_items = flat_items

    def test_every_catalog_variant_has_a_matching_price_sheet_entry(self):
        missing = []
        for category in cl.get_categories(self.catalog):
            for type_ in cl.get_types(self.catalog, category):
                for variant in cl.get_variants(self.catalog, category, type_):
                    if (type_, variant) not in self.lookup:
                        missing.append((category, type_, variant))
        self.assertEqual(missing, [])

    def test_every_price_sheet_item_has_a_matching_catalog_variant(self):
        # بالاتجاه المعاكس كمان: ما في صنف بملف الأسعار ضايع وما وصل الكتالوج.
        catalog_pairs = set()
        for category in cl.get_categories(self.catalog):
            for type_ in cl.get_types(self.catalog, category):
                for variant in cl.get_variants(self.catalog, category, type_):
                    catalog_pairs.add((type_, variant))
        missing = [
            (item["brand"], item["name"])
            for item in self.flat_items
            if (item["brand"], item["name"]) not in catalog_pairs
        ]
        self.assertEqual(missing, [])

    def test_total_variant_count_matches_price_sheet_item_count(self):
        total_variants = sum(
            len(cl.get_variants(self.catalog, category, type_))
            for category in cl.get_categories(self.catalog)
            for type_ in cl.get_types(self.catalog, category)
        )
        self.assertEqual(total_variants, len(self.flat_items))
        self.assertEqual(total_variants, 582)


if __name__ == "__main__":
    unittest.main()
