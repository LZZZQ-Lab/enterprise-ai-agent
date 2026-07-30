"""Task 4.8 engineering quality tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.version import __version__
from app.version import read_version


from tests.fixtures.paths import REPO_ROOT


def test_version_file_matches_module() -> None:

    file_version = REPO_ROOT.joinpath("VERSION").read_text(
        encoding="utf-8",
    ).strip()

    assert read_version() == __version__
    assert __version__ == file_version


def test_openapi_has_core_paths() -> None:

    client = TestClient(app)

    schema = client.get("/openapi.json").json()

    assert schema["info"]["version"] == __version__

    paths = schema.get("paths") or {}

    assert "/health" in paths
    assert "/api/v1/chat" in paths
    assert "/metrics" in paths


def test_root_links_docs() -> None:

    client = TestClient(app)

    payload = client.get("/").json()

    assert payload["version"] == __version__
    assert payload["docs"] == "/docs"
