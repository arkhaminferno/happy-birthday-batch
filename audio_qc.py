"""Audio quality gates for generated pipeline stages."""

from __future__ import annotations

import math
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from batch_birthday.audio_merge import probe_duration_sec

SAMPLE_RATE = 48000


class AudioQCError(RuntimeError):
    """Raised when a generated audio stage is unsafe to merge."""


@dataclass(frozen=True)
class AudioQCReport:
    """Basic audio statistics used to gate a stage."""

    path: str
    duration_sec: float
    rms_db: float
    peak: float
    clipped_fraction: float

    def to_dict(self) -> dict[str, float | str]:
        """Serialize report for JSON sidecars."""
        return asdict(self)


def _decode_mono(path: Path) -> np.ndarray:
    """Decode audio to mono float32 samples via ffmpeg."""
    cmd = [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        str(path),
        "-f",
        "f32le",
        "-acodec",
        "pcm_f32le",
        "-ac",
        "1",
        "-ar",
        str(SAMPLE_RATE),
        "-",
    ]
    result = subprocess.run(cmd, check=True, capture_output=True)
    return np.frombuffer(result.stdout, dtype=np.float32)


def analyze_audio(path: Path) -> AudioQCReport:
    """Return duration, RMS, peak, and clipping stats for a file."""
    if not path.exists() or path.stat().st_size == 0:
        raise AudioQCError(f"Audio file missing or empty: {path}")
    samples = _decode_mono(path)
    if samples.size == 0:
        raise AudioQCError(f"Audio decode produced no samples: {path}")
    finite = samples[np.isfinite(samples)]
    if finite.size == 0:
        raise AudioQCError(f"Audio decode produced no finite samples: {path}")
    peak = float(np.max(np.abs(finite)))
    rms = float(np.sqrt(np.mean(np.square(finite))))
    rms_db = 20.0 * math.log10(max(rms, 1e-9))
    clipped_fraction = float(np.mean(np.abs(finite) >= 0.999))
    return AudioQCReport(
        path=str(path),
        duration_sec=probe_duration_sec(path),
        rms_db=rms_db,
        peak=peak,
        clipped_fraction=clipped_fraction,
    )


def validate_audio(
    path: Path,
    *,
    label: str,
    min_duration_sec: float,
    max_duration_sec: float,
    min_rms_db: float = -42.0,
    min_peak: float = 0.01,
    max_clipped_fraction: float = 0.02,
) -> AudioQCReport:
    """Raise if a generated stage is silent, too short/long, or clipped."""
    report = analyze_audio(path)
    if report.duration_sec < min_duration_sec:
        raise AudioQCError(
            f"{label} too short: {report.duration_sec:.1f}s < {min_duration_sec:.1f}s"
        )
    if report.duration_sec > max_duration_sec:
        raise AudioQCError(
            f"{label} too long: {report.duration_sec:.1f}s > {max_duration_sec:.1f}s"
        )
    if report.rms_db < min_rms_db:
        raise AudioQCError(f"{label} too quiet/silent: RMS {report.rms_db:.1f} dB")
    if report.peak < min_peak:
        raise AudioQCError(f"{label} peak too low: {report.peak:.4f}")
    if report.clipped_fraction > max_clipped_fraction:
        raise AudioQCError(
            f"{label} clipped: {report.clipped_fraction:.2%} samples near full scale"
        )
    return report
