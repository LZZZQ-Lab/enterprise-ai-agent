"""
推理节点健康检查。
"""

from __future__ import annotations

import httpx

from app.service.types import ProviderNode


class HealthChecker:
    """
    vLLM / SGLang OpenAI 兼容服务健康探测。

    顺序：``/health``（去 /v1 前缀）→ ``/v1/models``。
    """

    def __init__(self, *, timeout_seconds: float = 5.0) -> None:
        self._timeout = timeout_seconds

    def check(self, node: ProviderNode) -> tuple[bool, str]:
        errors: list[str] = []

        health_url = f"{node.origin}/health"
        ok, err = self._probe_url(health_url)
        if ok:
            return True, ""
        if err:
            errors.append(f"health: {err}")

        models_url = f"{node.base_url.rstrip('/')}/models"
        ok, err = self._probe_url(models_url, need_auth=True, node=node)
        if ok:
            return True, ""
        if err:
            errors.append(f"models: {err}")

        return False, "; ".join(errors) or "unreachable"

    def _probe_url(
        self,
        url: str,
        *,
        need_auth: bool = False,
        node: ProviderNode | None = None,
    ) -> tuple[bool, str]:
        headers = {}
        if need_auth and node is not None and node.api_key:
            headers["Authorization"] = f"Bearer {node.api_key}"

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.get(url, headers=headers)
            if response.status_code < 500:
                return True, ""
            return False, f"HTTP {response.status_code}"
        except httpx.HTTPError as exc:
            return False, str(exc)
