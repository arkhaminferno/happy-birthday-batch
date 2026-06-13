"""Tests for humanize_audio clap bed generation."""

import tempfile
import unittest
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from batch_birthday.humanize_audio import SAMPLE_RATE, _write_clap_bed_wav


class TestClapBed(unittest.TestCase):
    """Clap bed WAV synthesis."""

    def test_clap_wav_matches_duration(self) -> None:
        """Clap bed should span the requested duration."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "claps.wav"
            duration = 2.5
            _write_clap_bed_wav(out, duration, bpm=120)
            sr, data = wavfile.read(out)
            self.assertEqual(sr, SAMPLE_RATE)
            expected = int(duration * SAMPLE_RATE)
            self.assertTrue(abs(len(data) - expected) <= sr)
            self.assertGreater(float(np.max(np.abs(data))), 0)


if __name__ == "__main__":
    unittest.main()
