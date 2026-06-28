"""Sung EDM countdown clip derived from the Sarah reference track."""

from __future__ import annotations

import subprocess
from pathlib import Path

from batch_birthday.pipeline_paths import BATCH_ROOT

SAMPLE_RATE = 48000
DEFAULT_BPM = 128
DEFAULT_COUNTDOWN_BEATS = 4
SARAH_COUNTDOWN_SOURCE = (
    BATCH_ROOT
    / "output"
    / "sarah-birthday-edm-party"
    / "sarah-birthday-edm-party_upload.mp3"
)
DEFAULT_COUNTDOWN_TEMPLATE = BATCH_ROOT / "templates" / "audio" / "sarah_edm_countdown.mp3"


def countdown_duration_sec(bpm: int, beats: int = DEFAULT_COUNTDOWN_BEATS) -> float:
    """Return countdown length in seconds for *beats* at *bpm*."""
    return beats * 60.0 / bpm


def _run_ffmpeg(cmd: list[str]) -> None:
    """Run ffmpeg and raise on failure."""
    subprocess.run(cmd, check=True, capture_output=True)


def extract_countdown_template(
    source_mp3: Path,
    dst: Path,
    *,
    bpm: int = DEFAULT_BPM,
    beats: int = DEFAULT_COUNTDOWN_BEATS,
) -> float:
    """Slice the sung 3-2-1-Go intro from a full Sarah-style ACE-Step export."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    duration_sec = countdown_duration_sec(bpm, beats)
    fade_start = max(0.0, duration_sec - 0.12)
    _run_ffmpeg(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source_mp3),
            "-t",
            f"{duration_sec:.6f}",
            "-af",
            f"afade=t=out:st={fade_start:.6f}:d=0.12,"
            "loudnorm=I=-16:TP=-1.5:LRA=8",
            "-ar",
            str(SAMPLE_RATE),
            "-ac",
            "2",
            "-b:a",
            "192k",
            str(dst),
        ]
    )
    from batch_birthday.audio_merge import probe_duration_sec

    return probe_duration_sec(dst)


def ensure_countdown_template(
    template_mp3: Path = DEFAULT_COUNTDOWN_TEMPLATE,
    *,
    source_mp3: Path = SARAH_COUNTDOWN_SOURCE,
    bpm: int = DEFAULT_BPM,
    beats: int = DEFAULT_COUNTDOWN_BEATS,
) -> Path:
    """Build the shared countdown template from Sarah if it is missing."""
    if template_mp3.exists() and template_mp3.stat().st_size > 0:
        return template_mp3
    if not source_mp3.exists():
        raise FileNotFoundError(
            f"Sarah countdown reference not found: {source_mp3}. "
            "Generate sarah-birthday-edm-party first or set a custom source."
        )
    extract_countdown_template(source_mp3, template_mp3, bpm=bpm, beats=beats)
    return template_mp3


def prepare_sung_countdown_mp3(
    dst: Path,
    *,
    bpm: int = DEFAULT_BPM,
    beats: int = DEFAULT_COUNTDOWN_BEATS,
    template_mp3: Path = DEFAULT_COUNTDOWN_TEMPLATE,
    source_mp3: Path = SARAH_COUNTDOWN_SOURCE,
    tail_trim_sec: float = 0.0,
) -> float:
    """Copy the Sarah-style sung countdown clip for the current song."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    template = ensure_countdown_template(
        template_mp3,
        source_mp3=source_mp3,
        bpm=bpm,
        beats=beats,
    )
    duration_sec = max(0.5, countdown_duration_sec(bpm, beats) - tail_trim_sec)
    _run_ffmpeg(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(template),
            "-t",
            f"{duration_sec:.6f}",
            "-af",
            "afade=t=out:st=0:d=0.01",
            "-ar",
            str(SAMPLE_RATE),
            "-ac",
            "2",
            "-b:a",
            "192k",
            str(dst),
        ]
    )
    from batch_birthday.audio_merge import probe_duration_sec

    return probe_duration_sec(dst)
