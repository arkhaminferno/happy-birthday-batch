"""Crossfade Verse 1 EDM cover into the original festival body."""

from __future__ import annotations

import subprocess
from pathlib import Path


def merge_party_song(
    intro: Path,
    verse1: Path,
    body: Path,
    dst: Path,
    *,
    intro_crossfade_sec: float = 0.5,
    body_crossfade_sec: float = 2.0,
    total_duration_sec: float | None = None,
) -> None:
    """Join intro → Verse 1 → body with short then longer crossfades."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    intro_fade = max(0.2, intro_crossfade_sec)
    body_fade = max(0.5, body_crossfade_sec)
    filter_complex = (
        f"[0:a][1:a]acrossfade=d={intro_fade}:c1=tri:c2=tri[opening];"
        f"[opening][2:a]acrossfade=d={body_fade}:c1=tri:c2=tri[aout]"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(intro),
        "-i",
        str(verse1),
        "-i",
        str(body),
        "-filter_complex",
        filter_complex,
        "-map",
        "[aout]",
        "-ar",
        "48000",
        "-b:a",
        "192k",
    ]
    if total_duration_sec is not None:
        cmd.extend(["-t", str(total_duration_sec)])
    cmd.append(str(dst))
    subprocess.run(cmd, check=True, capture_output=True)


def crossfade_merge(
    verse1: Path,
    body: Path,
    dst: Path,
    *,
    crossfade_sec: float = 2.0,
    total_duration_sec: float | None = None,
) -> None:
    """Crossfade Verse 1 into the body with no audible hard cut."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    fade = max(0.5, crossfade_sec)
    filter_complex = f"[0:a][1:a]acrossfade=d={fade}:c1=tri:c2=tri[aout]"
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(verse1),
        "-i",
        str(body),
        "-filter_complex",
        filter_complex,
        "-map",
        "[aout]",
        "-ar",
        "48000",
        "-b:a",
        "192k",
    ]
    if total_duration_sec is not None:
        cmd.extend(["-t", str(total_duration_sec)])
    cmd.append(str(dst))
    subprocess.run(cmd, check=True, capture_output=True)


def probe_duration_sec(path: Path) -> float:
    """Return audio duration in seconds via ffprobe."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return float(result.stdout.strip())
