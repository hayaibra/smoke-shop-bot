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
        ("اختمار", "اختمار قصير"),
        ("اختمار", "اختمار طويل"),
        ("اوسكار", "اوسكار طويل"),
        ("اوسكار", "اوسكار كوين"),
        ("اوسكار", "اوسكار سليم"),
        ("اليغانس", "اليغانس اسود كرتون"),
        ("اليغانس", "اليغانس كوين"),
        ("اليغانس", "اليغانس طويل فضي غ م"),
        ("اليغانس", "اليغانس سليم مربع"),
        ("اوريس", "اوريس سليم"),
        ("اوريس", "اوريس كوين"),
        ("اوريس", "اوريس طقتين"),
        ("اوريس", "اوريس قصير بطيخ"),
        # التاجرة بسّطت "ماستر" من ٢٣ صنف لـ٧ بس — الـ١٧ الباقيين محذوفين.
        ("ماستر", "ماستر طويل ورق م"),
        ("ماستر", "ماستر قصير ازرق م"),
        ("ماستر", "ماستر كوين ابيض م"),
        ("ماستر", "ماستر سليم فضي م"),
        ("ماستر", "ماستر سليم بطيخ"),
        ("ماستر", "ماستر سليم بلوبيري"),
        ("ماستر", "ماستر سليم تفاح و نعنع"),
        ("ماستر", "ماستر سليم علكة ونعنع"),
        ("ماستر", "ماستر سليم نعنع مثلج"),
        ("ماستر", "ماستر طويل ورق"),
        ("ماستر", "ماستر طويل كرتون"),
        ("ماستر", "ماستر طقتين دبل ايس ميكس"),
        ("ماستر", "ماستر طقتين دبل سمر"),
        ("ماستر", "ماستر طقتين دبل فيوجين سمر"),
        ("ماستر", "ماستر طقتين دبل بلوسم فيوجين"),
        ("ماستر", "ماستر قصير فضي م"),
        ("ماستر", "ماستر سليم ازرق م"),
        ("تيرا", "تيرا بلو / سينا / اوسن بيرل حرة"),
        # ٥ أصناف اتحذفوا من "كابتن بلاك" (الاسم المباشر بدون "طويل/كوين"،
        # يعني ابيض/ازرق/ذهبي/سليم/مسلف) — باقي الماركة (طويل × ٤، كوين
        # وسيجار يلو) ضل زي ما هو.
        ("كابتن بلاك", "كابتن بلاك ابيض"),
        ("كابتن بلاك", "كابتن بلاك ازرق"),
        ("كابتن بلاك", "كابتن بلاك ذهبي"),
        ("كابتن بلاك", "كابتن بلاك سليم"),
        ("كابتن بلاك", "كابتن بلاك مسلف"),
        # "بلاتينيوم فضي طويل" (فضي قبل طويل) محذوف — بعكس "بلاتينيوم طويل
        # فضي" (طويل قبل فضي) يلي هو صنف تاني لحاله وضل موجود.
        ("بلاتينيوم", "بلاتينيوم فضي طويل"),
        # ٣ أصناف "هيستوري" بالاسم المجرد (بلا فضي/ازرق) محذوفة — الأصناف
        # المفصّلة (طويل فضي/ازرق، قصير فضي/ازرق، كوين، سليم فضي/نعنع) ضلت.
        ("هيستوري", "هيستوري طويل"),
        ("هيستوري", "هيستوري قصير"),
        ("هيستوري", "هيستوري سليم"),
        # ٣ أصناف محذوفة من "روز": طويل/قصير المجردين + "سليم كومفورت / عادي".
        ("روز", "روز طويل"),
        ("روز", "روز قصير"),
        ("روز", "روز سليم كومفورت / عادي"),
        # ماركة "1970": ٨ أصناف بصيغة "<وصف> 1970" (1970 بآخر الاسم) محذوفة —
        # الصيغة التانية المشابهة "1970 <وصف>" (1970 بأول الاسم) ضلت كاملة،
        # هني أصناف مختلفة تماماً بالكتالوج رغم تشابه الاسم.
        ("1970", "طويل فضي 1970"),
        ("1970", "طويل ازرق 1970"),
        ("1970", "قصير فضي 1970"),
        ("1970", "قصير ازرق 1970"),
        ("1970", "كوين فضي 1970"),
        ("1970", "سليم فضي 1970"),
        ("1970", "سليم نعنع 1970"),
        ("1970", "سليم ازرق 1970"),
        ("كلواز", "كلواز قصير حرة"),
        # صنفين محذوفين من "البرو": "برو فضي طويل" و"يرو ازرق طويل" (بالاسم
        # المطبوع بالكتالوج فعلاً، بلا تصحيح إملائي) — بعكس "برو طويل فضي"
        # و"برو طويل ازرق" (ترتيب كلمات معاكس) يلي هني أصناف تانية وضلوا.
        ("البرو", "برو فضي طويل"),
        ("البرو", "يرو ازرق طويل"),
        # ماركتين انحذفوا بالكامل: "كلواز عريض" و"مادوكس" (مو صنف واحد جواهن).
        # ملاحظة: أصناف "كلواز عريض" (احمر/اصفر عريض) أسماؤها نفس أسماء
        # أصناف موجودة بماركة "كلواز" (لسا ظاهرة هناك) — بس هني مجموعتين
        # منفصلتين تماماً بملف الأسعار (برند مختلف)، فما في تعارض.
        ("كلواز عريض", "كلواز احمر عريض"),
        ("كلواز عريض", "كلواز اصفر عريض"),
        ("مادوكس", "مادوكس كوين"),
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
            ("اختمار", "اختمار طويل"): 38,
            ("اختمار", "اختمار قصير"): 39,
            ("اوسكار", "اوسكار طويل"): 31,
            ("اوسكار", "اوسكار كوين"): 32,
            ("اوسكار", "اوسكار سليم"): 33,
            ("اليغانس", "اليغانس اسود كرتون"): 43,
            ("اليغانس", "اليغانس طويل فضي غ م"): 58,
            ("اليغانس", "اليغانس كوين"): 61,
            ("اليغانس", "اليغانس سليم مربع"): 64,
            ("اوريس", "اوريس سليم"): 80,
            ("اوريس", "اوريس طقتين"): 81,
            ("اوريس", "اوريس كوين"): 82,
            ("اوريس", "اوريس قصير بطيخ"): 83,
            ("ماستر", "ماستر طويل ورق م"): 163,
            ("ماستر", "ماستر قصير ازرق م"): 164,
            ("ماستر", "ماستر كوين ابيض م"): 167,
            ("ماستر", "ماستر سليم فضي م"): 168,
            ("ماستر", "ماستر سليم بطيخ"): 169,
            ("ماستر", "ماستر سليم بلوبيري"): 170,
            ("ماستر", "ماستر سليم تفاح و نعنع"): 171,
            ("ماستر", "ماستر سليم علكة ونعنع"): 172,
            ("ماستر", "ماستر سليم نعنع مثلج"): 173,
            ("ماستر", "ماستر طويل ورق"): 174,
            ("ماستر", "ماستر طويل كرتون"): 175,
            ("ماستر", "ماستر طقتين دبل ايس ميكس"): 180,
            ("ماستر", "ماستر طقتين دبل سمر"): 181,
            ("ماستر", "ماستر طقتين دبل فيوجين سمر"): 182,
            ("ماستر", "ماستر طقتين دبل بلوسم فيوجين"): 183,
            ("ماستر", "ماستر قصير فضي م"): 184,
            ("ماستر", "ماستر سليم ازرق م"): 185,
            ("تيرا", "تيرا بلو / سينا / اوسن بيرل حرة"): 99,
            ("كابتن بلاك", "كابتن بلاك ابيض"): 251,
            ("كابتن بلاك", "كابتن بلاك ازرق"): 252,
            ("كابتن بلاك", "كابتن بلاك ذهبي"): 253,
            ("كابتن بلاك", "كابتن بلاك سليم"): 254,
            ("كابتن بلاك", "كابتن بلاك مسلف"): 255,
            ("بلاتينيوم", "بلاتينيوم فضي طويل"): 288,
            ("هيستوري", "هيستوري طويل"): 193,
            ("هيستوري", "هيستوري قصير"): 194,
            ("هيستوري", "هيستوري سليم"): 195,
            ("روز", "روز طويل"): 342,
            ("روز", "روز قصير"): 343,
            ("روز", "روز سليم كومفورت / عادي"): 344,
            ("1970", "طويل فضي 1970"): 392,
            ("1970", "طويل ازرق 1970"): 393,
            ("1970", "قصير فضي 1970"): 394,
            ("1970", "قصير ازرق 1970"): 395,
            ("1970", "كوين فضي 1970"): 396,
            ("1970", "سليم فضي 1970"): 397,
            ("1970", "سليم نعنع 1970"): 398,
            ("1970", "سليم ازرق 1970"): 399,
            ("كلواز", "كلواز قصير حرة"): 389,
            ("البرو", "برو فضي طويل"): 432,
            ("البرو", "يرو ازرق طويل"): 433,
            ("كلواز عريض", "كلواز احمر عريض"): 505,
            ("كلواز عريض", "كلواز اصفر عريض"): 506,
            ("مادوكس", "مادوكس كوين"): 553,
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
        # باقي أصناف "اختمار" (٤ أصناف) ضلوا زي ما كانوا بالضبط.
        ekhtimar_items = [item for item in self.flat_items if item["brand"] == "اختمار"]
        self.assertEqual([item["name"] for item in ekhtimar_items], [
            "اختمار قصير ازرق", "اختمار قصير فضي", "اختمار سليم فضي",
            "اختمار طويل ازرق", "اختمار طويل", "اختمار قصير",
        ])
        # وباقي أصناف "اوسكار" (٣ أصناف) ضلوا زي ما كانوا بالضبط.
        oscar_items = [item for item in self.flat_items if item["brand"] == "اوسكار"]
        self.assertEqual([item["name"] for item in oscar_items], [
            "اوسكار طويل فضي", "اوسكار سليم فضي", "اوسكار كوين ازرق",
            "اوسكار طويل", "اوسكار كوين", "اوسكار سليم",
        ])
        # وباقي أصناف "اليغانس" (٢١ صنف) ضلوا زي ما كانوا بالضبط — ولا رقم تحرك.
        elegance_items = [item for item in self.flat_items if item["brand"] == "اليغانس"]
        self.assertEqual([item["name"] for item in elegance_items], [
            "اليغانس طويل فضي غ", "اليغانس قصير فضي", "اليغانس طويل اسود", "اليغانس اسود كرتون",
            "اليغانس سليم فضي", "اليغانس سليم ازرق", "اليغانس سليم ازرق مربع",
            "اليغانس سليم فضي مربع", "اليغانس سليم نعنع جديد", "اليغانس سليم نعنع قديم",
            "اليغانس قصير طقتين", "اليغانس كوين ازرق طقة", "اليغانس سليم طقة موف",
            "اليغانس سليم طقة ازرق", "اليغانس سليم شوكولا", "اليغانس سليم دهبي",
            "اليغانس كوين ازرق جديد", "اليغانس كوين ابيض جديد", "اليغانس طويل فضي غ م",
            "اليغانس قصير اسود", "اليغانس قصير ابيض", "اليغانس كوين",
            "اليغانس طويل فضي مخصص", "اليغانس سليم فضي ازرق نعنع قديم", "اليغانس سليم مربع",
        ])
        # وباقي أصناف "اوريس" (١٧ صنف) — بنفس الترتيب والفهرس، ما عدا صنف واحد
        # اتغيّر اسمه بس (بدون ما يتحرك مكانه/فهرسه): "اوريس طقة منغا غ" صار
        # اسمه "اوريس سليم طقة منغا" (تبديل بالمكان بملف الأسعار والكتالوج سوا،
        # مش حذف/إضافة — فهرس ٧٣ ضل زي ما هو).
        oris_items = [item for item in self.flat_items if item["brand"] == "اوريس"]
        self.assertEqual([item["name"] for item in oris_items], [
            "اوريس كوين توت طقة غ", "اوريس كوين فريز طقة غ", "اوريس كوين شوكولا غ",
            "اوريس كوين بطيخ غ", "طقة بلس ازرق جديد م", "اوريس سليم طقة منغا",
            "اوريس سليم طقة توت", "اوريس سليم شوكولا", "اوريس طقتين بلوبيري م",
            "اوريس تفاح", "اوريس طقتين نعنع م", "اوريس تشكلس", "اوريس سليم",
            "اوريس طقتين", "اوريس كوين", "اوريس قصير بطيخ", "اوريس كلاسيك ابيض",
        ])
        renamed_item = next(item for item in oris_items if item["name"] == "اوريس سليم طقة منغا")
        self.assertEqual(renamed_item["index"], 73)

        # "ماستر" (استبدال كامل، ٢٣ -> ٧ أصناف): الـ٢٣ القدام لسا موجودين بملف
        # الأسعار بمكانهن الأصلي (١٦٣-١٨٥) بلا أي حذف/تحريك، وصنف واحد جديد
        # ("ماستر طويل") انضاف كمجموعة جديدة بآخر الملف تماماً (فهرس ٥٧٩)
        # منشان صفر تأثير على أي فهرس تاني بالملف كلو.
        master_items = [item for item in self.flat_items if item["brand"] == "ماستر"]
        self.assertEqual(len(master_items), 24)  # ٢٣ قدام (orphans) + ١ جديد
        new_master_item = next(item for item in master_items if item["name"] == "ماستر طويل")
        self.assertEqual(new_master_item["index"], 579)
        self.assertEqual(new_master_item["default_price"], 0)

        # "تيرا": صنف واحد محذوف ("بلو / سينا / اوسن بيرل حرة" — لسا بمكانه
        # الأصلي فهرس ٩٩)، وصنف جديد كلياً ("تيرا تركواز") انضاف بآخر الملف
        # (فهرس ٥٨٠)، بلا سعر بعد.
        tera_items = [item for item in self.flat_items if item["brand"] == "تيرا"]
        self.assertEqual(len(tera_items), 9)  # ٨ قدام (منهم واحد orphan) + ١ جديد
        new_tera_item = next(item for item in tera_items if item["name"] == "تيرا تركواز")
        self.assertEqual(new_tera_item["index"], 580)
        self.assertEqual(new_tera_item["default_price"], 0)

        # "كابتن بلاك": ٥ أصناف محذوفة (ابيض/ازرق/ذهبي/سليم/مسلف) — لسا
        # بمكانهن الأصلي (٢٥١-٢٥٥)، وباقي الـ١٦ صنف (طويل × ٤ + كوين/سيجار
        # يلو) ضلوا زي ما كانوا بالضبط.
        captain_black_items = [item for item in self.flat_items if item["brand"] == "كابتن بلاك"]
        self.assertEqual([item["name"] for item in captain_black_items], [
            "كابتن بلاك طويل مانجو", "كابتن بلاك طويل شوكولا", "كابتن بلاك طويل تفاح",
            "كابتن بلاك طويل عنب", "كابتن كوين دهبي", "كابتن كوين ازرق", "كابتن كوين ون",
            "كابتن سليم فضي", "كابتن سلييم ازرق", "كابتن كوين ون اسود", "كابتن كوين ون ازرق",
            "سيجار يلو عنب", "سجار يلو سلفر", "سيجار يلو فريز", "سيجار يلو كرز",
            "كابتن بلاك ابيض", "كابتن بلاك ازرق", "كابتن بلاك ذهبي", "كابتن بلاك سليم",
            "كابتن بلاك مسلف", "سيجار يلو قهوة", "مادوكس",
        ])
        # صنف جديد كلياً ("مادوكس") انضاف لماركة "كابتن بلاك" — كمجموعة
        # جديدة بآخر ملف الأسعار (فهرس ٥٨١)، بلا سعر بعد.
        new_captain_black_item = next(item for item in captain_black_items if item["name"] == "مادوكس")
        self.assertEqual(new_captain_black_item["index"], 581)
        self.assertEqual(new_captain_black_item["default_price"], 0)

        # "بلاتينيوم": صنف واحد محذوف ("فضي طويل" — فهرس ٢٨٨)، والصنف
        # التاني المشابه بالاسم بس بترتيب كلمات معاكس ("طويل فضي" — فهرس
        # ٣٠٧) ضل موجود بلا أي تغيير (سعر مختلف: ٦٢٥٠٠ مش ٣٩٠٠٠).
        platinum_items = [item for item in self.flat_items if item["brand"] == "بلاتينيوم"]
        self.assertIn("بلاتينيوم طويل فضي", [item["name"] for item in platinum_items])
        kept_item = next(item for item in platinum_items if item["name"] == "بلاتينيوم طويل فضي")
        self.assertEqual(kept_item["index"], 307)
        self.assertEqual(kept_item["default_price"], 62500)

        # "هيستوري": ٣ أصناف محذوفة (طويل/قصير/سليم المجردين — فهارس
        # ١٩٣-١٩٥)، وباقي الـ٧ أصناف المفصّلة ضلت زي ما هي بالضبط.
        history_items = [item for item in self.flat_items if item["brand"] == "هيستوري"]
        self.assertEqual([item["name"] for item in history_items], [
            "هيستوري طويل فضي", "هيستوري طويل ازرق", "هيستوري قصير فضي", "هيستوري قصير ازرق",
            "هيستوري كوين", "هيستوري سليم فضي", "هيستوري سليم نعنع",
            "هيستوري طويل", "هيستوري قصير", "هيستوري سليم",
        ])

        # "روز": ٣ أصناف محذوفة (طويل/قصير المجردين + سليم كومفورت/عادي —
        # فهارس ٣٤٢-٣٤٤)، وباقي الـ٨ أصناف المفصّلة ضلت زي ما هي بالضبط.
        rose_items = [item for item in self.flat_items if item["brand"] == "روز"]
        self.assertEqual([item["name"] for item in rose_items], [
            "روز طويل فضي", "روز طويل ازرق", "روز سليم فضي", "روز قصير ازرق",
            "روز قصير كولد", "روز قصير ابيض", "روز سليم بلوبيري", "روز كلاسيك ابيض",
            "روز طويل", "روز قصير", "روز سليم كومفورت / عادي",
        ])

        # "1970": ٨ أصناف بصيغة "<وصف> 1970" محذوفة (فهارس ٣٩٢-٣٩٩)، وباقي
        # الـ١٢ صنف بصيغة "1970 <وصف>" ضلوا زي ما هم بالضبط.
        nineteen_seventy_items = [item for item in self.flat_items if item["brand"] == "1970"]
        self.assertEqual([item["name"] for item in nineteen_seventy_items], [
            "طويل فضي 1970", "طويل ازرق 1970", "قصير فضي 1970", "قصير ازرق 1970",
            "كوين فضي 1970", "سليم فضي 1970", "سليم نعنع 1970", "سليم ازرق 1970",
            "1970 قصير فضي", "1970 قصير ازرق", "1970 كوين ابيض", "1970 كوين ازرق",
            "1970 كوين اسود", "1970 سليم فضي", "1970 سليم ازرق", "1970 سليم نعنع",
            "1970 طويل فضي", "1970 طويل ازرق", "1970 كوين فضي", "1970 سليم فضي كراش",
        ])

        # "كلواز 8 S" -> "كلواز": تبديل اسم الماركة نفسا (مش صنف داخلها) —
        # الـ٥ أصناف الأصليين ضلوا بنفس فهارسهن الأصلية (٣٨٧-٣٩١) وأسعارهن
        # بملف الأسعار، بس برند الماركة صار "كلواز". بعدين حذفنا صنف واحد
        # منهن ("كلواز قصير حرة" — orphan بفهرسه ٣٨٩، شوف فوق) فضل ٤ أصناف
        # ظاهرين بالكتالوج.
        klewaz_items = [item for item in self.flat_items if item["brand"] == "كلواز"]
        self.assertEqual([item["name"] for item in klewaz_items], [
            "كلواز كوين أحمر 8 S", "كلواز كوين أصفر 8 S", "كلواز قصير حرة",
            "كلواز احمر عريض", "كلواز اصفر عريض",
        ])
        self.assertEqual([item["index"] for item in klewaz_items], [387, 388, 389, 390, 391])
        self.assertEqual(
            [item["default_price"] for item in klewaz_items],
            [78500, 78500, 112000, 112000, 112000],
        )
        self.assertFalse(any(item["brand"] == "كلواز 8 S" for item in self.flat_items))

        # "البرو": صنفين محذوفين (فهارس ٤٣٢-٤٣٣)، وباقي الـ١٦ صنف ضلوا زي ما
        # هم بالضبط — بما فيهن الصنفين المشابهين بالاسم بس بترتيب كلمات
        # معاكس ("برو طويل فضي"، "برو طويل ازرق").
        bro_items = [item for item in self.flat_items if item["brand"] == "البرو"]
        self.assertEqual([item["name"] for item in bro_items], [
            "برو فضي طويل", "يرو ازرق طويل", "برو كوين فضي", "برو طويل شوكولا",
            "برو طويل حليب", "برو طويل كرز", "برو كوين اسود", "برو فضي سليم",
            "برو طويل فضي", "برو طويل ازرق", "برو كوين كيلر", "برو ازرق هابي مانغو",
            "برو بل جيم", "برو هافانا", "برو طويل حليب ترينيدي", "برو طويل كرز موهيتو",
            "برو كوين اسود لوف", "برو سليم فضي بحريني",
        ])

        # "كلواز عريض" و"مادوكس": ماركتين انحذفوا بالكامل من الكتالوج —
        # أصنافهن لسا بمكانهن الأصلي بملف الأسعار (فهارس ٥٠٥-٥٠٦، ٥٥٣).
        klewaz_wide_flat = [item for item in self.flat_items if item["brand"] == "كلواز عريض"]
        self.assertEqual([item["name"] for item in klewaz_wide_flat], ["كلواز احمر عريض", "كلواز اصفر عريض"])
        madox_items = [item for item in self.flat_items if item["brand"] == "مادوكس"]
        self.assertEqual([item["name"] for item in madox_items], ["مادوكس كوين"])
        # ماركة "كلواز" (لحالها) ما تأثرت — لسا فيها نفس الاسمين ("كلواز
        # احمر/اصفر عريض") ضمن أصنافها هي.
        klewaz_items_after = [item for item in self.flat_items if item["brand"] == "كلواز"]
        self.assertEqual(
            [item["name"] for item in klewaz_items_after],
            ["كلواز كوين أحمر 8 S", "كلواز كوين أصفر 8 S", "كلواز قصير حرة", "كلواز احمر عريض", "كلواز اصفر عريض"],
        )

    def test_total_variant_count_matches_price_sheet_item_count_minus_known_orphans(self):
        total_variants = sum(
            len(cl.get_variants(self.catalog, category, type_))
            for category in cl.get_categories(self.catalog)
            for type_ in cl.get_types(self.catalog, category)
        )
        self.assertEqual(total_variants, len(self.flat_items) - len(self.ORPHANED_PRICE_SHEET_ITEMS))
        self.assertEqual(total_variants, 518)


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
