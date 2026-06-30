"""Paths and layer names for the CelebrateVibes After Effects template."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from batch_birthday.orchestrator import BATCH_ROOT

REPO_ROOT = BATCH_ROOT.parent

TEMPLATE_ROOT = REPO_ROOT / "adobe after effect template" / "Adobe after effect files"
TEMPLATE_AEP = TEMPLATE_ROOT / "Happy birthday.aep"

# Names discovered from Happy birthday.aep (not the old KT doc labels).
EDIT_COMP_NAME = "Happy Birthday"
EDIT_COMP_FALLBACKS = ("EDIT LOOP", "Pre-comp 1", "Fireworks")
RENDER_COMP_NAME = "MAIN 2Min+"
NAME_TEXT_LAYER = "Rajesh"
ADJUST_LAYER_NAME = "ADJUST HERE"

AE_WORK_ROOT = BATCH_ROOT / "ae_work"
AE_JOBS_DIR = AE_WORK_ROOT / "jobs"
AE_PROJECTS_DIR = AE_WORK_ROOT / "projects"
AE_SCRIPTS_DIR = BATCH_ROOT / "ae_scripts"
CURRENT_JOB_POINTER = AE_WORK_ROOT / "current_job_path.txt"

MAC_AE_APP_CANDIDATES = (
    "/Applications/Adobe After Effects 2025/Adobe After Effects 2025.app",
    "/Applications/Adobe After Effects 2024/Adobe After Effects 2024.app",
)
MAC_AERENDER_CANDIDATES = (
    "/Applications/Adobe After Effects 2025/aerender",
    "/Applications/Adobe After Effects 2024/aerender",
)


def resolve_ae_app_bundle() -> Path:
    """Return the After Effects .app bundle path for Mac open --args."""
    for candidate in MAC_AE_APP_CANDIDATES:
        path = Path(candidate)
        if path.is_dir():
            return path
    raise FileNotFoundError(
        "After Effects app not found. Install AE 2024/2025 or set AE_APP_PATH."
    )


def resolve_aerender() -> Path:
    """Return aerender for headless comp export."""
    for candidate in MAC_AERENDER_CANDIDATES:
        path = Path(candidate)
        if path.is_file():
            return path
    found = shutil.which("aerender")
    if found:
        return Path(found)
    override = os.environ.get("AERENDER_PATH", "").strip()
    if override and Path(override).is_file():
        return Path(override)
    raise FileNotFoundError(
        "aerender not found. Install After Effects or set AERENDER_PATH."
    )
