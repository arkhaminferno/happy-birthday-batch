"""Tests for CelebrateVibes Hindi EDM lyrics template v2."""

import unittest

from batch_birthday.hindi_lyrics_v2 import build_hindi_body_lyrics_v2
from batch_birthday.lyrics_builder import build_full_song_lyrics


class TestHindiLyricsV2(unittest.TestCase):
    """India v2 template uses user-approved Hindi sections."""

    def test_aarav_uses_devanagari_name_in_chorus(self) -> None:
        """Chorus shouts the native name आरव."""
        body = build_hindi_body_lyrics_v2("Aarav", native_name="आरव")
        self.assertIn("आरव!", body)
        self.assertIn("हैप्पी बर्थडे!", body)

    def test_full_song_keeps_english_verse1(self) -> None:
        """India full song still opens with English Happy Birthday."""
        lyrics = build_full_song_lyrics("Aarav", "en", country="India")
        self.assertIn("Happy birthday dear Aarav", lyrics)
        self.assertIn("आज की रात है तेरे नाम", lyrics)
        self.assertIn("[Final Chorus]", lyrics)


if __name__ == "__main__":
    unittest.main()
