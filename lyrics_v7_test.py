"""Tests for EDM v7 commercial birthday template."""

import unittest

from batch_birthday.lyrics_builder import (
    BIRTHDAY_EDM_PARTY_V7_INSTRUCTION,
    INTRO_COUNTDOWN_EN,
    build_lyrics,
    genre_caption,
)


class TestEdmV7Lyrics(unittest.TestCase):
    """v7 ACT 1/2/3 structure — no countdown, no ad-libs."""

    def test_no_countdown_intro(self) -> None:
        """v7 opens with HB sing-along — no English countdown."""
        lyrics = build_lyrics("Suhani", "hi", genre_variant="birthday_edm_party_v7")
        self.assertNotIn(INTRO_COUNTDOWN_EN, lyrics)
        self.assertNotIn("[Intro - English Countdown]", lyrics)
        self.assertIn("[ACT 1 - Birthday Sing-Along]", lyrics)

    def test_opening_single_hb_refrain(self) -> None:
        """Opening sings classic HB exactly once."""
        lyrics = build_lyrics("Suhani", "hi", genre_variant="birthday_edm_party_v7")
        self.assertEqual(lyrics.count("Happy birthday dear Suhani"), 1)

    def test_no_adlibs_on_build(self) -> None:
        """Build riser is instrumental only."""
        lyrics = build_lyrics("Suhani", "hi", genre_variant="birthday_edm_party_v7")
        self.assertIn("[Build - Drum Riser]", lyrics)
        self.assertNotIn("Here we go", lyrics)
        self.assertIn("No ad-libs", lyrics)

    def test_act2_festival_drop(self) -> None:
        """Template includes ACT 2 festival drop."""
        lyrics = build_lyrics("Suhani", "hi", genre_variant="birthday_edm_party_v7")
        self.assertIn("[ACT 2 - Festival Drop]", lyrics)
        self.assertIn("supersaws", lyrics)

    def test_act3_hindi_body(self) -> None:
        """ACT 3 uses supplied Hindi verses and chorus."""
        lyrics = build_lyrics("Suhani", "hi", genre_variant="birthday_edm_party_v7")
        self.assertIn("[ACT 3 - Verse 2 - Original Birthday Song]", lyrics)
        self.assertIn("तुम्हारे सपने सच हों", lyrics)
        self.assertIn("[Ending - Emotional Final Chorus]", lyrics)

    def test_v7_instruction_loaded(self) -> None:
        """V7 instruction matches commercial ACT structure."""
        self.assertIn("ACT 1", BIRTHDAY_EDM_PARTY_V7_INSTRUCTION)
        self.assertIn("Tomorrowland", BIRTHDAY_EDM_PARTY_V7_INSTRUCTION)
        self.assertIn("No ad-libs", BIRTHDAY_EDM_PARTY_V7_INSTRUCTION)

    def test_caption_hi(self) -> None:
        """Hindi caption describes v7 commercial flow."""
        cap = genre_caption("birthday_edm_party_v7", "hi")
        self.assertIn("exactly one verse", cap)
        self.assertIn("Hindi", cap)


if __name__ == "__main__":
    unittest.main()
