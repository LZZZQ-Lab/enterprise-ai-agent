"""Single source of truth for release version (Task 4.8)."""

from __future__ import annotations

from pathlib import Path

_VERSION_FILE = Path(__file__).resolve().parents[2] / "VERSION"


def read_version(default: str = "0.1.0") -> str:

    if not _VERSION_FILE.is_file():

        return default

    text = _VERSION_FILE.read_text(encoding="utf-8").strip()

    return text or default


__version__ = read_version()
