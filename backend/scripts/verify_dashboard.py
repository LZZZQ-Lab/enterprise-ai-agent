#!/usr/bin/env python3
"""Smoke test for AI Infra Dashboard (Task 7.8)."""

from __future__ import annotations

import json
import sys

import httpx

BASE = "http://127.0.0.1:8001"


def main() -> int:
    errors: list[str] = []

    health = httpx.get(f"{BASE}/health", timeout=30.0)
    print(f"[health] {health.status_code}")
    if health.status_code != 200:
        errors.append(f"health failed: {health.status_code}")

    overview = httpx.get(
        f"{BASE}/api/v1/infra/dashboard/overview",
        timeout=30.0,
    )
    print(f"[overview] {overview.status_code}")
    if overview.status_code != 200:
        errors.append(f"overview failed: {overview.status_code} {overview.text[:300]}")
    else:
        data = overview.json()
        print(json.dumps(data, ensure_ascii=False, indent=2)[:4000])

    demo = httpx.get(f"{BASE}/infra/dashboard/demo", timeout=30.0)
    print(f"[demo html] {demo.status_code} len={len(demo.text)}")
    if demo.status_code != 200 or "infra/dashboard" not in demo.text.lower():
        errors.append(f"demo page failed: {demo.status_code}")

    chat = httpx.post(
        f"{BASE}/api/v1/chat",
        json={"session_id": "dashboard-smoke", "message": "ping"},
        timeout=120.0,
    )
    print(f"[chat] {chat.status_code} success={chat.json().get('success')}")

    overview2 = httpx.get(
        f"{BASE}/api/v1/infra/dashboard/overview",
        timeout=30.0,
    )
    if overview2.status_code == 200:
        snap = overview2.json()
        gateway = snap.get("gateway") or {}
        models = snap.get("models") or []
        print(
            "[overview after chat] "
            f"gateway_requests={gateway.get('total_requests')} "
            f"models={len(models)}"
        )

    if errors:
        print("\nFAILED:")
        for item in errors:
            print(f"  - {item}")
        return 1

    print("\nDashboard verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
