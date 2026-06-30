#!/usr/bin/env bash
# Run CelebrateVibes batch CLI from any clone folder name.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if command -v celebratevibes >/dev/null 2>&1; then
  exec celebratevibes "$@"
fi
if command -v uv >/dev/null 2>&1; then
  exec uv run celebratevibes "$@"
fi
exec python3 cli_entry.py "$@"
