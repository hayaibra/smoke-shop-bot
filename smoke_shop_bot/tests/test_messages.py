"""
اختبارات ملخص الدفع (المدفوع/الباقي) بالرسائل النهائية — messages.py.
ما بتحتاج مكتبة تلغرام إطلاقاً (messages.py نصوص فقط).
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import messages as m


class TestPriceInquiryWaitMessages(unittest.TestCase):
    """رسائل الصبر للزبون والتذكير للتاجر، إذا تأخر التاجر بالرد على استفسار سعر."""

    def test_customer_patience_message_is_nonempty_text(self):
        self.assertIsInstance(m.PRICE_WAIT_PATIENCE_MESSAGE, str)
        self.assertGreater(len(m.PRICE_WAIT_PATIENCE_MESSAGE.strip()), 0)

    def test_admin_reminder_notice_mentions_customer_label(self):
        text = m.admin_price_reminder_notice("أحمد (@ahmad)")
        self.assertIn("أحمد (@ahmad)", text)
        self.assertIn("تذكير", text)


class TestMyCartStatus(unittest.TestCase):
    def test_nothing_at_all_shows_no_cart_message(self):
        text = m.my_cart_status(None, None, None)
        self.assertEqual(text, m.NO_CART_STATUS_YET)

    def test_building_cart_shown_even_before_any_price_inquiry(self):
        # الزبونة ضافت صنف للسلة بس لسا ما دوست "استعلام عن السعر" — لازم تشوف
        # سلتها الحالية برضو لما تستعلم، مش رسالة "ما عندك شي مسجل".
        text = m.my_cart_status(
            "▫️ دخان – ماستر – سليم أزرق – 3 كروز", m.CART_STATE_BUILDING, None
        )
        self.assertIn("سلتك الحالية", text)
        self.assertIn("سليم أزرق", text)
        self.assertNotIn("بانتظار رد التاجر", text)
        self.assertNotIn("وصلك رد التاجر", text)
        self.assertNotIn("آخر طلب مؤكد", text)

    def test_pending_only(self):
        text = m.my_cart_status(
            "▫️ دخان – ماستر – ماستر طويل – 3 كروز", m.CART_STATE_PENDING, None
        )
        self.assertIn("بانتظار رد التاجر", text)
        self.assertIn("ماستر طويل", text)
        self.assertNotIn("آخر طلب مؤكد", text)
        self.assertNotIn("وصلك رد التاجر", text)

    def test_quoted_awaiting_customer_decision_only(self):
        # التاجر رد بالسعر، بس الزبون لسا ما أكد ولا لغى — هاي الحالة يلي كانت
        # ناقصة وسببت تقرير الزبونة إنها استعلمت عن سلتها وما طلع فيها شي.
        text = m.my_cart_status(
            "▫️ دخان – ماستر – ماستر طويل – 3 كروز", m.CART_STATE_QUOTED, None
        )
        self.assertIn("وصلك رد التاجر", text)
        self.assertIn("ماستر طويل", text)
        self.assertIn("لسا ما أكدتي ولا لغيتي", text)
        self.assertNotIn("بانتظار رد التاجر", text)
        self.assertNotIn("آخر طلب مؤكد", text)

    def test_last_order_only(self):
        order = {"cart": ["▫️ دخان – ماستر – ماستر طويل – 3 كروز"], "timestamp": "2026-09-13 12:00"}
        text = m.my_cart_status(None, None, order)
        self.assertIn("آخر طلب مؤكد", text)
        self.assertIn("2026-09-13 12:00", text)
        self.assertNotIn("بانتظار رد التاجر", text)

    def test_last_order_with_new_structured_cart_items_shows_display_text(self):
        # بعد تحديث السلة لبُنى (dicts)، الطلبات الجديدة المحفوظة بـ orders_log.json
        # صارت عبارة عن list[dict] (فيها "display") مش list[str] مباشرة.
        order = {
            "cart": [{"display": "▫️ دخان – ماستر – ماستر طويل ورق م – 3 🎁 كروز"}],
            "timestamp": "2026-09-15 10:00",
        }
        text = m.my_cart_status(None, None, order)
        self.assertIn("ماستر طويل ورق م", text)
        self.assertIn("آخر طلب مؤكد", text)

    def test_both_pending_and_last_order_shown_together(self):
        order = {"cart": ["▫️ معسل – الفاخر – تفاحتين – 3 كيلو"], "timestamp": "2026-09-10 10:00"}
        text = m.my_cart_status(
            "▫️ دخان – ماستر – ماستر طويل – 3 كروز", m.CART_STATE_PENDING, order
        )
        self.assertIn("بانتظار رد التاجر", text)
        self.assertIn("آخر طلب مؤكد", text)

    def test_both_quoted_and_last_order_shown_together(self):
        order = {"cart": ["▫️ معسل – الفاخر – تفاحتين – 3 كيلو"], "timestamp": "2026-09-10 10:00"}
        text = m.my_cart_status(
            "▫️ دخان – ماستر – ماستر طويل – 3 كروز", m.CART_STATE_QUOTED, order
        )
        self.assertIn("وصلك رد التاجر", text)
        self.assertIn("آخر طلب مؤكد", text)


class TestAutoPriceQuote(unittest.TestCase):
    """رد السعر التلقائي للزبون (البوت حسبو لحاله)، وإشعار التاجر المعلوماتي المرافق له."""

    def test_customer_quote_shows_priced_cart_and_total(self):
        text = m.auto_price_quote("▫️ دخان – ماستر – ماستر طويل ورق م – 3 🎁 كروز — 201000 ل.س", 201000)
        self.assertIn("201000", text)
        self.assertIn("ماستر طويل ورق م", text)
        self.assertIn("تأكيد الطلب", text)
        self.assertIn("إلغاء الطلب", text)

    def test_admin_notice_says_no_reply_needed(self):
        text = m.admin_auto_priced_notice("أحمد (@ahmad)", "▫️ سطر — 201000 ل.س", 201000, "2026-09-15 10:00")
        self.assertIn("أحمد (@ahmad)", text)
        self.assertIn("201000", text)
        self.assertIn("2026-09-15 10:00", text)
        self.assertIn("ما بتحتاج ترد عليه", text)


class TestPaymentSummaryInOrderConfirmation(unittest.TestCase):
    def test_prepaid_shows_full_amount_paid_and_no_remaining(self):
        text = m.order_confirmation("cart", payment_method="prepaid", paid_amount=600000, remaining_amount=0)
        self.assertIn("600000", text)
        self.assertIn("ما عليك شي باقي", text)

    def test_deposit_shows_paid_and_remaining_amounts(self):
        text = m.order_confirmation("cart", payment_method="deposit", paid_amount=300000, remaining_amount=300000)
        self.assertIn("رعبون 300000", text)
        self.assertIn("باقي عليك 300000", text)

    def test_cod_shows_full_amount_due_on_delivery(self):
        text = m.order_confirmation("cart", payment_method="cod", paid_amount=0, remaining_amount=600000)
        self.assertIn("المطلوب عند الاستلام: 600000", text)

    def test_missing_amount_omits_summary_line_silently(self):
        # لو ما قدرنا نفهم رقم من رد التاجر (extract_amount رجع None)، ما لازم
        # تطلع رسالة فيها أرقام غلط — بترجع نفس شكل الرسالة الأصلي بلا سطر مبلغ.
        with_amounts = m.order_confirmation("cart")
        self.assertNotIn("💰", with_amounts)


class TestPaymentSummaryInAdminNotice(unittest.TestCase):
    def _notice(self, **kwargs):
        base = dict(
            customer_label="Haya",
            phone="0998776",
            address="addr",
            cart_text="cart",
            payment_method_label="label",
            has_payment_proof=True,
            timestamp="now",
        )
        base.update(kwargs)
        return m.admin_final_order_notice(**base)

    def test_deposit_tells_admin_paid_and_owed(self):
        text = self._notice(payment_method="deposit", paid_amount=300000, remaining_amount=300000)
        self.assertIn("دفع الزبون رعبون: 300000", text)
        self.assertIn("الباقي عليه: 300000", text)

    def test_cod_tells_admin_full_amount_to_collect(self):
        text = self._notice(payment_method="cod", paid_amount=0, remaining_amount=600000)
        self.assertIn("المطلوب تحصيله عند التسليم: 600000", text)

    def test_missing_amount_omits_summary_line_silently(self):
        text = self._notice()
        self.assertNotIn("💰", text)


if __name__ == "__main__":
    unittest.main()
