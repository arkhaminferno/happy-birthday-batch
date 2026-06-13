"""AI-generated music detection for batch_birthday pre-upload QC.

Uses the spectral fakeprint method (Afchar et al., ISMIR 2025) with the
``lofcz/ai-music-detector`` logistic-regression weights from Hugging Face.
Optionally runs Veridex ``SpectralSignal`` when that package is installed.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torchaudio
from scipy import interpolate

BATCH_ROOT = Path(__file__).resolve().parent
MODEL_DIR = BATCH_ROOT / "models" / "ai-music-detector"
HF_REPO = "lofcz/ai-music-detector"
DEFAULT_THRESHOLD = 0.5
MIN_AUDIO_SEC = 10.0


@dataclass(frozen=True)
class FakeprintConfig:
    """Preprocessing settings for lofcz/ai-music-detector."""

    sample_rate: int = 16000
    n_fft: int = 8192
    freq_min: int = 1000
    freq_max: int = 8000
    hull_area: int = 10
    max_db: float = 5.0
    min_db: float = -45.0
    max_duration_sec: float = 180.0


@dataclass
class AiDetectionResult:
    """Result from one AI-music detector backend."""

    detector_id: str
    ai_probability: float
    label: str
    threshold: float
    passed: bool
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSON reports."""
        return asdict(self)


def _load_fakeprint_config() -> FakeprintConfig:
    """Load preprocessing config bundled with the Hugging Face model."""
    cfg_path = MODEL_DIR / "preprocessing_config.json"
    if not cfg_path.exists():
        return FakeprintConfig()
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    return FakeprintConfig(
        sample_rate=int(data.get("sample_rate", 16000)),
        n_fft=int(data.get("n_fft", 8192)),
        freq_min=int(data.get("freq_min", 1000)),
        freq_max=int(data.get("freq_max", 8000)),
        hull_area=int(data.get("hull_area", 10)),
        max_db=float(data.get("max_db", 5.0)),
        min_db=float(data.get("min_db", -45.0)),
    )


def ensure_detector_model() -> Path:
    """Download lofcz/ai-music-detector weights if missing."""
    weights_path = MODEL_DIR / "model.safetensors"
    if weights_path.exists():
        return weights_path

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    try:
        from huggingface_hub import hf_hub_download
    except ImportError as exc:
        raise RuntimeError(
            "huggingface_hub is required to download ai-music-detector weights"
        ) from exc

    for filename in ("model.safetensors", "preprocessing_config.json", "config.json"):
        cached = hf_hub_download(repo_id=HF_REPO, filename=filename)
        target = MODEL_DIR / filename
        if not target.exists():
            target.write_bytes(Path(cached).read_bytes())
    return weights_path


def _lower_hull(values: np.ndarray, area: int) -> tuple[np.ndarray, np.ndarray]:
    """Return lower-hull anchor points for envelope subtraction."""
    idx: list[int] = []
    hull: list[float] = []
    for i in range(len(values) - area + 1):
        patch = values[i : i + area]
        rel_idx = int(np.argmin(patch))
        abs_idx = rel_idx + i
        if abs_idx not in idx:
            idx.append(abs_idx)
            hull.append(float(patch[rel_idx]))
    if not idx:
        return np.array([0, len(values) - 1]), np.array([values[0], values[-1]])
    if idx[0] != 0:
        idx.insert(0, 0)
        hull.insert(0, float(values[0]))
    if idx[-1] != len(values) - 1:
        idx.append(len(values) - 1)
        hull.append(float(values[-1]))
    return np.array(idx), np.array(hull)


def _curve_profile(
    freqs: np.ndarray,
    spectrum_db: np.ndarray,
    *,
    freq_min: int,
    freq_max: int,
    hull_area: int,
    min_db: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Isolate artifact peaks by subtracting the spectral lower hull."""
    mask = (freq_min <= freqs) & (freqs <= freq_max)
    x_band = freqs[mask]
    y_band = spectrum_db[mask]
    lower_x, lower_y = _lower_hull(y_band, hull_area)
    hull_curve = interpolate.interp1d(
        x_band[lower_x],
        lower_y,
        kind="quadratic",
        fill_value="extrapolate",
    )(x_band)
    hull_curve = np.clip(hull_curve, min_db, None)
    residual = np.clip(y_band - hull_curve, 0.0, None)
    return x_band, residual


def _max_normalise(values: np.ndarray, max_db: float) -> np.ndarray:
    """Scale residual peaks to unit max (matches ISMIR reference code)."""
    clipped = np.clip(values, 0.0, max_db)
    return clipped / (1e-6 + float(np.max(clipped)))


def extract_fakeprint(waveform: np.ndarray, sample_rate: int, cfg: FakeprintConfig) -> np.ndarray:
    """Compute a fakeprint vector from mono/stereo PCM samples."""
    if waveform.ndim == 1:
        channels = waveform[np.newaxis, :]
    else:
        channels = waveform.T if waveform.shape[0] > waveform.shape[1] else waveform
    tensor = torch.from_numpy(channels.astype(np.float32))
    if sample_rate != cfg.sample_rate:
        tensor = torchaudio.functional.resample(tensor, sample_rate, cfg.sample_rate)
        sample_rate = cfg.sample_rate
    max_samples = int(cfg.max_duration_sec * sample_rate)
    tensor = tensor[..., :max_samples]
    spec = torchaudio.transforms.Spectrogram(n_fft=cfg.n_fft, power=2.0)(tensor)
    spec_db = 10.0 * torch.log10(torch.clamp(spec, min=1e-10, max=1e6))
    mean_db = spec_db.mean(dim=(0, 2)).numpy()
    freqs = np.linspace(0.0, sample_rate / 2.0, num=mean_db.shape[0])
    _, residual = _curve_profile(
        freqs,
        mean_db,
        freq_min=cfg.freq_min,
        freq_max=cfg.freq_max,
        hull_area=cfg.hull_area,
        min_db=cfg.min_db,
    )
    return _max_normalise(residual, cfg.max_db).astype(np.float32)


def _load_audio_mono(path: Path) -> tuple[np.ndarray, int]:
    """Load audio file to float32 numpy (channels, samples)."""
    waveform, sample_rate = torchaudio.load(str(path))
    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)
    return waveform.numpy(), int(sample_rate)


def predict_fakeprint_ai(
    audio_path: Path,
    *,
    threshold: float = DEFAULT_THRESHOLD,
) -> AiDetectionResult:
    """Run lofcz/ai-music-detector on one audio file."""
    ensure_detector_model()
    cfg = _load_fakeprint_config()
    from safetensors.numpy import load_file

    weights = load_file(str(MODEL_DIR / "model.safetensors"))
    w = weights["weights"]
    b = weights["bias"]

    waveform, sample_rate = _load_audio_mono(audio_path.resolve())
    duration_sec = waveform.shape[-1] / sample_rate
    fakeprint = extract_fakeprint(waveform, sample_rate, cfg)
    if fakeprint.shape[0] != w.shape[1]:
        raise ValueError(
            f"Fakeprint length {fakeprint.shape[0]} != model input {w.shape[1]}"
        )

    logit = float(np.dot(fakeprint, w.T) + b[0])
    probability = float(1.0 / (1.0 + math.exp(-logit)))
    passed = probability <= threshold
    label = "likely_human" if passed else "likely_ai_generated"
    return AiDetectionResult(
        detector_id="lofcz_fakeprint",
        ai_probability=probability,
        label=label,
        threshold=threshold,
        passed=passed,
        details={
            "model": HF_REPO,
            "duration_sec": round(duration_sec, 2),
            "min_duration_sec": MIN_AUDIO_SEC,
            "paper": "Afchar et al., ISMIR 2025 — A Fourier Explanation of AI-music Artifacts",
        },
    )


def predict_veridex_spectral(
    audio_path: Path,
    *,
    threshold: float = DEFAULT_THRESHOLD,
) -> AiDetectionResult | None:
    """Optional Veridex SpectralSignal detector (``pip install veridex[audio]``)."""
    try:
        from veridex import Veridex
        from veridex.signals.audio import SpectralSignal
    except ImportError:
        return None

    try:
        detector = Veridex(signals=[SpectralSignal()])
        result = detector.analyze(str(audio_path))
        probability = float(
            getattr(result, "ai_probability", getattr(result, "score", 0.5))
        )
    except Exception:
        return None
    passed = probability <= threshold
    return AiDetectionResult(
        detector_id="veridex_spectral",
        ai_probability=probability,
        label="likely_human" if passed else "likely_ai_generated",
        threshold=threshold,
        passed=passed,
        details={"package": "veridex", "signal": "SpectralSignal"},
    )


def run_ai_detectors(
    audio_path: Path,
    *,
    threshold: float = DEFAULT_THRESHOLD,
    include_veridex: bool = True,
) -> list[AiDetectionResult]:
    """Run all available AI music detectors on one file."""
    results = [predict_fakeprint_ai(audio_path, threshold=threshold)]
    if include_veridex:
        veridex = predict_veridex_spectral(audio_path, threshold=threshold)
        if veridex is not None:
            results.append(veridex)
    return results
