"""Task 7.3 Inference Gateway 测试。"""

from __future__ import annotations

from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.gateway.config import create_inference_backend
from app.gateway.config import resolve_backend_kind
from app.gateway.exceptions import GatewayBackendError
from app.gateway.exceptions import GatewayError
from app.gateway.provider import GatewayLLMProvider
from app.gateway.service import InferenceGateway
from app.gateway.stats import get_token_stats
from app.gateway.stats import reset_token_stats
from app.gateway.types import InferenceBackendKind
from app.gateway.types import TokenUsage
from app.llm.types import ChatResult
from app.llm.types import Message


@pytest.fixture(autouse=True)
def _disable_service_discovery_for_gateway_tests(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_SERVICE_DISCOVERY", "false")
    from app.config.settings import get_settings
    from app.llm.factory import reset_llm_client_cache

    get_settings.cache_clear()
    reset_llm_client_cache()


def test_resolve_backend_kinds() -> None:
    assert resolve_backend_kind("vllm").value == "vllm"
    assert resolve_backend_kind("sglang").value == "sglang"
    assert resolve_backend_kind("tgi").value == "tgi"


def test_gateway_records_token_stats() -> None:
    reset_token_stats()

    backend = MagicMock()
    backend.model_id = "test-model"
    backend.last_usage = TokenUsage(
        prompt_tokens=10,
        completion_tokens=20,
        total_tokens=30,
    )
    backend.chat.return_value = ChatResult(
        model="test-model",
        content="ok",
    )

    gateway = InferenceGateway(
        backend=backend,
        backend_kind=InferenceBackendKind.OPENAI,
    )
    payload = gateway.chat(
        [Message(role="user", content="hi")],
        use_tools=False,
    )

    assert payload.result.content == "ok"
    stats = get_token_stats()
    assert stats.total_requests == 1
    assert stats.total_tokens == 30
    assert stats.by_backend.get("openai") == 30


def test_gateway_maps_backend_error() -> None:
    backend = MagicMock()
    backend.model_id = "m"
    backend.chat.side_effect = RuntimeError("backend down")

    gateway = InferenceGateway(
        backend=backend,
        backend_kind=InferenceBackendKind.VLLM,
    )

    with pytest.raises(GatewayBackendError):
        gateway.chat(
            [Message(role="user", content="x")],
            use_tools=False,
        )


def test_factory_uses_gateway_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_INFERENCE_GATEWAY", "true")
    monkeypatch.setenv("MODEL_PROVIDER", "vllm")

    from app.config.settings import get_settings
    from app.llm.factory import create_llm_provider
    from app.llm.factory import reset_llm_client_cache

    get_settings.cache_clear()
    reset_llm_client_cache()

    provider = create_llm_provider()
    assert isinstance(provider, GatewayLLMProvider)


def test_create_sglang_backend(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_INFERENCE_GATEWAY", "false")
    monkeypatch.setenv("SGLANG_ENDPOINT", "http://127.0.0.1:30000/v1")

    from app.config.settings import get_settings

    get_settings.cache_clear()
    backend = create_inference_backend("sglang")
    assert backend.backend_kind == InferenceBackendKind.SGLANG


def test_rest_chat_completions_mock_gateway() -> None:
    from app.main import app

    mock_result = ChatResult(model="gpt-test", content="hello gateway")
    mock_meta = MagicMock()
    mock_meta.request_id = "abc"
    mock_meta.backend = InferenceBackendKind.OPENAI
    mock_meta.model = "gpt-test"
    mock_meta.duration_ms = 12.3
    mock_meta.usage = TokenUsage(
        prompt_tokens=1,
        completion_tokens=2,
        total_tokens=3,
    )

    with patch("app.gateway.router.get_inference_gateway") as get_gw:
        gw = MagicMock()
        gw.chat.return_value = MagicMock(
            result=mock_result,
            meta=mock_meta,
        )
        get_gw.return_value = gw

        client = TestClient(app)
        response = client.post(
            "/api/v1/inference/chat/completions",
            json={
                "messages": [{"role": "user", "content": "hi"}],
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["choices"][0]["message"]["content"] == "hello gateway"
    assert body["usage"]["total_tokens"] == 3
    assert body["gateway"]["backend"] == "openai"


def test_rest_gateway_error_format() -> None:
    from app.main import app

    with patch("app.gateway.router.get_inference_gateway") as get_gw:
        gw = MagicMock()
        gw.chat.side_effect = GatewayError(
            "failed",
            code="gateway_test",
            status_code=418,
        )
        get_gw.return_value = gw

        client = TestClient(app)
        response = client.post(
            "/api/v1/inference/chat/completions",
            json={
                "messages": [{"role": "user", "content": "hi"}],
            },
        )

    assert response.status_code == 418
    assert response.json()["error"]["code"] == "gateway_test"
