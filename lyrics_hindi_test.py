"""Tests for Hindi EDM v6 lyrics."""

import unittest

from batch_birthday.lyrics_builder import build_lyrics, genre_caption


class TestHindiEdmLyrics(unittest.TestCase):
    """Hindi language path for v6 template."""

    def test_hindi_lyrics_contain_devanagari(self) -> None:
        """Suhani Hindi lyrics should use Devanagari script."""
        lyrics = build_lyrics("Suhani", "hi", genre_variant="birthday_edm_party_v6_restore")
        self.assertIn("जन्मदिन", lyrics)
        self.assertIn("Suhani", lyrics)

    def test_hindi_caption(self) -> None:
        """Hindi should select Hindi vocal caption."""
        cap = genre_caption("birthday_edm_party_v6_restore", "hi")
        self.assertIn("Hindi", cap)


if __name__ == "__main__":
    unittest.main()
