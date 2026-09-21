"""
اختبارات prices_state.py — بس الأجزاء الجديدة: CATEGORY_OF_BRAND (يلي بيربط كل
برند بقسمه من data/catalog.json، منشان قائمة "/prices" للزبون تنعرض منظمة
هرمياً قسم ← برند ← صنف)، و visible_flat_items() (يلي بيفلتر أي صنف "محذوف"
[orphan] — موجود بملف price_sheet.json بس مو موجود بالكتالوج — منشان ما يظهر
للزبون بقائمة الأسعار رغم إنه ما منقدر نبيعه عبر البوت). باقي الملف
(FLAT_ITEMS/overrides) غلاف رقيق فوق price_sheet_logic.py، مغطى أصلاً بـ
test_price_sheet_logic.py.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import prices_state


class TestCategoryOfBrand(unittest.TestCase):
    def test_every_brand_in_visible_flat_items_has_a_category(self):
        # كل برند لسا ظاهر (يعني بالكتالوج فعلياً) لازم يكون إلو قسم — هاد يلي
        # فعلياً منستخدمه سوا بقوائم الأسعار يلي بتوصل الزبون (شوف visible_flat_items).
        brands = {item["brand"] for item in prices_state.visible_flat_items()}
        missing = brands - set(prices_state.CATEGORY_OF_BRAND)
        self.assertEqual(missing, set())

    def test_known_brands_map_to_expected_categories(self):
        self.assertEqual(prices_state.CATEGORY_OF_BRAND["ماستر"], "🚬 دخان")
        self.assertEqual(prices_state.CATEGORY_OF_BRAND["معسل مزايا"], "💨 معسل")
        self.assertEqual(prices_state.CATEGORY_OF_BRAND["الزعيم"], "🔥 فحم")
        self.assertEqual(prices_state.CATEGORY_OF_BRAND["مباسم"], "🧰 إكسسوارات")
        self.assertEqual(
            prices_state.CATEGORY_OF_BRAND["اراكيل الكترونية برو"], "🔋 اراكيل الكترونية"
        )


class TestVisibleFlatItems(unittest.TestCase):
    """
    أصناف اتحذفت من الكتالوج بس تركناها بمكانها بملف price_sheet.json (منشان
    ترقيم باقي الأصناف ما يتحرك، شوف tests/test_cart_pricing.py) لازم تختفي من
    visible_flat_items() — وإلا ضلت تظهر بقائمة "/prices"/النشرة اليومية
    كأنها لسا للبيع، رغم إنه ما منقدر نضيفها للسلة عبر البوت إطلاقاً.
    """

    def test_orphaned_items_are_excluded(self):
        visible_pairs = {(item["brand"], item["name"]) for item in prices_state.visible_flat_items()}
        orphans = [
            ("نابولي", "نابولي قصير سفر"),
            ("ون شيستر", "ونشستر سليم"),
            ("ون شيستر", "ونشستر كوين"),
            ("ون شيستر", "ون شيستر كوين سيلفر"),
            ("ون شيستر", "ون شيستر سليم ابيض دهبي"),
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
            ("كابتن بلاك", "كابتن بلاك ابيض"),
            ("كابتن بلاك", "كابتن بلاك ازرق"),
            ("كابتن بلاك", "كابتن بلاك ذهبي"),
            ("كابتن بلاك", "كابتن بلاك سليم"),
            ("كابتن بلاك", "كابتن بلاك مسلف"),
            ("بلاتينيوم", "بلاتينيوم فضي طويل"),
            ("هيستوري", "هيستوري طويل"),
            ("هيستوري", "هيستوري قصير"),
            ("هيستوري", "هيستوري سليم"),
            ("روز", "روز طويل"),
            ("روز", "روز قصير"),
            ("روز", "روز سليم كومفورت / عادي"),
            ("1970", "طويل فضي 1970"),
            ("1970", "طويل ازرق 1970"),
            ("1970", "قصير فضي 1970"),
            ("1970", "قصير ازرق 1970"),
            ("1970", "كوين فضي 1970"),
            ("1970", "سليم فضي 1970"),
            ("1970", "سليم نعنع 1970"),
            ("1970", "سليم ازرق 1970"),
            ("كلواز", "كلواز قصير حرة"),
            ("البرو", "برو فضي طويل"),
            ("البرو", "يرو ازرق طويل"),
            ("كلواز عريض", "كلواز احمر عريض"),
            ("كلواز عريض", "كلواز اصفر عريض"),
            ("مادوكس", "مادوكس كوين"),
        ]
        for pair in orphans:
            self.assertNotIn(pair, visible_pairs, msg=pair)

    def test_non_orphaned_items_still_present_with_original_index(self):
        visible_by_pair = {(item["brand"], item["name"]): item for item in prices_state.visible_flat_items()}
        self.assertIn(("نابولي", "نابولي قصير دهبي"), visible_by_pair)
        self.assertIn(("ون شيستر", "ون شيستر كوين فضي"), visible_by_pair)
        self.assertIn(("جيتان", "جيتان قصير"), visible_by_pair)
        # الفهرس (index) ما تغير — لسا نفس رقمه الأصلي بملف price_sheet.json.
        self.assertEqual(visible_by_pair[("جيتان", "جيتان قصير")]["index"], 0)
        # صنف "ماستر" الجديد (المضاف بآخر price_sheet.json) ظاهر برقمه الجديد.
        self.assertEqual(visible_by_pair[("ماستر", "ماستر طويل")]["index"], 579)
        # صنف "تيرا تركواز" الجديد (المضاف بآخر price_sheet.json) ظاهر برقمه الجديد.
        self.assertIn(("تيرا", "تيرا تركواز"), visible_by_pair)
        self.assertEqual(visible_by_pair[("تيرا", "تيرا تركواز")]["index"], 580)

    def test_visible_count_is_full_count_minus_orphans(self):
        self.assertEqual(len(prices_state.visible_flat_items()), len(prices_state.FLAT_ITEMS) - 64)


if __name__ == "__main__":
    unittest.main()
