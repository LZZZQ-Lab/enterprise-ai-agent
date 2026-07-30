"""Swagger / ReDoc 文档页 CDN 配置（避免 jsdelivr 在国内长期加载）。"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)

_CDN_PRESETS: dict[str, dict[str, str]] = {
    "unpkg": {
        "js": "https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-bundle.js",
        "css": "https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui.css",
        "redoc": "https://unpkg.com/redoc@2.1.3/bundles/redoc.standalone.js",
    },
    "bootcdn": {
        "js": "https://cdn.bootcdn.net/ajax/libs/swagger-ui/5.9.0/swagger-ui-bundle.js",
        "css": "https://cdn.bootcdn.net/ajax/libs/swagger-ui/5.9.0/swagger-ui.css",
        "redoc": "https://cdn.bootcdn.net/ajax/libs/redoc/2.1.3/bundles/redoc.standalone.js",
    },
    "jsdelivr": {
        "js": "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        "css": "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        "redoc": "https://cdn.jsdelivr.net/npm/redoc@2/bundles/redoc.standalone.js",
    },
}


def _cdn_urls(preset: str) -> dict[str, str]:
    key = (preset or "unpkg").strip().lower()
    return _CDN_PRESETS.get(key, _CDN_PRESETS["unpkg"])


def mount_api_docs(app: FastAPI, *, cdn_preset: str = "unpkg") -> None:
    """
    使用可配置 CDN 挂载 /docs 与 /redoc（FastAPI 默认 jsdelivr 易在国内卡住）。
    """

    urls = _cdn_urls(cdn_preset)
    openapi_url = app.openapi_url or "/openapi.json"

    @app.get("/docs", include_in_schema=False)
    async def swagger_ui_html():
        return get_swagger_ui_html(
            openapi_url=openapi_url,
            title=f"{app.title} - Swagger UI",
            swagger_js_url=urls["js"],
            swagger_css_url=urls["css"],
        )

    @app.get(app.swagger_ui_oauth2_redirect_url or "/docs/oauth2-redirect", include_in_schema=False)
    async def swagger_ui_redirect():
        return get_swagger_ui_oauth2_redirect_html()

    @app.get("/redoc", include_in_schema=False)
    async def redoc_html():
        return get_redoc_html(
            openapi_url=openapi_url,
            title=f"{app.title} - ReDoc",
            redoc_js_url=urls["redoc"],
        )
