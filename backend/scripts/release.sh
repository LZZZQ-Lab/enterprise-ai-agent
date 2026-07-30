#!/usr/bin/env bash
# Task 8.8: release helper — verify VERSION, tests, OpenAPI, optional tag
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${1:-}"

if [[ -z "$VERSION" ]]; then
  VERSION="$(tr -d ' \r\n' < "$ROOT/VERSION")"
fi

echo "==> Release check for v${VERSION}"
echo "    ROOT: $ROOT"

cd "$BACKEND"

echo "==> pytest (not integration)"
bash scripts/run_tests.sh

echo "==> ruff lint"
pip install -q -r requirements-dev.txt 2>/dev/null || true
python -m ruff check app tests benchmark loadtest security scripts observability 2>/dev/null || bash scripts/run_lint.sh

echo "==> export OpenAPI"
python scripts/export_openapi.py

echo "==> verify VERSION"
python -c "
import json, pathlib
root = pathlib.Path('${ROOT}')
v = root.joinpath('VERSION').read_text(encoding='utf-8').strip()
o = json.loads(root.joinpath('docs/openapi.json').read_text(encoding='utf-8'))['info']['version']
assert v == '${VERSION}', f'VERSION file {v} != expected ${VERSION}'
assert v == o, f'OpenAPI {o} != VERSION {v}'
print('VERSION OK:', v)
"

echo
echo "Release checks passed for v${VERSION}"
echo
echo "Next steps:"
echo "  git add VERSION CHANGELOG.md RELEASE.md README.md docs/openapi.json"
echo "  git commit -m \"release: v${VERSION}\""
echo "  git tag -a v${VERSION} -m \"v${VERSION}\""
echo "  git push origin main && git push origin v${VERSION}"
echo "  gh release create v${VERSION} --title \"v${VERSION}\" --notes-file CHANGELOG.md"
