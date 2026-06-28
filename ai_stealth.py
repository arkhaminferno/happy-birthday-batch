"""Post-humanize pass to lower local AI-music detector scores before upload."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from batch_birthday.ai_music_detector import DEFAULT_THRESHOLD, run_ai_detectors
from batch_birthday.batch_variation import _digest

STEALTH_AI_TARGET = 0.01
SAMPLE_RATE = 48000
# Safe pitch-shift rates that break fakeprint fingerprints without audible drift.
STEALTH_PITCH_RATES = (0.995, 0.9945, 0.9955, 0.994, 0.9985)


def stealth_pitch_rate_for(name: str) -> float:
    """Return a per-name pitch rate inside the detector-safe band."""
    slot = _digest(name)[0] / 255.0
    return round(0.994 + slot * 0.0015, 4)


def build_stealth_filter(
    *,
    pitch_rate: float,
    loudness_i: float = -14.2,
    lra_target: float = 11.0,
) -> str:
    """Build ffmpeg audio filter that breaks AI spectral fingerprints."""
    tempo = 1.0 / pitch_rate
    return (
        f"asetrate={SAMPLE_RATE}*{pitch_rate},aresample={SAMPLE_RATE},"
        f"atempo={tempo:.5f},"
        f"loudnorm=I={loudness_i}:TP=-1.0:LRA={lra_target}"
    )


def apply_stealth_mp3(
    src: Path,
    dst: Path,
    *,
    pitch_rate: float,
) -> Path:
    """Apply stealth pitch/loudness pass to one MP3."""
    src = src.resolve()
    dst = dst.resolve()
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(src),
        "-af",
        build_stealth_filter(pitch_rate=pitch_rate),
        "-ar",
        str(SAMPLE_RATE),
        "-c:a",
        "libmp3lame",
        "-b:a",
        "192k",
        str(dst),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return dst


def _measure_ai_probability(mp3_path: Path) -> float:
    """Return primary fakeprint AI probability for one MP3."""
    detections = run_ai_detectors(mp3_path, threshold=DEFAULT_THRESHOLD)
    return detections[0].ai_probability if detections else 1.0


def harden_for_upload(
    src: Path,
    dst: Path,
    *,
    name: str,
    target_ai: float = STEALTH_AI_TARGET,
) -> tuple[Path, float, float]:
    """Pick the lowest-scoring stealth pitch rate at or below *target_ai*.

    Returns:
        Tuple of output path, chosen pitch rate, and measured AI probability.
    """
    preferred = stealth_pitch_rate_for(name)
    candidates = [preferred]
    for rate in STEALTH_PITCH_RATES:
        if rate not in candidates:
            candidates.append(rate)

    best_path: Path | None = None
    best_rate = preferred
    best_ai = 1.0

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        for rate in candidates:
            candidate = tmp / f"stealth_{rate:.4f}.mp3"
            apply_stealth_mp3(src, candidate, pitch_rate=rate)
            ai_prob = _measure_ai_probability(candidate)
            if ai_prob < best_ai:
                best_ai = ai_prob
                best_rate = rate
                best_path = candidate
            if ai_prob <= target_ai:
                break

        if best_path is None:
            raise RuntimeError(f"Stealth hardening failed for {src}")

        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(best_path.read_bytes())

    return dst, best_rate, best_ai
