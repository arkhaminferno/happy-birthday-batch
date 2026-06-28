"""Tests for CelebrateVibes v2 lyrics split."""

import unittest

from batch_birthday.lyrics_builder import (
    build_body_lyrics,
    build_full_song_lyrics,
    build_lyrics,
    build_verse1_lyrics,
)


class TestCelebrateVibesV2Lyrics(unittest.TestCase):
    """Verse 1 and body lyrics are split correctly."""

    def test_verse1_only_name_changes(self) -> None:
        """Verse 1 is English HB with personalized name — no performance prose."""
        lyrics = build_verse1_lyrics("Suhani")
        self.assertIn("Happy birthday dear Suhani", lyrics)
        self.assertEqual(lyrics.count("Happy birthday to you"), 3)
        self.assertNotIn("Performance", lyrics)
        self.assertNotIn("Do NOT", lyrics)

    def test_body_has_no_hb_melody(self) -> None:
        """Body has singable sections only — no directive prose."""
        body = build_body_lyrics("Suhani", "hi")
        self.assertIn("[Verse 2]", body)
        self.assertIn("[Chorus]", body)
        self.assertNotIn("Happy birthday to you", body)
        self.assertNotIn("Instrumental only", body)
        self.assertNotIn("Do NOT", body)

    def test_body_weaves_name_throughout(self) -> None:
        """Party body repeats the name with birthday imagery."""
        body = build_body_lyrics("Suhani", "hi")
        self.assertGreaterEqual(body.count("Suhani"), 5)
        self.assertIn("Happy birthday Suhani", body)
        self.assertIn("candles", body.lower())

    def test_combined_genre_lyrics(self) -> None:
        """build_lyrics for celebratevibes_v2 returns intro + HB + party body."""
        full = build_lyrics("Rahul", "en", genre_variant="celebratevibes_v2")
        self.assertIn("[Intro", full)
        self.assertIn("Happy birthday dear Rahul", full)
        self.assertIn("[Verse 2]", full)
        self.assertNotIn("3!", full)
        self.assertNotIn("Performance", full)

    def test_full_song_has_no_countdown(self) -> None:
        """Single-pass lyrics must not include spoken countdown or sung intro prompts."""
        full = build_full_song_lyrics("Aarav")
        self.assertIn("[Instrumental]", full)
        self.assertNotIn("Bright synth", full)
        self.assertNotIn("No vocals", full)
        self.assertNotIn("3!", full)
        self.assertNotIn("Go!", full)


if __name__ == "__main__":
    unittest.main()
