#!/usr/bin/env bash
# One-time setup for macOS (Apple Silicon or Intel).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "== CelebrateVibes setup (macOS) =="

if ! command -v git >/dev/null 2>&1; then
  echo "Install Xcode Command Line Tools / git first."
  exit 1
fi

if command -v git-lfs >/dev/null 2>&1; then
  git lfs install
  git lfs pull
else
  echo "WARN: git-lfs not found — install with: brew install git-lfs"
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "WARN: ffmpeg not found — install with: brew install ffmpeg"
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

echo "Installing batch dependencies..."
uv sync

ACESTEP_DIR="${ACESTEP_ROOT:-$ROOT/../ACE-Step-1.5}"
if [[ -d "$ACESTEP_DIR/acestep" ]]; then
  echo "ACE-Step found at: $ACESTEP_DIR"
else
  echo ""
  echo "ACE-Step not found at: $ACESTEP_DIR"
  echo "Clone it for audio generation:"
  echo "  git clone https://github.com/ace-step/ACE-Step-1.5.git \"$ACESTEP_DIR\""
  echo "  cd \"$ACESTEP_DIR\" && uv sync"
  echo "Or set ACESTEP_ROOT to your existing checkout."
fi

echo ""
echo "Setup complete. Next steps:"
echo "  1) Terminal A — start API:"
echo "       bash scripts/start_acestep_api.sh"
echo "  2) Terminal B — init LLM (first time):"
echo "       ./scripts/batch.sh init-api"
echo "  3) Generate + render:"
echo "       ./scripts/batch.sh generic-intro --force --video"
echo "       ./scripts/batch.sh ae-batch --slug rahul-in-birthday-edm-party --limit 1"
echo "  4) Health check:"
echo "       ./scripts/batch.sh doctor"
