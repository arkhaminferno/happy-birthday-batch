"""Tests for native-language party lyrics routing."""

import unittest
from unittest.mock import MagicMock

from batch_birthday.lyrics_builder import build_full_song_lyrics
from batch_birthday.native_party_lyrics import build_native_body_lyrics
from batch_birthday.song_generator import build_full_song_payload


class TestNativePartyLyrics(unittest.TestCase):
    """Each country uses native language in the party body."""

    def test_russia_uses_cyrillic_body(self) -> None:
        """Russia body is Cyrillic after English Verse 1."""
        lyrics = build_full_song_lyrics("Ivan", "ru", country="Russia", variant=0)
        self.assertIn("Happy birthday dear Ivan", lyrics)
        self.assertIn("Сегодня ночь", lyrics)
        self.assertIn("Иван!", lyrics)

    def test_china_uses_mandarin_body(self) -> None:
        """China body is Mandarin after English Verse 1."""
        lyrics = build_full_song_lyrics("Wei", "zh", country="China", variant=1)
        self.assertIn("Happy birthday dear Wei", lyrics)
        self.assertIn("今晚", lyrics)
        self.assertIn("伟!", lyrics)

    def test_variants_change_russian_chorus(self) -> None:
        """Different variants produce different Russian hooks."""
        a = build_native_body_lyrics("Anna", "Russia", variant=0, native_name="Анна")
        b = build_native_body_lyrics("Anna", "Russia", variant=1, native_name="Анна")
        self.assertNotEqual(a, b)

    def test_russia_payload_uses_ru_vocal_language(self) -> None:
        """Russia rows request Russian vocal language."""
        row = MagicMock(name="Ivan", country="Russia", bpm=129, pronunciation="ee-VAHN")
        payload = build_full_song_payload(row, lyrics="[Verse 1]", duration_sec=165, seed=1)
        self.assertEqual(payload["vocal_language"], "ru")
        self.assertIn("Russian", payload["prompt"])

    def test_china_payload_uses_zh_vocal_language(self) -> None:
        """China rows request Chinese vocal language."""
        row = MagicMock(name="Li", country="China", bpm=128, pronunciation="LEE")
        payload = build_full_song_payload(row, lyrics="[Verse 1]", duration_sec=165, seed=1)
        self.assertEqual(payload["vocal_language"], "zh")
        self.assertIn("Chinese", payload["prompt"])


if __name__ == "__main__":
    unittest.main()
