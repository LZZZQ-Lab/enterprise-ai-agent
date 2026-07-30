"""Settings 测试隔离。"""

from __future__ import annotations

import pytest

from app.config.settings import reset_settings_cache
from app.llm.factory import reset_llm_client_cache


@pytest.fixture(autouse=True)
def _disable_inference_gateway(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_INFERENCE_GATEWAY", "false")
    reset_settings_cache()
    reset_llm_client_cache()
    yield
    reset_settings_cache()
    reset_llm_client_cache()
