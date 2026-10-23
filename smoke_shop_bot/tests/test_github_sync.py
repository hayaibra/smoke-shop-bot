# -*- coding: utf-8 -*-
"""اختبارات github_sync.py — بدون أي اتصال شبكة فعلي (urllib.request.urlopen
مُموَّه/mocked بالكامل)."""
import json
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import github_sync as gs


def _fake_response(payload: dict):
    cm = MagicMock()
    cm.read.return_value = json.dumps(payload).encode("utf-8")
    cm.__enter__.return_value = cm
    cm.__exit__.return_value = False
    return cm


class TestUpdateFileValidation(unittest.TestCase):
    """لازم نرفض الطلب قبل أي اتصال شبكة لو الإعدادات ناقصة — رسالة واضحة
    بالعربي بدل Exception غامض وقت التشغيل الفعلي."""

    def test_missing_token_raises_clear_error(self):
        with self.assertRaises(gs.GitHubSyncError) as ctx:
            gs.update_file("a/b", "data/x.json", "", "{}", "msg")
        self.assertIn("GITHUB_TOKEN", str(ctx.exception))

    def test_missing_repo_raises_clear_error(self):
        with self.assertRaises(gs.GitHubSyncError) as ctx:
            gs.update_file("", "data/x.json", "tok", "{}", "msg")
        self.assertIn("GITHUB_REPO", str(ctx.exception))


class TestGetFileSha(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_returns_sha_when_file_exists(self, mock_urlopen):
        mock_urlopen.return_value = _fake_response({"sha": "abc123"})
        sha = gs.get_file_sha("owner/repo", "data/usd_prices.json", "tok")
        self.assertEqual(sha, "abc123")

    @patch("urllib.request.urlopen")
    def test_returns_none_when_file_missing_404(self, mock_urlopen):
        err = urllib.error.HTTPError(
            url="x", code=404, msg="Not Found", hdrs=None, fp=MagicMock(read=lambda: b"{}")
        )
        mock_urlopen.side_effect = err
        sha = gs.get_file_sha("owner/repo", "data/usd_prices.json", "tok")
        self.assertIsNone(sha)

    @patch("urllib.request.urlopen")
    def test_other_http_errors_propagate(self, mock_urlopen):
        err = urllib.error.HTTPError(
            url="x", code=401, msg="Unauthorized", hdrs=None, fp=MagicMock(read=lambda: b"{}")
        )
        mock_urlopen.side_effect = err
        with self.assertRaises(gs.GitHubSyncError):
            gs.get_file_sha("owner/repo", "data/usd_prices.json", "bad-token")


class TestUpdateFile(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_includes_sha_when_file_already_exists(self, mock_urlopen):
        # أول نداء (GET للـ sha) بيرجع sha، التاني (PUT) بيرجع تأكيد — نتحقق
        # إنو جسم طلب PUT فيه نفس الـ sha يلي رجعناه (منشان ما يصير تعارض نسخة).
        mock_urlopen.side_effect = [
            _fake_response({"sha": "old-sha"}),
            _fake_response({"content": {}}),
        ]
        gs.update_file("owner/repo", "data/usd_prices.json", "tok", '{"0": 1.5}', "msg")

        put_call = mock_urlopen.call_args_list[1]
        put_request = put_call.args[0]
        body = json.loads(put_request.data.decode("utf-8"))
        self.assertEqual(body["sha"], "old-sha")
        self.assertEqual(put_request.get_method(), "PUT")

    @patch("urllib.request.urlopen")
    def test_no_sha_when_file_does_not_exist_yet(self, mock_urlopen):
        err = urllib.error.HTTPError(
            url="x", code=404, msg="Not Found", hdrs=None, fp=MagicMock(read=lambda: b"{}")
        )
        mock_urlopen.side_effect = [err, _fake_response({"content": {}})]
        gs.update_file("owner/repo", "data/usd_prices.json", "tok", '{"0": 1.5}', "msg")

        put_call = mock_urlopen.call_args_list[1]
        put_request = put_call.args[0]
        body = json.loads(put_request.data.decode("utf-8"))
        self.assertNotIn("sha", body)

    @patch("urllib.request.urlopen")
    def test_content_is_base64_encoded_utf8(self, mock_urlopen):
        import base64

        mock_urlopen.side_effect = [
            urllib.error.HTTPError(
                url="x", code=404, msg="Not Found", hdrs=None, fp=MagicMock(read=lambda: b"{}")
            ),
            _fake_response({"content": {}}),
        ]
        gs.update_file("owner/repo", "data/usd_prices.json", "tok", '{"غلواز": 11}', "msg")

        put_request = mock_urlopen.call_args_list[1].args[0]
        body = json.loads(put_request.data.decode("utf-8"))
        decoded = base64.b64decode(body["content"]).decode("utf-8")
        self.assertEqual(decoded, '{"غلواز": 11}')


if __name__ == "__main__":
    unittest.main()
