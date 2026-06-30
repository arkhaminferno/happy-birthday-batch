"""Run After Effects JSX and aerender for one render job."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from batch_birthday.ae_config import AE_WORK_ROOT, resolve_aerender
from batch_birthday.ae_headless import launch_jsx, quit_ae
from batch_birthday.ae_launcher import ACTIVE_SCRIPT, SMOKE_PROJECT, write_active_script
from batch_birthday.ae_render_job import RenderJob, write_render_job


def _wait_for_project(project_path: Path, *, timeout_sec: int = 900) -> None:
    """Poll until AE saves the expected .aep project file."""
    deadline = time.time() + timeout_sec
    last_size = -1
    stable_reads = 0
    while time.time() < deadline:
        if project_path.is_file():
            size = project_path.stat().st_size
            if size > 10_000 and size == last_size:
                stable_reads += 1
                if stable_reads >= 2:
                    return
            else:
                stable_reads = 0
            last_size = size
        time.sleep(2)
    raise TimeoutError(
        f"After Effects did not save project within {timeout_sec}s: {project_path}\n"
        "Enable: Preferences > Scripting & Expressions > "
        "Allow Scripts to Write Files and Access Network"
    )


def run_active_script(
    *,
    expect_project: Path | None = None,
    timeout_sec: int = 900,
) -> None:
    """Launch AE script and wait for the saved project file."""
    if not ACTIVE_SCRIPT.is_file():
        raise FileNotFoundError(f"Missing bundled script: {ACTIVE_SCRIPT}")

    print("Launching After Effects script...")
    print(f"  mode: {os.environ.get('AE_UI_MODE', 'applescript')}")
    print(f"  script: {ACTIVE_SCRIPT}")
    launch_jsx(ACTIVE_SCRIPT)
    if expect_project is not None:
        _wait_for_project(expect_project, timeout_sec=timeout_sec)
        print(f"Project saved: {expect_project}")


def run_jsx_script(
    body_script_name: str,
    *,
    job: RenderJob | None = None,
    expect_project: Path | None = None,
    timeout_sec: int = 900,
) -> None:
    """Bundle a script body and launch it in After Effects."""
    job_dict = job.to_dict() if job else None
    write_active_script(body_script_name, job=job_dict)
    run_active_script(expect_project=expect_project, timeout_sec=timeout_sec)


def run_aerender(job: RenderJob, *, timeout_sec: int = 7200) -> Path:
    """Render the saved per-slug project to MP4."""
    aerender = resolve_aerender()
    job.output_mp4.parent.mkdir(parents=True, exist_ok=True)
    if job.output_mp4.exists():
        job.output_mp4.unlink()

    cmd = [
        str(aerender),
        "-project",
        str(job.project_path.resolve()),
        "-comp",
        str(job.to_dict()["render_comp"]),
        "-output",
        str(job.output_mp4.resolve()),
    ]
    print("Starting aerender (headless, several minutes)...")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        check=False,
    )
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())
    if job.output_mp4.is_file() and job.output_mp4.stat().st_size > 1_000_000:
        return job.output_mp4
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "unknown aerender error").strip()
        raise RuntimeError(f"aerender failed for {job.slug}: {detail}")
    if not job.output_mp4.is_file():
        raise RuntimeError(f"aerender finished but MP4 missing: {job.output_mp4}")
    raise RuntimeError(f"aerender output too small: {job.output_mp4}")


def prepare_project(job: RenderJob) -> Path:
    """Write job JSON, run JSX to customize template, and save per-slug project."""
    write_render_job(job)
    job.project_path.parent.mkdir(parents=True, exist_ok=True)
    if job.project_path.exists():
        job.project_path.unlink()
    run_jsx_script(
        "render_job.jsx",
        job=job,
        expect_project=job.project_path,
    )
    return job.project_path


def render_job(job: RenderJob, *, cooldown_sec: int = 8) -> Path:
    """Full pipeline: JSX prep, aerender export, short cooldown."""
    prepare_project(job)
    quit_ae()
    output = run_aerender(job)
    quit_ae()
    if cooldown_sec > 0:
        time.sleep(cooldown_sec)
    return output
