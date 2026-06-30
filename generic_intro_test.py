"""Tests for generic Happy Birthday to You lyrics."""

from __future__ import annotations

import unittest

from batch_birthday.lyrics_builder import build_generic_full_song_lyrics


class TestGenericIntroLyrics(unittest.TestCase):
    """Universal lyrics must not contain a personal name placeholder."""

    def test_generic_lyrics_use_to_you_not_dear_name(self) -> None:
        """Verse 1 should be classic to-you lines without 'dear {name}'."""
        lyrics = build_generic_full_song_lyrics()
        self.assertIn("Happy birthday to you", lyrics)
        self.assertNotIn("dear Rahul", lyrics.lower())
        self.assertNotIn("dear Priya", lyrics.lower())
        self.assertNotIn("happy birthday rahul", lyrics.lower())

    def test_generic_body_avoids_personal_name_hooks(self) -> None:
        """Party body should celebrate generically."""
        lyrics = build_generic_full_song_lyrics()
        self.assertIn("Happy birthday to you", lyrics)
        self.assertIn("[Chorus]", lyrics)

    def test_generic_lyrics_are_singable_only(self) -> None:
        """Lyrics must not embed caption/instruction prose that ACE-Step will sing."""
        lyrics = build_generic_full_song_lyrics()
        self.assertTrue(lyrics.startswith("[Verse 1]"))
        self.assertNotIn("[Intro]\n[Instrumental]", lyrics)
        self.assertNotIn("Performance:", lyrics)
        self.assertNotIn("Tempo:", lyrics)
        self.assertNotIn("within the first 6 seconds", lyrics)


if __name__ == "__main__":
    unittest.main()
