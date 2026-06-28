"""Prepend sung EDM countdown and trim weak opening — instant drop after Go."""

from __future__ import annotations

import shutil
import struct
import subprocess
import tempfile
from pathlib import Path

from batch_birthday.countdown_reference import (
    DEFAULT_BPM,
    DEFAULT_COUNTDOWN_BEATS,
    prepare_sung_countdown_mp3,
)

SAMPLE_RATE = 48000
DEFAULT_OPENING_TRIM_SEC = 0.0
DROP_SEARCH_START_SEC = 0.0
DROP_SEARCH_END_SEC = 8.0
COUNTDOWN_TAIL_TRIM_SEC = 0.14


def beat_duration_sec(bpm: int) -> float:
    """Return one beat length in seconds."""
    return 60.0 / bpm


def snap_to_beat(time_sec: float, bpm: int) -> float:
    """Snap a timestamp to the nearest BPM grid line."""
    beat = beat_duration_sec(bpm)
    return round(time_sec / beat) * beat


def _run_ffmpeg(cmd: list[str]) -> None:
    """Run ffmpeg and raise on failure."""
    subprocess.run(cmd, check=True, capture_output=True)


def _decode_mono_segment(src: Path, start_sec: float, end_sec: float) -> tuple[list[int], int]:
    """Decode a mono PCM slice for energy analysis."""
    duration = max(0.1, end_sec - start_sec)
    cmd = [
        "ffmpeg",
        "-ss",
        f"{start_sec:.6f}",
        "-t",
        f"{duration:.6f}",
        "-i",
        str(src),
        "-ac",
        "1",
        "-ar",
        "22050",
        "-f",
        "s16le",
        "-",
    ]
    raw = subprocess.run(cmd, check=True, capture_output=True).stdout
    if not raw:
        return [], 22050
    samples = struct.unpack("<" + "h" * (len(raw) // 2), raw)
    return list(samples), 22050


def detect_edm_drop_start(
    src: Path,
    *,
    bpm: int = DEFAULT_BPM,
    search_start_sec: float = DROP_SEARCH_START_SEC,
    search_end_sec: float = DROP_SEARCH_END_SEC,
    fallback_sec: float = DEFAULT_OPENING_TRIM_SEC,
) -> float:
    """Find the first loud EDM downbeat after a quiet merged intro."""
    samples, sample_rate = _decode_mono_segment(src, search_start_sec, search_end_sec)
    if not samples:
        return snap_to_beat(fallback_sec, bpm)

    window = max(1, int(0.05 * sample_rate))
    hop = max(1, window // 2)
    energies: list[tuple[float, float]] = []
    for index in range(0, len(samples) - window, hop):
        chunk = samples[index : index + window]
        energy = sum(value * value for value in chunk) / window
        energies.append((search_start_sec + index / sample_rate, energy))

    if len(energies) < 4:
        return 0.0

    baseline = sum(value for _, value in energies[:4]) / 4
    threshold = max(baseline * 1.6, baseline + 120_000)
    beat = beat_duration_sec(bpm)
    for time_sec, energy in energies:
        if energy < threshold:
            continue
        aligned = snap_to_beat(time_sec, bpm)
        return max(0.0, aligned)

    return 0.0


def trim_and_prepend_countdown(
    src: Path,
    dst: Path,
    *,
    countdown_mp3: Path,
    trim_start_sec: float,
    bpm: int = DEFAULT_BPM,
) -> None:
    """Hard-join countdown to the EDM drop with zero gap."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    aligned_trim = snap_to_beat(trim_start_sec, bpm)
    filter_complex = "[0:a][1:a]concat=n=2:v=0:a=1[aout]"
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(countdown_mp3),
        "-ss",
        f"{aligned_trim:.6f}",
        "-i",
        str(src),
        "-filter_complex",
        filter_complex,
        "-map",
        "[aout]",
        "-ar",
        str(SAMPLE_RATE),
        "-b:a",
        "192k",
    ]
    if dst.resolve() == src.resolve():
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False, dir=dst.parent) as tmp:
            tmp_path = Path(tmp.name)
        try:
            _run_ffmpeg([*cmd, str(tmp_path)])
            shutil.move(str(tmp_path), dst)
        finally:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
    else:
        _run_ffmpeg([*cmd, str(dst)])


def prepend_countdown(
    src: Path,
    dst: Path,
    *,
    countdown_mp3: Path,
    bpm: int = DEFAULT_BPM,
    beats: int = DEFAULT_COUNTDOWN_BEATS,
) -> dict[str, float | str | int | bool]:
    """Prepend Sarah-style countdown then the full song — no trim."""
    countdown_duration = prepare_sung_countdown_mp3(
        countdown_mp3,
        bpm=bpm,
        beats=beats,
        tail_trim_sec=COUNTDOWN_TAIL_TRIM_SEC,
    )
    trim_and_prepend_countdown(
        src,
        dst,
        countdown_mp3=countdown_mp3,
        trim_start_sec=0.0,
        bpm=bpm,
    )
    from batch_birthday.audio_merge import probe_duration_sec

    return {
        "countdown_mp3": str(countdown_mp3),
        "countdown_source": "sarah_sung_reference",
        "auto_detect_drop": False,
        "bpm": bpm,
        "countdown_beats": beats,
        "countdown_duration_sec": countdown_duration,
        "trim_start_sec": 0.0,
        "trim_aligned_sec": 0.0,
        "output_duration_sec": probe_duration_sec(dst),
    }


def apply_opening_edit(
    src: Path,
    dst: Path,
    *,
    countdown_mp3: Path,
    trim_start_sec: float | None = None,
    bpm: int = DEFAULT_BPM,
    beats: int = DEFAULT_COUNTDOWN_BEATS,
    auto_detect_drop: bool = True,
) -> dict[str, float | str | int | bool]:
    """Attach Sarah-style sung countdown, trim weak intro, and write final MP3."""
    if auto_detect_drop or trim_start_sec is None:
        aligned_trim = detect_edm_drop_start(
            src,
            bpm=bpm,
            fallback_sec=trim_start_sec or DEFAULT_OPENING_TRIM_SEC,
        )
    else:
        aligned_trim = snap_to_beat(trim_start_sec, bpm)

    countdown_duration = prepare_sung_countdown_mp3(
        countdown_mp3,
        bpm=bpm,
        beats=beats,
        tail_trim_sec=COUNTDOWN_TAIL_TRIM_SEC,
    )
    trim_and_prepend_countdown(
        src,
        dst,
        countdown_mp3=countdown_mp3,
        trim_start_sec=aligned_trim,
        bpm=bpm,
    )
    from batch_birthday.audio_merge import probe_duration_sec

    return {
        "countdown_mp3": str(countdown_mp3),
        "countdown_source": "sarah_sung_reference",
        "auto_detect_drop": auto_detect_drop,
        "bpm": bpm,
        "countdown_beats": beats,
        "countdown_duration_sec": countdown_duration,
        "trim_start_sec": trim_start_sec or DEFAULT_OPENING_TRIM_SEC,
        "trim_aligned_sec": aligned_trim,
        "output_duration_sec": probe_duration_sec(dst),
    }
