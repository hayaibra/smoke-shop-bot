"""اختبارات الدوال النقية بـ telegram_state.py (تشفير/فك تشفير نص الرسالة المثبتة)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import telegram_state as ts


class TestStateTextRoundTrip(unittest.TestCase):
    def test_round_trip(self):
        subs = [111, 222, 333]
        text = ts._build_state_text(subs)
        parsed = ts._parse_state_text(text)
        self.assertEqual(parsed, subs)

    def test_empty_list_round_trip(self):
        text = ts._build_state_text([])
        self.assertEqual(ts._parse_state_text(text), [])

    def test_parse_rejects_unrelated_text(self):
        self.assertIsNone(ts._parse_state_text("مرحبا شو أخبارك"))
        self.assertIsNone(ts._parse_state_text("{}"))
        self.assertIsNone(ts._parse_state_text('{"marker": "something_else", "subscribers": [1]}'))

    def test_parse_rejects_malformed_subscribers_field(self):
        self.assertIsNone(
            ts._parse_state_text('{"marker": "%s", "subscribers": "not-a-list"}' % ts._STATE_MARKER)
        )

    def test_parse_handles_plain_invalid_json(self):
        self.assertIsNone(ts._parse_state_text("not json at all {{{"))


if __name__ == "__main__":
    unittest.main()
