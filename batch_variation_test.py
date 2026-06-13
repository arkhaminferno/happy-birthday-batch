"""Tests for per-name batch variation helpers."""

import unittest

from batch_birthday.batch_variation import (
    build_distribute_filter,
    derive_seed,
    master_variation_for,
    slug_for_name,
)


class TestBatchVariation(unittest.TestCase):
    """Deterministic seed and mastering variation."""

    def test_derive_seed_differs_by_name(self) -> None:
        """Different names should get different seeds."""
        self.assertNotEqual(derive_seed("Priya"), derive_seed("Arjun"))

    def test_derive_seed_stable(self) -> None:
        """Same name should always map to the same seed."""
        self.assertEqual(derive_seed("Priya"), derive_seed("Priya"))

    def test_slug_from_name(self) -> None:
        """Slug should be filesystem-safe."""
        self.assertEqual(slug_for_name("Priya"), "priya-birthday-edm-party")

    def test_variation_filter_contains_pitch(self) -> None:
        """Filter chain should include asetrate for fingerprint shift."""
        var = master_variation_for("Neha")
        filt = build_distribute_filter(var)
        self.assertIn("asetrate", filt)
        self.assertIn("extrastereo", filt)


if __name__ == "__main__":
    unittest.main()
