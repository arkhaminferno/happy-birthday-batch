"""FFmpeg helpers for mastering audio and rendering simple birthday videos."""

from __future__ import annotations

import subprocess
from pathlib import Path


def master_mp3_vocal_forward(src: Path, dst: Path) -> None:
    """Normalize and boost vocal presence so lyrics are easier to hear."""
    af = (
        "highpass=f=100,"
        "equalizer=f=2500:width_type=h:width=1.5:g=2.5,"
        "equalizer=f=5000:width_type=h:width=1:g=1.5,"
        "compand=attacks=0.3:decays=0.8:points=-80/-80|-20/-15|-5/-5|0/-3,"
        "loudnorm=I=-14:TP=-1.5:LRA=11"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(src),
        "-af",
        af,
        "-ar",
        "48000",
        "-b:a",
        "192k",
        str(dst),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def master_mp3(src: Path, dst: Path) -> None:
    """Apply light loudness normalization to the generated MP3."""
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(src),
        "-af",
        "loudnorm=I=-14:TP=-1.5:LRA=11",
        "-ar",
        "48000",
        "-b:a",
        "192k",
        str(dst),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def render_video(
    mp3_path: Path,
    name: str,
    out_mp4: Path,
    duration_sec: int,
    background: Path | None = None,
) -> None:
    """Render a 1080p MP4 with title overlay and the birthday audio."""
    title = f"Happy Birthday {name}!"
    safe_title = title.replace(":", "\\:").replace("'", "\\'")

    if background and background.exists():
        video_input = ["-stream_loop", "-1", "-i", str(background)]
    else:
        video_input = [
            "-f",
            "lavfi",
            "-i",
            f"color=c=0x2d1b69:s=1920x1080:d={duration_sec}",
        ]

    vf = (
        f"drawtext=text='{safe_title}':fontsize=72:fontcolor=white:"
        f"x=(w-text_w)/2:y=h*0.12:shadowcolor=black:shadowx=2:shadowy=2"
    )

    cmd = [
        "ffmpeg",
        "-y",
        *video_input,
        "-i",
        str(mp3_path),
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        "-t",
        str(duration_sec),
        str(out_mp4),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
