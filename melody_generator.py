"""Fixed worldwide Happy Birthday melody — identical for every song.

Prefers a real sung Happy Birthday recording as the cover anchor (carries the
famous tune reliably); falls back to a synthesized melody when no recording is
present. Cover mode needs real vocal phrasing to reproduce the melody — a bare
sine tone is a poor anchor.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from batch_birthday.ingest_reference import probe_duration_sec
from batch_birthday.pipeline_paths import (
    BATCH_ROOT,
    FIXED_MELODY_WAV,
    SHARED_MELODY_DIR,
)

SAMPLE_RATE = 48000
DEFAULT_BPM = 128
# Traditional Happy Birthday is usually sung around this tempo (3/4 waltz).
HB_SOURCE_BPM = 132
HB_MAX_SEC = 18.0

# Real sung Happy Birthday recordings, best (shortest, ~1 verse) first.
_REFERENCE_CANDIDATES = (
    "Happy Birthday Viraj (2).mp3",
    "For HAPPY (Name) Birthday Song Happy Birthday to You.mp3",
    "Happy Birthday Song!!!.mp3",
)


def resolve_melody_source(*, bpm: int = DEFAULT_BPM) -> Path:
    """Return the best Happy Birthday cover anchor (real recording or synth)."""
    audio_dir = BATCH_ROOT / "templates" / "audio"
    for name in _REFERENCE_CANDIDATES:
        candidate = audio_dir / name
        if candidate.exists() and candidate.stat().st_size > 0:
            return candidate
    return ensure_melody_wav(bpm=bpm)


def prepare_hb_cover_source(
    src: Path,
    dst: Path,
    *,
    target_bpm: int = DEFAULT_BPM,
    source_bpm: int = HB_SOURCE_BPM,
    max_sec: float = HB_MAX_SEC,
) -> float:
    """Convert HB recording to 48 kHz stereo WAV, tempo-aligned for cover mode.

    Slows/speeds the source toward *target_bpm* and trims to one verse length.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    atempo = target_bpm / source_bpm
    filters = []
    if abs(atempo - 1.0) > 0.005:
        filters.append(f"atempo={atempo:.6f}")
    af = ",".join(filters) if filters else "anull"
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(src),
        "-af",
        af,
        "-t",
        str(max_sec),
        "-ar",
        str(SAMPLE_RATE),
        "-ac",
        "2",
        str(dst),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return probe_duration_sec(dst)


# Classic "Happy Birthday to You" in C major (one complete verse).
_MELODY = [
    67, 67, 69, 67, 72, 71,
    67, 67, 69, 67, 74, 72,
    67, 67, 67, 76, 72, 71, 69,
    75, 75, 76, 72, 74, 72,
]
_NOTE_BEATS = [
    1, 1, 1, 1, 2, 2,
    1, 1, 1, 1, 2, 2,
    1, 1, 1, 1, 2, 1, 1,
    2, 2, 1, 1, 2, 2,
]


def _midi_to_hz(note: int) -> float:
    return 440.0 * (2.0 ** ((note - 69) / 12.0))


def _tone(freq: float, duration_sec: float, volume: float = 0.35) -> np.ndarray:
    """Simple piano-like tone with a quick decay."""
    n = max(1, int(SAMPLE_RATE * duration_sec))
    t = np.linspace(0, duration_sec, n, endpoint=False)
    wave = np.sin(2 * np.pi * freq * t)
    wave += 0.35 * np.sin(2 * np.pi * freq * 2 * t)
    env = np.exp(-3.0 * t / max(duration_sec, 0.05))
    return (wave * env * volume).astype(np.float32)


def build_phrase(*, bpm: int = DEFAULT_BPM) -> np.ndarray:
    """Build one pass of the Happy Birthday melody at the given BPM."""
    beat_sec = 60.0 / bpm
    chunks: list[np.ndarray] = []
    for note, beats in zip(_MELODY, _NOTE_BEATS):
        dur = beats * beat_sec
        if note <= 0:
            chunks.append(np.zeros(int(SAMPLE_RATE * dur), dtype=np.float32))
        else:
            chunks.append(_tone(_midi_to_hz(note), dur))
    return np.concatenate(chunks)


def phrase_duration_sec(*, bpm: int = DEFAULT_BPM) -> float:
    """Return the length of one complete Happy Birthday verse."""
    return len(build_phrase(bpm=bpm)) / SAMPLE_RATE


def ensure_melody_wav(
    *,
    output: Path | None = None,
    bpm: int = DEFAULT_BPM,
) -> Path:
    """Write the shared fixed melody WAV if missing; return its path."""
    dst = output or FIXED_MELODY_WAV
    if dst.exists() and dst.stat().st_size > 0:
        return dst
    SHARED_MELODY_DIR.mkdir(parents=True, exist_ok=True)
    mono = build_phrase(bpm=bpm)
    stereo = np.stack([mono, mono], axis=1)
    peak = np.max(np.abs(stereo))
    if peak > 0:
        stereo = stereo / peak * 0.9
    wavfile.write(str(dst), SAMPLE_RATE, (stereo * 32767).astype(np.int16))
    return dst
