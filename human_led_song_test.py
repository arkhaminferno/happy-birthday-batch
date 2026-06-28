"""Tests for human-led production bed + vocal cover flow."""

import unittest
from unittest.mock import MagicMock

from batch_birthday.human_led_song import (
    build_instrumental_bed_lyrics,
    build_production_bed_payload,
    build_vocal_cover_payload,
)
from batch_birthday.pipeline_paths import BATCH_ROOT, PipelinePaths


class TestHumanLedSong(unittest.TestCase):
    """Human-led stages use instrumental bed then cover with exact lyrics."""

    def test_bed_payload_is_instrumental_text2music(self) -> None:
        """Stage 1 is instrumental-only text2music."""
        row = MagicMock(bpm=129)
        bed_lyrics = build_instrumental_bed_lyrics(
            "[Intro]\nx\n\n[Verse 1]\nHappy birthday\n\n[Chorus]\nHey"
        )
        payload = build_production_bed_payload(row, instrumental_lyrics=bed_lyrics, seed=1)
        self.assertEqual(payload["task_type"], "text2music")
        self.assertIn("[Instrumental]", payload["lyrics"])
        self.assertNotIn("Happy birthday", payload["lyrics"])
        self.assertIn("NO vocals", payload["instruction"])
        self.assertEqual(payload["seed"], 1)

    def test_instrumental_bed_mirrors_sections(self) -> None:
        """Bed lyrics keep section tags but strip vocal lines."""
        bed = build_instrumental_bed_lyrics(
            "[Verse 1]\nLine one\nLine two\n\n[Chorus]\nHook"
        )
        self.assertIn("[Verse 1]\n[Instrumental]", bed)
        self.assertIn("[Chorus]\n[Instrumental]", bed)

    def test_cover_payload_locks_lyrics(self) -> None:
        """Stage 2 cover uses bed source and forbids lyric improvisation."""
        row = MagicMock(
            bpm=129,
            country="India",
            pronunciation="AA-ruhv",
            name="Aarav",
        )
        paths = PipelinePaths.for_slug(BATCH_ROOT / "output", "human-led-test")
        bed = paths.root / "song" / "human-led-test_bed.mp3"
        bed.parent.mkdir(parents=True, exist_ok=True)
        bed.write_bytes(b"x")
        payload = build_vocal_cover_payload(
            row,
            bed_mp3=bed,
            paths=paths,
            lyrics="[Verse 1]\nHappy birthday",
            seed=2,
        )
        bed.unlink(missing_ok=True)
        self.assertEqual(payload["task_type"], "cover")
        self.assertIn("Do NOT invent", payload["instruction"])
        self.assertEqual(payload["audio_cover_strength"], 0.50)
        self.assertIn("human-led-test_bed.mp3", payload["src_audio_path"])


if __name__ == "__main__":
    unittest.main()
