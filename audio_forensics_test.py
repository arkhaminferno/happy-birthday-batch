"""Tests for audio_forensics metrics."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from scipy.io import wavfile

from batch_birthday.audio_forensics import (
    measure_spectral_flatness,
    measure_stereo_correlation,
)


class TestForensicMetrics(unittest.TestCase):
    """Spectral and stereo forensic helpers."""

    def test_stereo_correlation_perfect_for_identical_channels(self) -> None:
        """Identical L/R should correlate near 1.0."""
        samples = np.sin(np.linspace(0, 20, 8000))
        stereo = np.stack([samples, samples])
        corr = measure_stereo_correlation(stereo)
        self.assertGreater(corr, 0.99)

    def test_spectral_flatness_on_noise(self) -> None:
        """White noise should have relatively high flatness."""
        rng = np.random.default_rng(0)
        mono = rng.normal(0, 0.1, size=(1, 16000)).astype(np.float32)
        flatness = measure_spectral_flatness(mono, 16000)
        self.assertGreater(flatness, 0.1)


if __name__ == "__main__":
    unittest.main()
