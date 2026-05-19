# input: ASGI scope/receive/send, core.i18n.set_locale
# output: LocaleMiddleware (纯 ASGI)
# owner: wanhua.gu
# pos: 表示层中间件 - 语言/区域解析（纯 ASGI 实现）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""
Locale 解析中间件（纯 ASGI 实现）

优先级：?lang=xx > X-Lang > Accept-Language > 默认 'en'。

注意：不使用 BaseHTTPMiddleware。详见 api/middleware/__init__.py。
"""

from __future__ import annotations

from urllib.parse import parse_qs

from starlette.types import ASGIApp, Receive, Scope, Send

from core.i18n import set_locale


def _pick_from_accept_language(al: str) -> str:
    """Parse Accept-Language with q weights, return best lang tag.

    Examples:
      'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7' -> 'zh-CN'
    """
    try:
        items = []
        for part in al.split(","):
            p = part.strip()
            if not p:
                continue
            seg = p.split(";", 1)
            lang = seg[0].strip()
            q = 1.0
            if len(seg) == 2 and seg[1].strip().startswith("q="):
                try:
                    q = float(seg[1].strip()[2:])
                except Exception:
                    q = 1.0
            items.append((lang, q))
        if not items:
            return "en"
        items.sort(key=lambda x: x[1], reverse=True)
        return items[0][0]
    except Exception:
        return "en"


def _normalize(lang: str) -> str:
    """Map common browser tags to our locales."""
    tag = (lang or "en").replace("_", "-").lower()
    if tag in {"zh-cn", "zh-hans", "zh"}:
        return "zh_Hans"
    if tag in {"en", "en-us", "en-gb"}:
        return "en"
    return lang


def _get_header(scope: Scope, name: str) -> str:
    name_lower = name.lower().encode("latin-1")
    for key, value in scope.get("headers", []):
        if key == name_lower:
            return value.decode("latin-1")
    return ""


def _get_query_param(scope: Scope, name: str) -> str:
    qs = scope.get("query_string", b"")
    if not qs:
        return ""
    parsed = parse_qs(qs.decode("latin-1"))
    values = parsed.get(name)
    return values[0] if values else ""


class LocaleMiddleware:
    """Parse locale from query/header and set into context (纯 ASGI)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        lang = _get_query_param(scope, "lang") or _get_header(scope, "X-Lang")
        if not lang:
            al = _get_header(scope, "Accept-Language")
            lang = _pick_from_accept_language(al) if al else "en"

        set_locale(_normalize(lang))

        # 同时写入 scope.state，保留 request.state.locale 的访问语义
        state = scope.setdefault("state", {})
        state["locale"] = lang

        await self.app(scope, receive, send)
