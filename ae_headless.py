"""Headless After Effects launch helpers for macOS and Windows."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from batch_birthday.ae_config import resolve_ae_app_bundle, resolve_afterfx_com

# AppleScript DoScriptFile is the most reliable launcher on AE 2025 Mac.
AE_UI_MODE = os.environ.get("AE_UI_MODE", "applescript").strip().lower()


def _ae_process_name() -> str:
    """Return the AE MacOS binary name for pgrep."""
    return "After Effects"


def is_ae_running() -> bool:
    """Return True when an After Effects process is still alive."""
    result = subprocess.run(
        ["pgrep", "-f", f"{_ae_process_name()} 20"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def quit_ae_mac(*, wait_sec: int = 30) -> None:
    """Quit After Effects and wait until the process exits."""
    if not is_ae_running():
        return
    app_name = resolve_ae_app_bundle().stem
    subprocess.run(
        ["osascript", "-e", f'tell application "{app_name}" to quit'],
        capture_output=True,
        text=True,
        check=False,
    )
    deadline = time.time() + wait_sec
    while time.time() < deadline:
        if not is_ae_running():
            time.sleep(2)
            return
        time.sleep(1)
    subprocess.run(
        ["pkill", "-f", "Adobe After Effects 20"],
        capture_output=True,
        text=True,
        check=False,
    )
    time.sleep(2)


def ensure_ae_ready() -> None:
    """Ensure AE is idle before launching the next JSX script."""
    quit_ae_mac()
    time.sleep(2)


def quit_ae(*, wait_sec: int = 30) -> None:
    """Quit After Effects and wait until the process exits."""
    if sys.platform == "win32":
        quit_ae_windows(wait_sec=wait_sec)
        return
    quit_ae_mac(wait_sec=wait_sec)


def launch_jsx(script_path: Path) -> None:
    """Launch JSX on the current platform and block until the script finishes."""
    if sys.platform == "win32":
        launch_jsx_windows(script_path)
        return
    launch_jsx_mac(script_path)


def launch_jsx_mac(script_path: Path) -> None:
    """Launch JSX on macOS and block until the script finishes."""
    ensure_ae_ready()
    script = str(script_path.resolve())
    mode = AE_UI_MODE

    if mode == "jxa":
        _launch_jxa(script)
        return
    if mode == "gui":
        _launch_gui(script)
        return
    if mode == "headless":
        _launch_noui(script)
        return

    _launch_applescript(script)


def _launch_noui(script: str) -> None:
    """Run JSX with -noui (often hangs on Mac)."""
    app_bundle = resolve_ae_app_bundle()
    binary = app_bundle / "Contents" / "MacOS" / "After Effects"
    cmd = [str(binary), "-noui", "-r", script]
    print("Launching AE headless (-noui)...")
    subprocess.run(cmd, capture_output=True, text=True, check=False)


def _launch_jxa(script: str) -> None:
    """Run JSX via JavaScript for Automation."""
    app_name = resolve_ae_app_bundle().stem
    escaped = script.replace("\\", "\\\\").replace('"', '\\"')
    jxa = (
        f'var ae = Application("{app_name}"); '
        f'ae.doScriptFile("{escaped}", {{override:true}});'
    )
    print(f"Launching AE via JXA ({app_name})...")
    result = subprocess.run(
        ["osascript", "-l", "JavaScript", "-e", jxa],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "JXA failed").strip())


def _launch_applescript(script: str) -> None:
    """Run JSX via AppleScript DoScriptFile with retries on AppleEvent timeout."""
    app_name = resolve_ae_app_bundle().stem
    escaped = script.replace("\\", "\\\\").replace('"', '\\"')
    applescript = (
        f'with timeout of 900 seconds\n'
        f'tell application "{app_name}"\n'
        f'activate\n'
        f'DoScriptFile "{escaped}" with override\n'
        f"end tell\n"
        f"end timeout"
    )
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        print(f"Launching AE via AppleScript ({app_name})... attempt {attempt}/{max_attempts}")
        result = subprocess.run(
            ["osascript", "-e", applescript],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return
        detail = (result.stderr or result.stdout or "AppleScript failed").strip()
        if attempt < max_attempts and (
            "timed out" in detail.lower()
            or "-1712" in detail
            or "second script" in detail.lower()
        ):
            print(f"AppleScript busy, quitting AE and retrying: {detail}")
            quit_ae_mac()
            time.sleep(5)
            continue
        raise RuntimeError(detail)


def _launch_gui(script: str) -> None:
    """Fallback: open AE with visible UI."""
    app_bundle = resolve_ae_app_bundle()
    cmd = ["open", "-g", "-a", str(app_bundle), "--args", "-r", script]
    print("Launching AE with UI (fallback)...")
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def quit_ae_windows(*, wait_sec: int = 30) -> None:
    """Quit After Effects on Windows."""
    subprocess.run(
        ["taskkill", "/IM", "AfterFX.exe", "/F"],
        capture_output=True,
        text=True,
        check=False,
    )
    time.sleep(min(wait_sec, 5))


def launch_jsx_windows(script_path: Path) -> None:
    """Run JSX via AfterFX.com -r on Windows."""
    quit_ae_windows()
    time.sleep(2)
    afterfx = resolve_afterfx_com()
    script = str(script_path.resolve())
    cmd = [str(afterfx), "-r", script]
    print(f"Launching AE via AfterFX.com ({afterfx.name})...")
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "AfterFX.com failed").strip()
        raise RuntimeError(detail)
