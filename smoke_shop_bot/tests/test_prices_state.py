"""
اختبارات prices_state.py — بس الجزء الجديد (CATEGORY_OF_BRAND)، يلي بيربط كل
برند بقسمه من data/catalog.json، منشان قائمة "/prices" للزبون تنعرض منظمة
هرمياً (قسم ← برند ← صنف). باقي الملف (FLAT_ITEMS/overrides) غلاف رقيق فوق
price_sheet_logic.py، مغطى أصلاً بـ test_price_sheet_logic.py.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import prices_state


class TestCategoryOfBrand(unittest.TestCase):
    def test_every_brand_in_flat_items_has_a_category(self):
        brands = {item["brand"] for item in prices_state.FLAT_ITEMS}
        missing = brands - set(prices_state.CATEGORY_OF_BRAND)
        self.assertEqual(missing, set())

    def test_known_brands_map_to_expected_categories(self):
        self.assertEqual(prices_state.CATEGORY_OF_BRAND["ماستر"], "🚬 دخان")
        self.assertEqual(prices_state.CATEGORY_OF_BRAND["معسل مزايا"], "💨 معسل")
        self.assertEqual(prices_state.CATEGORY_OF_BRAND["فحم"], "🔥 فحم")
        self.assertEqual(prices_state.CATEGORY_OF_BRAND["مباسم"], "🧰 إكسسوارات")
        self.assertEqual(
            prices_state.CATEGORY_OF_BRAND["اراكيل الكترونية برو"], "🔋 اراكيل الكترونية"
        )


if __name__ == "__main__":
    unittest.main()
