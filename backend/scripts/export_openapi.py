#!/usr/bin/env python3
"""Export OpenAPI schema to docs/openapi.json (Task 4.8)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app  # noqa: E402
from app.version import __version__  # noqa: E402


def main() -> int:

    schema = app.openapi()
    schema["info"]["version"] = __version__

    out = REPO_ROOT / "docs" / "openapi.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Wrote {out} (version {__version__})")
    return 0


if __name__ == "__main__":

    raise SystemExit(main())
