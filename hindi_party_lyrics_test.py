"""Tests for India Hindi party lyrics."""

import unittest
from unittest.mock import MagicMock

from batch_birthday.hindi_lyrics_v2 import build_hindi_body_lyrics_v2
from batch_birthday.lyrics_builder import build_full_song_lyrics
from batch_birthday.song_generator import build_full_song_payload


class TestIndiaHindiPartyLyrics(unittest.TestCase):
    """India songs keep English HB and switch to v2 Hindi body."""

    def test_verse1_stays_english_for_india(self) -> None:
        """Happy Birthday verse remains English for India."""
        lyrics = build_full_song_lyrics("Aarav", "en", country="India")
        self.assertIn("Happy birthday dear Aarav", lyrics)
        self.assertIn("[Verse 1]", lyrics)

    def test_body_uses_v2_hindi_template(self) -> None:
        """Verse 2 onward uses the approved v2 Hindi template."""
        lyrics = build_full_song_lyrics("Aarav", "en", country="India")
        self.assertIn("आज की रात है तेरे नाम", lyrics)
        self.assertIn("आरव!", lyrics)
        self.assertIn("[Final Chorus]", lyrics)
        self.assertNotIn("Everybody jump", lyrics)

    def test_hindi_body_has_final_chorus(self) -> None:
        """v2 template ends with Final Chorus, not Outro."""
        body = build_hindi_body_lyrics_v2("Aarav", native_name="आरव")
        self.assertIn("[Final Chorus]", body)
        self.assertNotIn("[Outro]", body)

    def test_us_still_english_body(self) -> None:
        """Non-India countries keep the English party body."""
        lyrics = build_full_song_lyrics("Liam", "en", country="United States")
        self.assertIn("Everybody jump", lyrics)
        self.assertNotIn("आज की रात", lyrics)

    def test_india_payload_keeps_english_vocal_language(self) -> None:
        """India uses same vocal_language as the approved English mix."""
        row = MagicMock(name="Aarav", country="India", bpm=129, pronunciation="AA-ruhv")
        payload = build_full_song_payload(row, lyrics="[Verse 1]", duration_sec=165, seed=1)
        self.assertEqual(payload["vocal_language"], "en")
        self.assertIn("Hindi", payload["prompt"])


if __name__ == "__main__":
    unittest.main()
