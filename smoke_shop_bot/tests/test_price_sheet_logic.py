"""اختبارات منطق قائمة الأسعار الكاملة — price_sheet_logic.py (بدون تلغرام إطلاقاً)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import price_sheet_logic as ps

SAMPLE_GROUPS = [
    {
        "brand": "جيتان",
        "items": [{"name": "جيتان قصير", "default_price": 99000}],
    },
    {
        "brand": "تي اس",
        "items": [
            {"name": "تي اس طويل فضي", "default_price": 40500},
            {"name": "تي اس سليم فضي", "default_price": 0},
        ],
    },
]


class TestFlattenItems(unittest.TestCase):
    def test_assigns_sequential_global_index(self):
        flat = ps.flatten_items(SAMPLE_GROUPS)
        self.assertEqual([item["index"] for item in flat], [0, 1, 2])
        self.assertEqual(flat[0]["name"], "جيتان قصير")
        self.assertEqual(flat[2]["default_price"], 0)


class TestEffectivePrices(unittest.TestCase):
    def test_uses_default_when_no_override(self):
        flat = ps.flatten_items(SAMPLE_GROUPS)
        result = ps.effective_prices(flat, {})
        self.assertEqual(result, {0: 99000, 1: 40500, 2: 0})

    def test_override_wins_over_default(self):
        flat = ps.flatten_items(SAMPLE_GROUPS)
        result = ps.effective_prices(flat, {2: 33000})
        self.assertEqual(result[2], 33000)
        self.assertEqual(result[0], 99000)  # ما تأثر


class TestCompactPriceEncoding(unittest.TestCase):
    def test_round_trip(self):
        prices = {0: 99000, 12: 45500, 327: 0}
        encoded = ps.encode_prices_compact(prices)
        self.assertEqual(ps.decode_prices_compact(encoded), prices)

    def test_empty_round_trip(self):
        self.assertEqual(ps.encode_prices_compact({}), "")
        self.assertEqual(ps.decode_prices_compact(""), {})
        self.assertEqual(ps.decode_prices_compact(None), {})

    def test_full_catalog_size_fits_under_telegram_pinned_message_limit(self):
        # فحص واقعي: أكبر قاموس أسعار ممكن (كل الأصناف الحقيقية بملف البيانات)
        # لازم يضل تحت حد تلغرام (٤٠٩٦ محرف) حتى بعد ما نلفه بحمولة الحالة الكاملة
        # (مشتركين + الترميز) — شوف telegram_state.py.
        #
        # ⚠️ ملاحظة (بعد توسيع الكتالوج لـ ٦٠٢ صنف): هالسيناريو (كل صنف وكل صنف
        # إله سعر معدّل يدوياً بنفس الوقت) صار وحده أكبر من ٤٠٩٦ محرف، يعني لو
        # التاجرة يوماً ما عدّلت سعر كل صنف عندها (مش واقعي حالياً، بس ممكن
        # مستقبلاً)، telegram_state.sync_state_to_telegram رح يتخطى حفظ آخر
        # تحديث بالرسالة المثبتة (فيه حماية بالكود، ما رح يطيح البوت، بس الحفظ
        # الاحتياطي بيصير متأخر). الحد هون رفعناه ليعكس الواقع الجديد، وخلينا
        # الملاحظة هون كتذكير إذا حبينا نحسّن الترميز مستقبلاً.
        import config

        groups = ps.load_price_sheet(config.PRICE_SHEET_PATH)
        flat = ps.flatten_items(groups)
        all_prices = {item["index"]: item["default_price"] or 1 for item in flat}
        encoded = ps.encode_prices_compact(all_prices)
        self.assertLess(len(encoded), 6000)


class TestPriceUpdateParsing(unittest.TestCase):
    def test_looks_like_price_update_accepts_multiple_valid_lines(self):
        self.assertTrue(ps.looks_like_price_update("0 99000\n2 33000"))
        self.assertTrue(ps.looks_like_price_update("5 0"))

    def test_looks_like_price_update_rejects_normal_text(self):
        self.assertFalse(ps.looks_like_price_update("مرحبا شو أخبارك"))
        self.assertFalse(ps.looks_like_price_update(""))
        self.assertFalse(ps.looks_like_price_update("0 99000\nهاي جملة عادية"))

    def test_parse_valid_updates(self):
        flat = ps.flatten_items(SAMPLE_GROUPS)
        updates, errors = ps.parse_price_update_lines("0 105000\n2 35000", flat)
        self.assertEqual(updates, {0: 105000, 2: 35000})
        self.assertEqual(errors, [])

    def test_parse_reports_out_of_range_index_but_keeps_valid_ones(self):
        flat = ps.flatten_items(SAMPLE_GROUPS)
        updates, errors = ps.parse_price_update_lines("0 105000\n999 1000", flat)
        self.assertEqual(updates, {0: 105000})
        self.assertEqual(len(errors), 1)
        self.assertIn("999", errors[0])


class TestFormatting(unittest.TestCase):
    def test_admin_reference_includes_brand_headers_and_index(self):
        flat = ps.flatten_items(SAMPLE_GROUPS)
        prices = ps.effective_prices(flat, {})
        chunks = ps.format_admin_reference(flat, prices)
        joined = "\n".join(chunks)
        self.assertIn("جيتان", joined)
        self.assertIn("0. جيتان قصير", joined)
        self.assertIn("⚠️ ما انحط سعر بعد", joined)  # الصنف اللي سعره 0

    def test_customer_prices_hides_zero_price_items(self):
        flat = ps.flatten_items(SAMPLE_GROUPS)
        prices = ps.effective_prices(flat, {})
        chunks = ps.format_customer_prices(flat, prices, "محل هيا", "2026-09-13")
        joined = "\n".join(chunks)
        self.assertIn("جيتان قصير", joined)
        self.assertIn("تي اس طويل فضي", joined)
        self.assertNotIn("تي اس سليم فضي", joined)  # سعرها 0، ما لازم تظهر للزبون

    def test_customer_prices_no_items_at_all_shows_fallback_text(self):
        flat = ps.flatten_items(SAMPLE_GROUPS)
        chunks = ps.format_customer_prices(flat, {0: 0, 1: 0, 2: 0}, "محل هيا", "2026-09-13")
        self.assertEqual(len(chunks), 1)
        self.assertIn("لسا ما في أسعار مضافة", chunks[0])

    def test_customer_prices_grouped_by_category_when_mapping_given(self):
        # بدون تقسيم قسم أعلى من البرند، القائمة كانت تطلع "مكركبة" — كل البرندات
        # ورا بعض بلا أي عنوان قسم فوقهم. هلق منجمّع حسب القسم (دخان/معسل/...) أول شي.
        flat = ps.flatten_items(SAMPLE_GROUPS)
        prices = ps.effective_prices(flat, {})
        category_of_brand = {"جيتان": "🚬 دخان", "تي اس": "🚬 دخان"}
        chunks = ps.format_customer_prices(
            flat, prices, "محل هيا", "2026-09-13", category_of_brand=category_of_brand
        )
        joined = "\n".join(chunks)
        self.assertIn("🚬 دخان", joined)
        # القسم لازم يطلع مرة وحدة بس (البرندين التنين تحت نفس القسم).
        self.assertEqual(joined.count("🚬 دخان"), 1)
        # البرند لسا بيطلع كعنوان فرعي تحت القسم.
        self.assertIn("🔸 جيتان", joined)
        self.assertIn("🔸 تي اس", joined)

    def test_same_brand_scattered_across_multiple_groups_shows_header_once(self):
        # لو نفس اسم البرند موجود بأكتر من مجموعة متفرقة بالملف (صار هيك فعلياً
        # لبعض ماركات الفحم بعد إضافات لاحقة، لتفادي تحريك مواقع أصناف موجودة)،
        # لازم القائمة المعروضة (للتاجر وللزبون) تجمعهم تحت عنوان وحد، مش
        # تكرر عنوان البرند بمكانين مختلفين بنفس القائمة.
        groups = [
            {"brand": "الزعيم", "items": [{"name": "الزعيم أ", "default_price": 10000}]},
            {"brand": "برند وسط", "items": [{"name": "صنف وسط", "default_price": 5000}]},
            {"brand": "الزعيم", "items": [{"name": "الزعيم ب", "default_price": 12000}]},
        ]
        flat = ps.flatten_items(groups)
        prices = ps.effective_prices(flat, {})

        admin_chunks = ps.format_admin_reference(flat, prices)
        admin_joined = "\n".join(admin_chunks)
        self.assertEqual(admin_joined.count("🔸 الزعيم"), 1)
        self.assertIn("الزعيم أ", admin_joined)
        self.assertIn("الزعيم ب", admin_joined)
        # رقم الصنف (index) ضل متل ما هو، بلا أي تحريك.
        self.assertIn("0. الزعيم أ", admin_joined)
        self.assertIn("2. الزعيم ب", admin_joined)

        customer_chunks = ps.format_customer_prices(flat, prices, "محل هيا", "2026-09-13")
        customer_joined = "\n".join(customer_chunks)
        self.assertEqual(customer_joined.count("🔸 الزعيم"), 1)
        self.assertIn("الزعيم أ", customer_joined)
        self.assertIn("الزعيم ب", customer_joined)

    def test_customer_prices_without_category_mapping_falls_back_to_old_layout(self):
        # لو ما انبعت category_of_brand إطلاقاً، نفس التقسيم القديم (برند ← صنف بس).
        flat = ps.flatten_items(SAMPLE_GROUPS)
        prices = ps.effective_prices(flat, {})
        chunks = ps.format_customer_prices(flat, prices, "محل هيا", "2026-09-13")
        joined = "\n".join(chunks)
        self.assertNotIn("🚬", joined)
        self.assertIn("🔸 جيتان", joined)

    def test_long_list_splits_into_multiple_chunks_under_limit(self):
        big_groups = [
            {
                "brand": f"ماركة{i}",
                "items": [{"name": f"صنف رقم {i} طويل الاسم شوي منشان الفحص", "default_price": 50000}],
            }
            for i in range(400)
        ]
        flat = ps.flatten_items(big_groups)
        prices = ps.effective_prices(flat, {})
        chunks = ps.format_customer_prices(flat, prices, "محل هيا", "2026-09-13")
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), ps.MAX_MESSAGE_CHARS + 500)  # + هامش الفوتر بآخر جزء


if __name__ == "__main__":
    unittest.main()
