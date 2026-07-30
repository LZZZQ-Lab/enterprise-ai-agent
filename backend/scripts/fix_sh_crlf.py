"""Convert backend/scripts/*.sh to Unix LF (run in WSL: python3 scripts/fix_sh_crlf.py)."""
from __future__ import annotations

from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent

for path in sorted(SCRIPTS.glob("*.sh")):
    raw = path.read_bytes()
    fixed = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    if fixed != raw:
        path.write_bytes(fixed)
        print(f"fixed: {path.name}")
    else:
        print(f"ok:    {path.name}")
