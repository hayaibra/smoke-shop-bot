# -*- coding: utf-8 -*-
"""
حفظ تعديلات أسعار الدولار (/usdprices) بشكل دائم على GitHub — مباشرة بملف
data/usd_prices.json بنفس الريبو يلي التاجرة أصلاً برفع عليه كل ملفاتها يدوياً.

ليش هالملف بالذات (بدل الرسالة المثبتة بتلغرام يلي بتحفظ فيها أسعار الليرة —
شوف telegram_state.py)؟ لأنو تلغرام بيعطينا رسالة مثبتة واحدة بس لكل شات،
بحد أقصى ٤٠٩٦ محرف — وأسعار الدولار لحالها (لو عبّت التاجرة كل الكتالوج)
ممكن تتعدى هالحجم بسهولة. فـ GitHub هون هو "قاعدة البيانات" الدائمة.

بيحتاج 3 إعدادات من config.py (environment variables عَ Render):
- GITHUB_TOKEN: Personal Access Token بصلاحية "repo".
- GITHUB_REPO: "اسم_الحساب/اسم_المستودع".
- GITHUB_BRANCH: الفرع (افتراضياً "main").

لو أي واحد منهم ناقص، update_file() بترمي GitHubSyncError واضحة — التاجرة
المفروض تشوف رسالة تحذير بالبوت تقولها التعديل صار بس ما انحفظ بشكل دائم.

الدوال هون بتعمل طلب شبكة فعلي (urllib، بدون أي مكتبة خارجية جديدة)، فهي
مش "نقية" متل باقي ملفات المشروع — بس مفصولة لحالها هون منشان handlers.py
يقدر يستخدمها بـ run_in_executor (البوت async، وurllib متزامن/blocking).
"""
import base64
import json
import urllib.error
import urllib.request
from typing import Optional

_API_BASE = "https://api.github.com"
_TIMEOUT_SECONDS = 15


class GitHubSyncError(Exception):
    """فشلت محاولة القراءة/الحفظ على GitHub (إعدادات ناقصة، شبكة، صلاحيات...)."""


def _request(method: str, url: str, token: str, body: Optional[dict] = None) -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "smoke-shop-bot")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT_SECONDS) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise GitHubSyncError(f"GitHub API رجع خطأ {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise GitHubSyncError(f"تعذر الوصول لـ GitHub: {exc}") from exc


def get_file_sha(repo: str, path: str, token: str, branch: str = "main") -> Optional[str]:
    """بترجع sha الملف الحالي عالـ GitHub (لازم تنحط بطلب التحديث)، أو None لو
    الملف لسا مش موجود هناك إطلاقاً (أول مرة بينحفظ)."""
    url = f"{_API_BASE}/repos/{repo}/contents/{path}?ref={branch}"
    try:
        result = _request("GET", url, token)
    except GitHubSyncError as exc:
        if "خطأ 404" in str(exc):
            return None
        raise
    return result.get("sha")


def update_file(
    repo: str,
    path: str,
    token: str,
    content: str,
    message: str,
    branch: str = "main",
) -> None:
    """بتحدث (أو بتنشئ لو أول مرة) ملف على GitHub بمحتوى جديد (نص UTF-8 عادي).
    بترمي GitHubSyncError واضحة لو إعدادات الاتصال ناقصة أو الطلب فشل."""
    if not token:
        raise GitHubSyncError("GITHUB_TOKEN مش معبّى بمتغيرات البيئة.")
    if not repo:
        raise GitHubSyncError("GITHUB_REPO مش معبّى بمتغيرات البيئة.")

    sha = get_file_sha(repo, path, token, branch)
    encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
    body = {"message": message, "content": encoded, "branch": branch}
    if sha:
        body["sha"] = sha

    url = f"{_API_BASE}/repos/{repo}/contents/{path}"
    _request("PUT", url, token, body)
