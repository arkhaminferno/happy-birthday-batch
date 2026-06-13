"""Tests for per-name outro lyric variation."""

import unittest

from batch_birthday.lyrics_builder import build_lyrics


class TestLyricsOutroVariation(unittest.TestCase):
    """Different names should get different outro blocks."""

    def test_outro_differs_by_name(self) -> None:
        """Outro section should vary deterministically per name."""
        a = build_lyrics("Priya", genre_variant="birthday_edm_party_v6_restore")
        b = build_lyrics("Arjun", genre_variant="birthday_edm_party_v6_restore")
        self.assertIn("[Outro]", a)
        self.assertIn("[Outro]", b)
        self.assertNotEqual(a.split("[Outro]")[1], b.split("[Outro]")[1])

    def test_outro_stable_for_same_name(self) -> None:
        """Same name should always produce the same outro."""
        first = build_lyrics("Neha", genre_variant="birthday_edm_party_v6_restore")
        second = build_lyrics("Neha", genre_variant="birthday_edm_party_v6_restore")
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
