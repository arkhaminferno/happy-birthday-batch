"""Local audio forensic metrics aligned with streaming-platform detection signals.

Measures spectral flatness, stereo phase correlation, and loudness dynamics on
mastered tracks. Used by ``upload_verify`` before distributor upload.
"""

from __future__ import annotations

import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torchaudio

# AI mixes often score high flatness (over-uniform spectrum) vs live recordings.
SPECTRAL_FLATNESS_WARN = 0.42
SPECTRAL_FLATNESS_FAIL = 0.55

# Perfect L/R correlation suggests mathematically generated stereo fields.
STEREO_CORR_WARN = 0.985
STEREO_CORR_FAIL = 0.995

# ACE-Step exports are often brick-limited (~3 LU); fail only on extreme cases.
LRA_WARN = 3.5
LRA_FAIL = 2.0

ANALYSIS_SR = 16000
MAX_ANALYSIS_SEC = 180.0


@dataclass
class ForensicMetrics:
    """Measured forensic signals for one audio file."""

    duration_sec: float
    spectral_flatness_mean: float
    stereo_correlation: float | None
    loudness_range_lu: float | None

    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSON reports."""
        return asdict(self)


def _load_mono_stereo(path: Path) -> tuple[np.ndarray, np.ndarray | None, int]:
    """Load audio; return mono mix and optional stereo matrix (2, n)."""
    waveform, sample_rate = torchaudio.load(str(path))
    if sample_rate != ANALYSIS_SR:
        waveform = torchaudio.functional.resample(waveform, sample_rate, ANALYSIS_SR)
        sample_rate = ANALYSIS_SR
    max_samples = int(MAX_ANALYSIS_SEC * sample_rate)
    waveform = waveform[:, :max_samples]
    stereo = waveform.numpy() if waveform.shape[0] >= 2 else None
    mono = waveform.mean(dim=0, keepdim=True).numpy()
    return mono, stereo, sample_rate


def measure_spectral_flatness(mono: np.ndarray, sample_rate: int) -> float:
    """Mean spectral flatness — high values suggest over-uniform AI spectra."""
    tensor = torch.from_numpy(mono.astype(np.float32))
    spec = torchaudio.transforms.Spectrogram(n_fft=2048, hop_length=512)(tensor)
    power = spec.squeeze(0).numpy()
    power = np.clip(power, 1e-12, None)
    geo = np.exp(np.mean(np.log(power), axis=0))
    arith = np.mean(power, axis=0)
    flatness = geo / np.clip(arith, 1e-12, None)
    return float(np.mean(flatness))


def measure_stereo_correlation(stereo: np.ndarray) -> float:
    """Pearson correlation between L/R — near 1.0 can indicate synthetic stereo."""
    left = stereo[0]
    right = stereo[1]
    if left.size < 64:
        return 0.0
    corr = np.corrcoef(left, right)[0, 1]
    return float(corr)


def measure_lra(path: Path) -> float | None:
    """Loudness range (LU) via ffmpeg ebur128."""
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i",
        str(path),
        "-af",
        "ebur128=framelog=verbose",
        "-f",
        "null",
        "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    for line in result.stderr.splitlines():
        if "LRA:" in line:
            try:
                return float(line.split("LRA:")[1].split("LU")[0].strip())
            except (IndexError, ValueError):
                continue
    return None


def analyze_forensics(path: Path) -> ForensicMetrics:
    """Compute forensic metrics for one audio file."""
    path = path.resolve()
    mono, stereo, sample_rate = _load_mono_stereo(path)
    duration = mono.shape[-1] / sample_rate
    flatness = measure_spectral_flatness(mono, sample_rate)
    corr = measure_stereo_correlation(stereo) if stereo is not None else None
    lra = measure_lra(path)
    return ForensicMetrics(
        duration_sec=round(duration, 2),
        spectral_flatness_mean=round(flatness, 4),
        stereo_correlation=round(corr, 4) if corr is not None else None,
        loudness_range_lu=round(lra, 2) if lra is not None else None,
    )
