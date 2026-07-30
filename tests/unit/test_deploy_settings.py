"""Deploy-related configuration tests."""

from __future__ import annotations

from app.config.settings import Settings


def test_chroma_http_settings_fields() -> None:

    settings = Settings(
        CHROMA_HOST="chroma",
        CHROMA_PORT=8000,
        REDIS_URL="redis://redis:6379/0",
    )

    assert settings.CHROMA_HOST == "chroma"
    assert settings.REDIS_URL.startswith("redis://")
