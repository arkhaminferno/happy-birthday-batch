"""FFmpeg helpers to stitch generated song segments."""

from __future__ import annotations

import subprocess
from pathlib import Path


def stitch_crossfade(
    intro: Path,
    body: Path,
    dst: Path,
    *,
    crossfade_sec: float = 2.5,
    total_duration_sec: float | None = None,
) -> None:
    """Crossfade intro into body and write a single MP3.

    Args:
        intro: Opening segment (classic HB on beat).
        body: Main dance party segment.
        dst: Output path.
        crossfade_sec: Overlap length in seconds.
        total_duration_sec: Optional hard trim/pad to exact length.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    fade = max(0.5, crossfade_sec)
    filter_complex = (
        f"[0:a][1:a]acrossfade=d={fade}:c1=tri:c2=tri[aout]"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(intro),
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
