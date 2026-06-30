"""Locate ACE-Step and help start or probe the local generation API."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import requests

from batch_birthday.orchestrator import BATCH_ROOT, DEFAULT_API_BASE

ACESTEP_REPO_NAMES = ("ACE-Step-1.5", "ACE-Step", "acestep")


def resolve_acestep_root() -> Path | None:
    """Return the ACE-Step repo root if it can be found on disk."""
    env = os.environ.get("ACESTEP_ROOT", "").strip()
    if env:
        candidate = Path(env).expanduser().resolve()
        if _is_acestep_root(candidate):
            return candidate

    parent = BATCH_ROOT.parent
    if _is_acestep_root(parent):
        return parent

    for name in ACESTEP_REPO_NAMES:
        candidate = parent / name
        if _is_acestep_root(candidate):
            return candidate
    return None


def _is_acestep_root(path: Path) -> bool:
    """Return True when path looks like an ACE-Step checkout."""
    return (path / "acestep").is_dir() and (
        (path / "pyproject.toml").is_file() or (path / "start_api_server.bat").is_file()
    )


def acestep_start_command() -> list[str]:
    """Return the platform-specific command to start the ACE-Step API."""
    root = resolve_acestep_root()
    if root is None:
        raise FileNotFoundError(
            "ACE-Step not found. Clone https://github.com/ace-step/ACE-Step-1.5 "
            "next to this repo or set ACESTEP_ROOT."
        )
    if sys.platform == "win32":
        script = root / "start_api_server.bat"
    elif sys.platform == "darwin":
        script = root / "start_api_server_macos.sh"
        if not script.is_file():
            script = root / "start_api_server.sh"
    else:
        script = root / "start_api_server.sh"
    if not script.is_file():
        raise FileNotFoundError(f"ACE-Step API launcher not found: {script}")
    if sys.platform == "win32":
        return ["cmd", "/c", str(script)]
    return ["bash", str(script)]


def api_health(api_base: str = DEFAULT_API_BASE) -> dict[str, object]:
    """Fetch /health from the ACE-Step API."""
    response = requests.get(f"{api_base.rstrip('/')}/health", timeout=30)
    response.raise_for_status()
    return response.json().get("data", {})


def init_llm_models(
    api_base: str = DEFAULT_API_BASE,
    *,
    lm_model_path: str = "acestep-5Hz-lm-1.7B",
) -> dict[str, object]:
    """POST /v1/init to load DiT + LLM (required for sung lyrics)."""
    payload = {
        "model": "acestep-v15-turbo",
        "init_llm": True,
        "lm_model_path": lm_model_path,
    }
    response = requests.post(
        f"{api_base.rstrip('/')}/v1/init",
        json=payload,
        timeout=600,
    )
    response.raise_for_status()
    body = response.json()
    if body.get("code") != 200:
        raise RuntimeError(body.get("error") or "Model init failed")
    return body.get("data", {})


def which_or_none(name: str) -> str | None:
    """Return executable path from PATH, or None."""
    from shutil import which

    found = which(name)
    return found


def run_doctor() -> int:
    """Print environment checks for Mac/Windows batch workflows."""
    ok = True
    print("CelebrateVibes environment check")
    print(f"  Batch root:     {BATCH_ROOT}")
    print(f"  Platform:       {sys.platform}")
    print(f"  Python:         {sys.version.split()[0]}")

    for tool in ("ffmpeg", "ffprobe"):
        path = which_or_none(tool)
        status = path or "MISSING"
        print(f"  {tool + ':':<16} {status}")
        if not path:
            ok = False

    template = BATCH_ROOT / "ae_template" / "Happy birthday.aep"
    print(f"  AE template:    {'OK' if template.is_file() else 'MISSING'}")

    try:
        from batch_birthday.ae_config import resolve_aerender

        aerender = resolve_aerender()
        print(f"  aerender:       {aerender}")
    except FileNotFoundError as exc:
        print(f"  aerender:       MISSING ({exc})")
        ok = False

    acestep = resolve_acestep_root()
    print(f"  ACE-Step root:  {acestep or 'NOT FOUND (set ACESTEP_ROOT)'}")

    try:
        health = api_health()
        llm = health.get("llm_initialized")
        print(f"  API {DEFAULT_API_BASE}:  up, llm_initialized={llm}")
        if not llm:
            print("    → Run: celebratevibes init-api")
    except requests.RequestException:
        print(f"  API {DEFAULT_API_BASE}:  DOWN")
        print("    → Start ACE-Step API in another terminal (see SETUP.md)")
        ok = False

    if ok:
        print("\nReady for audio + video batch workflows.")
        return 0
    print("\nFix the items marked MISSING, then run celebratevibes doctor again.")
    return 1
