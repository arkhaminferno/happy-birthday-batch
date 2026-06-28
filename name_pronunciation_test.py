"""Tests for name pronunciation lookup and instruction text."""

from __future__ import annotations

import unittest

from batch_birthday.name_pronunciation import (
    build_pronunciation_instruction,
    lookup_pronunciation,
    resolve_pronunciation,
    tts_spoken_name,
)


class TestNamePronunciation(unittest.TestCase):
    """Validate pronunciation table and helpers."""

    def test_india_aarav_phonetic(self) -> None:
        """Aarav should use the India-specific guide."""
        pron = lookup_pronunciation("Aarav", "India")
        self.assertIsNotNone(pron)
        assert pron is not None
        self.assertEqual(pron.phonetic, "AA-ruhv")

    def test_russia_alexander_differs_from_us(self) -> None:
        """Alexander pronunciation should differ by country."""
        us = lookup_pronunciation("Alexander", "United States")
        ru = lookup_pronunciation("Alexander", "Russia")
        assert us is not None and ru is not None
        self.assertNotEqual(us.phonetic, ru.phonetic)

    def test_instruction_contains_phonetic(self) -> None:
        """ACE instruction should include the phonetic guide."""
        pron = resolve_pronunciation("Suhani", "India", phonetic="soo-HAH-nee")
        text = build_pronunciation_instruction(pron)
        self.assertIn("soo-HAH-nee", text)

    def test_tts_spoken_name_replaces_hyphens(self) -> None:
        """TTS helper should turn hyphens into spaces."""
        pron = resolve_pronunciation("Aarav", "India")
        self.assertEqual(tts_spoken_name(pron), "AA ruhv")


if __name__ == "__main__":
    unittest.main()
