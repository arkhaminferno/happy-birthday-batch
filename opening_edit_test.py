"""Tests for sung countdown opening edit and drop detection."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from batch_birthday.countdown_reference import countdown_duration_sec
from batch_birthday.opening_edit import (
    DEFAULT_OPENING_TRIM_SEC,
    apply_opening_edit,
    detect_edm_drop_start,
    snap_to_beat,
)


class TestOpeningEdit(unittest.TestCase):
    """Validate drop detection and sung countdown wiring."""

    def test_snap_to_beat_at_128_bpm(self) -> None:
        """14.0s should snap to the nearest 128 BPM downbeat."""
        aligned = snap_to_beat(14.0, 128)
        self.assertAlmostEqual(aligned, 30 * countdown_duration_sec(128, 1), places=4)

    @patch("batch_birthday.opening_edit._decode_mono_segment")
    def test_detect_edm_drop_start_finds_early_onset(self, decode_mock) -> None:
        """Drop detection should pick the earliest loud beat."""
        sample_rate = 22050
        quiet = [100] * sample_rate
        loud = [4000] * sample_rate * 3
        decode_mock.return_value = (quiet + loud, sample_rate)
        drop = detect_edm_drop_start(
            Path("/tmp/body.mp3"),
            bpm=128,
            search_start_sec=0.0,
            search_end_sec=8.0,
            fallback_sec=0.0,
        )
        self.assertLessEqual(drop, 1.5)

    @patch("batch_birthday.opening_edit.trim_and_prepend_countdown")
    @patch("batch_birthday.opening_edit.prepare_sung_countdown_mp3", return_value=1.735)
    @patch("batch_birthday.opening_edit.detect_edm_drop_start", return_value=0.0)
    def test_apply_opening_edit_auto_detects_drop(self, _detect, _prep, trim_mock) -> None:
        """Opening edit should auto-detect the EDM drop before joining countdown."""
        src = Path("/tmp/src.mp3")
        dst = Path("/tmp/dst.mp3")
        countdown = Path("/tmp/countdown.mp3")

        with patch("batch_birthday.audio_merge.probe_duration_sec", return_value=150.0):
            meta = apply_opening_edit(
                src,
                dst,
                countdown_mp3=countdown,
                trim_start_sec=DEFAULT_OPENING_TRIM_SEC,
                bpm=128,
            )

        trim_mock.assert_called_once()
        self.assertEqual(meta["trim_aligned_sec"], 0.0)
        self.assertTrue(meta["auto_detect_drop"])


if __name__ == "__main__":
    unittest.main()
