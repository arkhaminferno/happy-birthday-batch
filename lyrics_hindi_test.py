"""Tests for Hindi EDM v6 performance-score lyrics."""

import unittest

from batch_birthday.lyrics_builder import (
    INTRO_COUNTDOWN_EN,
    MELODY_CONDITIONED_NOTE,
    build_lyrics,
    genre_caption,
)


class TestHindiEdmLyrics(unittest.TestCase):
    """Hindi language path for v6 performance-score template."""

    def test_intro_always_english(self) -> None:
        """Intro countdown must stay English for all languages."""
        lyrics = build_lyrics("Suhani", "hi", genre_variant="birthday_edm_party_v6_restore")
        self.assertIn(INTRO_COUNTDOWN_EN, lyrics)
        self.assertIn("[Intro - English Countdown]", lyrics)

    def test_opening_single_hb_refrain(self) -> None:
        """Opening sings classic HB exactly once — not tripled."""
        lyrics = build_lyrics("Suhani", "hi", genre_variant="birthday_edm_party_v6_restore")
        self.assertEqual(lyrics.count("Happy birthday dear Suhani"), 1)

    def test_opening_performance_constraints(self) -> None:
        """Opening must include explicit do-not-improvise constraints."""
        lyrics = build_lyrics("Suhani", "hi", genre_variant="birthday_edm_party_v6_restore")
        self.assertIn("[Opening - Traditional Happy Birthday Melody]", lyrics)
        self.assertIn("Do NOT invent a new melody", lyrics)
        self.assertIn("No melisma", lyrics)

    def test_build_drop_transition(self) -> None:
        """Template includes build after opening and festival drop."""
        lyrics = build_lyrics("Suhani", "hi", genre_variant="birthday_edm_party_v6_restore")
        self.assertIn("[Build - Transition After Opening]", lyrics)
        self.assertIn("[Drop - Massive Festival EDM Drop]", lyrics)

    def test_verse2_original_composition_tag(self) -> None:
        """Verse 2 onward tagged as original — not traditional tune."""
        lyrics = build_lyrics("Suhani", "hi", genre_variant="birthday_edm_party_v6_restore")
        self.assertIn("[Verse 2 - Original Festival Composition]", lyrics)
        self.assertIn("Do NOT use Happy Birthday to You tune", lyrics)
        self.assertIn("तुम्हारे सपने सच हों", lyrics)

    def test_caption_no_improvise_opening(self) -> None:
        """Caption must forbid improvising the opening melody."""
        cap = genre_caption("birthday_edm_party_v6_restore", "hi")
        self.assertIn("exactly once", cap)
        self.assertIn("Do NOT", cap)

    def test_melody_conditioned_note_documented(self) -> None:
        """Module documents text-only HB limitation."""
        self.assertIn("reference-audio", MELODY_CONDITIONED_NOTE)


if __name__ == "__main__":
    unittest.main()
