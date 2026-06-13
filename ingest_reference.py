"""Prepare user MP3/WAV files as ACE-Step cover source audio."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

BATCH_ROOT = Path(__file__).resolve().parent
AUDIO_TEMPLATE_DIR = BATCH_ROOT / "templates" / "audio"
DEFAULT_USER_MP3 = (
    AUDIO_TEMPLATE_DIR / "For HAPPY (Name) Birthday Song Happy Birthday to You.mp3"
)
FALLBACK_USER_MP3 = AUDIO_TEMPLATE_DIR / "Happy Birthday Song!!!.mp3"
PREPARED_WAV = AUDIO_TEMPLATE_DIR / "user_birthday_reference.wav"
SAMPLE_RATE = 48000


def probe_duration_sec(path: Path) -> float:
    """Return media duration in seconds via ffprobe."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(path),
    ]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def prepare_reference(
    src: Path,
    dst: Path = PREPARED_WAV,
    *,
    loop_to_duration_sec: float | None = None,
    pad_to_duration_sec: float | None = None,
) -> float:
    """Convert source audio to 48 kHz stereo WAV for ACE-Step.

    Args:
        src: User MP3 or WAV file.
        dst: Output WAV path.
        loop_to_duration_sec: Loop short clips to this length (cover mode).
        pad_to_duration_sec: Append silence if shorter (legacy padding).

    Returns:
        Final WAV duration in seconds.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(".tmp.wav")

    if loop_to_duration_sec is not None:
        cmd = [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(src),
            "-t",
            str(loop_to_duration_sec),
            "-ar",
            str(SAMPLE_RATE),
            "-ac",
            "2",
            str(tmp),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        tmp.replace(dst)
        return probe_duration_sec(dst)

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(src),
        "-ar",
        str(SAMPLE_RATE),
        "-ac",
        "2",
        str(tmp),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    tmp.replace(dst)

    duration = probe_duration_sec(dst)
    if pad_to_duration_sec is not None and duration < pad_to_duration_sec:
        pad_sec = pad_to_duration_sec - duration
        padded = dst.with_suffix(".padded.wav")
        pad_cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(dst),
            "-af",
            f"apad=pad_dur={pad_sec:.3f}",
            str(padded),
        ]
        subprocess.run(pad_cmd, check=True, capture_output=True)
        padded.replace(dst)
        duration = probe_duration_sec(dst)
    return duration


def resolve_user_reference(explicit: Path | None = None) -> Path | None:
    """Return the user template path if it exists."""
    if explicit is not None and explicit.exists():
        return explicit
    if DEFAULT_USER_MP3.exists():
        return DEFAULT_USER_MP3
    if FALLBACK_USER_MP3.exists():
        return FALLBACK_USER_MP3
    return None
