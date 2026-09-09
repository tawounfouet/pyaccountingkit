#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

failures=0

fail() {
  printf 'HYGIENE ERROR: %s\n' "$1" >&2
  failures=$((failures + 1))
}

printf '== PyAccountingKit repository hygiene ==\n'

if ! command -v git >/dev/null 2>&1; then
  fail "git is required to validate tracked repository content"
else
  tracked_artifacts="$({
    git ls-files -z | tr '\0' '\n' | grep -E \
      '(^|/)(__pycache__|\.pytest_cache|\.mypy_cache|\.ruff_cache)(/|$)|\.py[co]$|(^|/)\.DS_Store$|(^|/)\.coverage$|(^|/)dist/|(^|/)build/|\.egg-info/'
  } || true)"
  if [[ -n "$tracked_artifacts" ]]; then
    fail "generated/cache artifacts are tracked:\n$tracked_artifacts"
  fi

  tracked_local_env="$({
    git ls-files -z | tr '\0' '\n' | grep -E '(^|/)\.env($|\.)' | grep -vE '\.example$|\.sample$'
  } || true)"
  if [[ -n "$tracked_local_env" ]]; then
    fail "local environment files are tracked:\n$tracked_local_env"
  fi
fi

provenance_hits="$({
  git grep -n -I -E 'filecite|turn[0-9]+file[0-9]+' -- \
    README.md docs src tests examples scripts 2>/dev/null
} || true)"
if [[ -n "$provenance_hits" ]]; then
  fail "ChatGPT/file-search provenance markers remain:\n$provenance_hits"
fi

conflict_hits="$({
  git grep -n -I -E '^(<<<<<<<|=======|>>>>>>>)' -- \
    '*.py' '*.toml' '*.yml' '*.yaml' '*.json' '*.sh' 2>/dev/null
} || true)"
if [[ -n "$conflict_hits" ]]; then
  fail "merge-conflict markers remain:\n$conflict_hits"
fi

python3 - <<'PY'
from __future__ import annotations

import json
from pathlib import Path

root = Path.cwd()
json_files = [
    root / "PUBLIC_API_MANIFEST.json",
    root / "PUBLIC_ERROR_CODES.json",
    root / "ADAPTER_CONTRACT_MANIFEST.json",
    root / "REGULATORY_COMPATIBILITY_MATRIX.json",
]
for path in json_files:
    if not path.is_file():
        raise SystemExit(f"HYGIENE ERROR: required manifest missing: {path.name}")
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"HYGIENE ERROR: invalid JSON in {path.name}: {exc}") from exc
print("JSON manifests: valid")
PY

python3 -m compileall -q scripts src/pyaccountingkit
printf 'Python syntax: valid\n'

if [[ "$failures" -ne 0 ]]; then
  printf 'Repository hygiene: FAIL (%d issue group(s))\n' "$failures" >&2
  exit 1
fi

printf 'Repository hygiene: PASS\n'
