# input: FastAPI app, LocaleMiddleware 解析的 request.state.locale
# output: register_docs(app) 自定义 Swagger UI（/docs，含 i18n 语言注入）
# owner: wanhua.gu
# pos: 表示层 - API 文档 UI 装配（从 main.py 抽出的 Swagger 定制，依赖 FastAPI 生成的 HTML 结构，升级 FastAPI 时需要回归 /docs）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
"""Custom Swagger UI registration with locale support.

Kept out of ``main.py`` on purpose: this patches the HTML that
``get_swagger_ui_html`` produces via string replacement, which is inherently
coupled to FastAPI internals. If ``/docs`` breaks after a FastAPI upgrade,
this module is the only place to look.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.openapi.docs import get_swagger_ui_html
from starlette.responses import HTMLResponse

from core.config import settings


def _map_locale_to_swagger_lang(locale: str) -> str:
    """将后端 locale 映射为 Swagger UI 支持的语言代码。"""
    if not locale:
        return "en"
    tag = locale.replace("_", "-").lower()
    # 常见映射（根据 Swagger UI 语言包）
    if tag in {"zh", "zh-cn", "zh-hans"}:
        return "zh-CN"
    if tag in {"zh-tw", "zh-hant"}:
        return "zh-TW"
    if tag in {"en", "en-us", "en-gb"}:
        return "en"
    # 其他语言可按需扩展
    return "en"


def register_docs(app: FastAPI) -> None:
    """Register the customized ``/docs`` route (i18n-aware Swagger UI)."""

    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html(request: Request) -> HTMLResponse:
        # 由 LocaleMiddleware 解析的语言，或从查询参数获取
        current = getattr(request.state, "locale", None)
        lang = _map_locale_to_swagger_lang(str(current or "en"))

        base = get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{settings.PROJECT_NAME} - API Docs",
            swagger_ui_parameters={
                # 关键：传入语言
                "lang": lang,
                # 常用增强参数（可按需调整）
                "persistAuthorization": True,
                "displayRequestDuration": True,
            },
        )
        # 注入 requestInterceptor：为“Try it out”请求附带语言信息
        try:
            content = base.body.decode("utf-8")
        except Exception:
            content = str(base.body)
        injection = (
            "requestInterceptor: function(req){\n"
            "  try {\n"
            "    const url = new URL(req.url, window.location.origin);\n"
            "    const params = new URLSearchParams(window.location.search);\n"
            "    const lang = params.get('lang') || localStorage.getItem('docs_lang') || '%s';\n"
            "    if (lang) {\n"
            "      req.headers = req.headers || {};\n"
            "      req.headers['X-Lang'] = lang;\n"
            "      url.searchParams.set('lang', lang);\n"
            "      req.url = url.toString();\n"
            "    }\n"
            "  } catch (e) {}\n"
            "  return req;\n"
            "},"
        ) % (lang,)
        content = content.replace("SwaggerUIBundle({", "SwaggerUIBundle({\n  " + injection, 1)
        # 记住当前语言（刷新仍能保留）
        remember_lang_script = (
            "<script>\n"
            "(function(){\n"
            "  try {\n"
            "    var p = new URLSearchParams(window.location.search);\n"
            "    var l = p.get('lang');\n"
            "    if (l) localStorage.setItem('docs_lang', l);\n"
            "  } catch (e) {}\n"
            "})();\n"
            "</script>"
        )
        content = content.replace("</body>", remember_lang_script + "\n</body>")
        # 返回新的 HTMLResponse，避免沿用旧的 Content-Length 头
        return HTMLResponse(content=content, status_code=base.status_code)
