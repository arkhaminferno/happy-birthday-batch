"""Tests for deterministic AE video variation."""

from __future__ import annotations

import unittest

from batch_birthday.ae_video_variation import video_variation_for


class TestVideoVariation(unittest.TestCase):
    """Stable per-slug cohesive party themes."""

    def test_same_slug_is_stable(self) -> None:
        """Variation must not drift between calls."""
        first = video_variation_for("aarav-in-birthday-edm-party")
        second = video_variation_for("aarav-in-birthday-edm-party")
        self.assertEqual(first, second)

    def test_different_slugs_can_differ(self) -> None:
        """Distinct slugs should usually get distinct themes."""
        aarav = video_variation_for("aarav-in-birthday-edm-party")
        arjun = video_variation_for("arjun-in-birthday-edm-party")
        self.assertNotEqual(aarav.theme_name, arjun.theme_name)

    def test_theme_is_cohesive_across_elements(self) -> None:
        """All visual layers share one party hue like the default gold template."""
        variation = video_variation_for("pooja-in-birthday-edm-party")
        hues = (
            variation.cake_hue,
            variation.candle_hue,
            variation.firework_hue,
            variation.gradient_hue,
            variation.confetti_hue,
            variation.background_hue,
        )
        self.assertEqual(len(set(hues)), 1)
        self.assertEqual(hues[0], variation.theme_hue)
        self.assertGreaterEqual(variation.firework_speed, 0.94)
        self.assertLessEqual(variation.confetti_speed, 1.06)


if __name__ == "__main__":
    unittest.main()
