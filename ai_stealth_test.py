"""Tests for AI stealth hardening pass."""

import unittest

from batch_birthday.ai_stealth import (
    STEALTH_AI_TARGET,
    build_stealth_filter,
    stealth_pitch_rate_for,
)


class TestAiStealth(unittest.TestCase):
    """Stealth filter stays inside the safe pitch band."""

    def test_pitch_rate_in_safe_band(self) -> None:
        """Per-name pitch rates stay in the detector-safe range."""
        for name in ("Aarav", "Priya", "Liam", "Maria"):
            rate = stealth_pitch_rate_for(name)
            self.assertGreaterEqual(rate, 0.994)
            self.assertLessEqual(rate, 0.9955)

    def test_build_stealth_filter_contains_pitch_shift(self) -> None:
        """Filter applies micro pitch shift and loudness normalization."""
        filt = build_stealth_filter(pitch_rate=0.995)
        self.assertIn("asetrate=48000*0.995", filt)
        self.assertIn("atempo=", filt)
        self.assertIn("loudnorm=", filt)

    def test_target_is_one_percent(self) -> None:
        """Upload hardening targets <= 1% local AI probability."""
        self.assertEqual(STEALTH_AI_TARGET, 0.01)


if __name__ == "__main__":
    unittest.main()
