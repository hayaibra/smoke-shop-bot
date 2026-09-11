"""اختبارات التخزين — بتستخدم ملفات مؤقتة، ما بتلمس بيانات المشروع الحقيقية."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import storage as st


class TestSubscribers(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self.tmpdir.name) / "subscribers.json"

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_add_and_get(self):
        st.add_subscriber(self.path, 111)
        st.add_subscriber(self.path, 222)
        st.add_subscriber(self.path, 111)  # مكرر، ما لازم يتضاعف
        self.assertEqual(sorted(st.get_subscribers(self.path)), [111, 222])

    def test_remove(self):
        st.add_subscriber(self.path, 111)
        st.remove_subscriber(self.path, 111)
        self.assertEqual(st.get_subscribers(self.path), [])

    def test_get_on_missing_file(self):
        self.assertEqual(st.get_subscribers(self.path), [])


class TestPendingReplies(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self.tmpdir.name) / "pending.json"

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_save_and_pop(self):
        st.save_pending_reply(self.path, admin_message_id=555, customer_chat_id=999)
        self.assertEqual(st.peek_pending_reply(self.path, 555), 999)
        popped = st.pop_pending_reply(self.path, 555)
        self.assertEqual(popped, 999)
        # بعد الـ pop، ما لازم يضل موجود
        self.assertIsNone(st.pop_pending_reply(self.path, 555))

    def test_pop_missing_returns_none(self):
        self.assertIsNone(st.pop_pending_reply(self.path, 123))


class TestLastQuote(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self.tmpdir.name) / "quotes.json"

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_save_and_get(self):
        st.save_last_quote(self.path, 999, "150000 ل.س")
        self.assertEqual(st.get_last_quote(self.path, 999), "150000 ل.س")

    def test_get_missing_returns_none(self):
        self.assertIsNone(st.get_last_quote(self.path, 999))


class TestOrderLog(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self.tmpdir.name) / "orders.jsonl"

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_append_creates_file_and_appends_lines(self):
        st.append_order_log(self.path, {"customer": "أحمد"})
        st.append_order_log(self.path, {"customer": "سارة"})
        lines = self.path.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertIn("أحمد", lines[0])
        self.assertIn("سارة", lines[1])


if __name__ == "__main__":
    unittest.main()
