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


class TestHiddenCartonMultiplierPerVariant(unittest.TestCase):
    """
    كرتونة الفحم — بعكس كرتونة الدخان (يلي بتنطبق عالماركة كلها) — بتنطبق على
    صنف وحد محدد بس جوا الماركة (متلاً "فحم كيلو" بس، مش "فحم نص كيلو")،
    عن طريق "variant_units" بالكتالوج.
    """

    def setUp(self):
        self.catalog = {
            "فحم": {
                "emoji": "🔥",
                "types": {"ماركة فحم": ["فحم كيلو", "فحم نص كيلو"]},
                "units": [{"name": "🧮 عدد", "fixed": False, "multiplier": 1}],
                "variant_units": {
                    "ماركة فحم": {
                        "فحم كيلو": [
                            {"name": "🧮 عدد", "fixed": False, "multiplier": 1},
                            {"name": "📦📦 كرتونة", "fixed": False, "multiplier": 10},
                        ]
                    }
                },
            }
        }
        self.lookup = cp.build_price_lookup(
            [
                {"index": 0, "brand": "ماركة فحم", "name": "فحم كيلو", "default_price": 30000},
                {"index": 1, "brand": "ماركة فحم", "name": "فحم نص كيلو", "default_price": 16000},
            ]
        )
        self.prices = {0: 30000, 1: 16000}

    def test_variant_with_carton_override_computes_hidden_multiplier(self):
        item = cl.format_cart_line("فحم", "ماركة فحم", "فحم كيلو", "📦📦 كرتونة", False, 3)
        price = cp.price_cart_item(item, self.catalog, self.lookup, self.prices)
        self.assertEqual(price, 30000 * 10 * 3)

    def test_sibling_variant_without_override_has_no_carton_unit_available(self):
        units = cl.get_units(self.catalog, "فحم", "ماركة فحم", "فحم نص كيلو")
        self.assertNotIn("📦📦 كرتونة", {u["name"] for u in units})


class TestHalfCartonFixedUnitForCharcoal(unittest.TestCase):
    """
    بعض أصناف الفحم (متلا "فحم سيبروس كيلو") إلها 3 وحدات عبر "variant_units":
    كرتونة (10 علب، مش ثابتة — الزبون بيحدد كم كرتونة)، نص كرتونة (وحدة ثابتة =
    نص الكرتونة تماماً = 5 علب، بلا ما تطلب عدد)، وعدد (عدد محدد من العلب،
    مضاعِف 1). هالاختبار بيتأكد إن نص الكرتونة فعلاً نص سعر الكرتونة بالضبط،
    وإنها ما بتتأثر بالعدد إطلاقاً (وحدة ثابتة).
    """

    def setUp(self):
        self.catalog = {
            "فحم": {
                "emoji": "🔥",
                "types": {"سيبروس": ["فحم سيبروس كيلو"]},
                "units": [{"name": "🧮 عدد", "fixed": False, "multiplier": 1}],
                "variant_units": {
                    "سيبروس": {
                        "فحم سيبروس كيلو": [
                            {"name": "📦📦 كرتونة", "fixed": False, "multiplier": 10},
                            {"name": "🥡 نص كرتونة", "fixed": True, "multiplier": 5},
                            {"name": "🧮 عدد", "fixed": False, "multiplier": 1},
                        ]
                    }
                },
            }
        }
        self.lookup = cp.build_price_lookup(
            [{"index": 0, "brand": "سيبروس", "name": "فحم سيبروس كيلو", "default_price": 31500}]
        )
        self.prices = {0: 31500}

    def test_full_carton_multiplies_by_ten_and_count(self):
        item = cl.format_cart_line("فحم", "سيبروس", "فحم سيبروس كيلو", "📦📦 كرتونة", False, 2)
        price = cp.price_cart_item(item, self.catalog, self.lookup, self.prices)
        self.assertEqual(price, 31500 * 10 * 2)

    def test_half_carton_is_exactly_half_of_full_carton_and_ignores_count(self):
        full_carton = cp.price_cart_item(
            cl.format_cart_line("فحم", "سيبروس", "فحم سيبروس كيلو", "📦📦 كرتونة", False, 1),
            self.catalog,
            self.lookup,
            self.prices,
        )
        half_carton = cp.price_cart_item(
            cl.format_cart_line("فحم", "سيبروس", "فحم سيبروس كيلو", "🥡 نص كرتونة", True, None),
            self.catalog,
            self.lookup,
            self.prices,
        )
        self.assertEqual(half_carton, full_carton / 2)
        self.assertEqual(half_carton, 31500 * 5)

    def test_specific_count_unit_still_available_at_single_bag_price(self):
        item = cl.format_cart_line("فحم", "سيبروس", "فحم سيبروس كيلو", "🧮 عدد", False, 3)
        price = cp.price_cart_item(item, self.catalog, self.lookup, self.prices)
        self.assertEqual(price, 31500 * 3)


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

    استثناءات متعمَّدة: أصناف التاجرة طلبت حذفها نهائياً من الكتالوج (ما عادوا
    يظهروا/ينختاروا بالبوت إطلاقاً)، بس تركناهن هني بمكانهن بالضبط بملف
    price_sheet.json (بلا حذف السطر ولا تحريكه) منشان رقمهن (index) يضل زي ما
    هو ورقم كل صنف بعدهن ما يتحرك — لأن لو تحرك ممكن يخرب أي سعر محفوظ سابقاً
    عبر /setprices (محفوظ بالرسالة المثبتة برقم الصنف بالضبط).
    """

    ORPHANED_PRICE_SHEET_ITEMS = {
        ("نابولي", "نابولي قصير سفر"),
        ("ون شيستر", "ونشستر سليم"),
        ("ون شيستر", "ونشستر كوين"),
        ("ون شيستر", "ون شيستر كوين سيلفر"),
        ("ون شيستر", "ون شيستر سليم ابيض دهبي"),
        # ماركة "جتان" بالكامل انحذفت من الكتالوج (مو صنف واحد جواها) —
        # بلا ما تأثر ماركة "جيتان" (لحالها تماماً، لسا موجودة).
        ("جتان", "جتان قصير"),
        ("جتان", "جتان كوين"),
    }

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

    def test_every_price_sheet_item_has_a_matching_catalog_variant_or_is_a_known_orphan(self):
        # بالاتجاه المعاكس كمان: ما في صنف بملف الأسعار ضايع وما وصل الكتالوج،
        # ما عدا الاستثناء الموثّق فوق (ORPHANED_PRICE_SHEET_ITEMS).
        catalog_pairs = set()
        for category in cl.get_categories(self.catalog):
            for type_ in cl.get_types(self.catalog, category):
                for variant in cl.get_variants(self.catalog, category, type_):
                    catalog_pairs.add((type_, variant))
        missing = [
            (item["brand"], item["name"])
            for item in self.flat_items
            if (item["brand"], item["name"]) not in catalog_pairs
            and (item["brand"], item["name"]) not in self.ORPHANED_PRICE_SHEET_ITEMS
        ]
        self.assertEqual(missing, [])

    def test_orphaned_items_still_sit_at_their_original_index_untouched(self):
        # هاد الفحص الأهم: التأكد إن كل الأصناف المحذوفة من الكتالوج لسا بمكانها
        # تماماً بملف price_sheet.json (نفس الفهرس، نفس السعر) — يعني ولا صنف
        # تاني بعدها تحرك رقمه.
        expected_indexes = {
            ("نابولي", "نابولي قصير سفر"): 17,
            ("ون شيستر", "ونشستر كوين"): 6,
            ("ون شيستر", "ونشستر سليم"): 7,
            ("ون شيستر", "ون شيستر كوين سيلفر"): 9,
            ("ون شيستر", "ون شيستر سليم ابيض دهبي"): 12,
            ("جتان", "جتان قصير"): 539,
            ("جتان", "جتان كوين"): 540,
        }
        for key, expected_idx in expected_indexes.items():
            orphan = next(item for item in self.flat_items if (item["brand"], item["name"]) == key)
            self.assertEqual(orphan["index"], expected_idx, msg=key)

        # وباقي أصناف نابولي (دهبي/فضي/احمر) وون شيستر (٦ أصناف) ضلوا زي ما كانوا بالضبط.
        naboli_items = [item for item in self.flat_items if item["brand"] == "نابولي"]
        self.assertEqual([item["name"] for item in naboli_items], [
            "نابولي قصير دهبي", "نابولي قصير فضي", "نابولي قصير احمر", "نابولي قصير سفر",
        ])
        winchester_items = [item for item in self.flat_items if item["brand"] == "ون شيستر"]
        self.assertEqual([item["name"] for item in winchester_items], [
            "ون شيستر كوين فضي", "ون شيستر كوين ازرق", "ونشستر كوين", "ونشستر سليم",
            "ون شيستر كوين دهبي", "ون شيستر كوين سيلفر", "ون شيستر سليم اسود",
            "ون شيستر سليم ازرق", "ون شيستر سليم ابيض دهبي", "ون شيستر سليم فضي",
        ])
        # "جيتان" (ماركة لحالها) ما تأثرت إطلاقاً.
        gitane_items = [item for item in self.flat_items if item["brand"] == "جيتان"]
        self.assertEqual([item["name"] for item in gitane_items], ["جيتان قصير"])

    def test_total_variant_count_matches_price_sheet_item_count_minus_known_orphans(self):
        total_variants = sum(
            len(cl.get_variants(self.catalog, category, type_))
            for category in cl.get_categories(self.catalog)
            for type_ in cl.get_types(self.catalog, category)
        )
        self.assertEqual(total_variants, len(self.flat_items) - len(self.ORPHANED_PRICE_SHEET_ITEMS))
        self.assertEqual(total_variants, 572)


class TestRealCatalogCharcoalCartonUnits(unittest.TestCase):
    """
    اختبار تكامل: كل صنف فحم (أي برند، أي وزن) لازم يطلعلو خيار كرتونة/نص
    كرتونة بالإضافة لـ"عدد" — أصناف الكيلو الكامل (كيلو / 1 كغ / 1000 غ) عندها
    كرتونة = 10 علب، وباقي الأوزان (نص كيلو، ربع كيلو، 250غ، 400غ، 500غ، أو بلا
    وزن مكتوب بالاسم أصلاً) عندها الكرتونة القياسية = 50 (نفس القياسي المعتمد
    بباقي الأقسام).
    """

    # (برند، صنف) -> مضاعِف الكرتونة المتوقع لهالصنف بالضبط.
    EXPECTED_CARTON_MULTIPLIER = {
        ("سيبروس", "فحم سيبروس كيلو"): 10,
        ("الزعيم", "فحم الزعيم نصف كيلو"): 50,
        ("الزعيم", "فحم الزعيم كيلو"): 10,
        ("الزعيم", "فحم الزعيم 500 غ"): 50,
        ("الزعيم", "فحم الزعيم 250 غ"): 50,
        ("الزعيم", "فحم الزعيم 400 غ"): 50,
        ("الزعيم", "فحم الزعيم 1000 غ"): 10,
        ("الزعيم", "فحم الزعيم 1 كغ"): 10,
        ("ايكو نارا", "فحم إيكو نارا"): 50,
        ("ايكو نارا", "فحم ايكو نارا اخضر احمر"): 50,
        ("هورس", "فحم هورس 250 غ"): 50,
        ("سارا", "فحم سارا"): 50,
        ("سارا", "فحم سارا جوز هند"): 50,
        ("يحيى كريستال", "فحم يحيى كريستال 1000 غ"): 10,
        ("الرشيد", "فحم الرشيد 500 غ"): 50,
        ("الاغا", "فحم الاغا 1 كغ"): 10,
        ("بيروتي", "فحم بيروتي 1 كغ"): 10,
        ("كوكو 8", "فحم كوكو 8 1 كغ"): 10,
        ("دراغون", "فحم دراغون ربع كيلو"): 50,
        ("ولف", "فحم ولف ربع كيلو"): 50,
        ("اتش انش", "فحم اتش انش ربع كيلو"): 50,
        ("فحم برو", "فحم برو"): 50,
        ("فحم برو", "فحم برو 250 غ"): 50,
        ("فحم برو", "فحم برو 1 كغ"): 10,
        ("فحم برو", "فحم برو ربع كيلو"): 50,
    }

    def setUp(self):
        self.catalog = cl.load_catalog(CATALOG_PATH)

    def test_every_charcoal_variant_has_carton_half_carton_and_count_units(self):
        for category in cl.get_categories(self.catalog):
            if category != "فحم":
                continue
            for type_ in cl.get_types(self.catalog, category):
                for variant in cl.get_variants(self.catalog, category, type_):
                    key = (type_, variant)
                    self.assertIn(key, self.EXPECTED_CARTON_MULTIPLIER, msg=f"صنف فحم جديد بلا تصنيف: {key}")

        for (brand, item_name), carton_mult in self.EXPECTED_CARTON_MULTIPLIER.items():
            units = cl.get_units(self.catalog, "فحم", brand, item_name)
            by_name = {u["name"]: u for u in units}
            self.assertEqual(
                set(by_name), {"📦📦 كرتونة", "🥡 نص كرتونة", "🧮 عدد"}, msg=f"{brand} / {item_name}"
            )
            self.assertEqual(by_name["📦📦 كرتونة"]["multiplier"], carton_mult, msg=f"{brand} / {item_name}")
            self.assertFalse(by_name["📦📦 كرتونة"]["fixed"])
            self.assertEqual(
                by_name["🥡 نص كرتونة"]["multiplier"], carton_mult / 2, msg=f"{brand} / {item_name}"
            )
            self.assertTrue(by_name["🥡 نص كرتونة"]["fixed"])
            self.assertEqual(by_name["🧮 عدد"]["multiplier"], 1)
            self.assertFalse(by_name["🧮 عدد"]["fixed"])


if __name__ == "__main__":
    unittest.main()
