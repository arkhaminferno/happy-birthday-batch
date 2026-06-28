"""Tests for CelebrateVibes v2 pipeline modules (no ACE-Step API)."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
from scipy.io import wavfile

from batch_birthday.audio_qc import AudioQCError, validate_audio
from batch_birthday.cover_generator import build_verse1_cover_payload
from batch_birthday.lyrics_builder import build_verse1_lyrics
from batch_birthday.melody_generator import ensure_melody_wav, phrase_duration_sec
from batch_birthday.pipeline_paths import BATCH_ROOT, PipelinePaths, resolve_raw_mp3
from batch_birthday.song_generator import build_body_payload
from batch_birthday.verse1_stem import create_verse1_stem


class TestCelebrateVibesV2Pipeline(unittest.TestCase):
    """Path layout, melody asset, and ACE-Step payload shapes."""

    def test_pipeline_paths_layout(self) -> None:
        """Each slug gets stage subdirectories under output."""
        with tempfile.TemporaryDirectory() as tmp:
            paths = PipelinePaths.for_slug(Path(tmp), "suhani-birthday")
            self.assertEqual(paths.verse1_stem_wav.parent.name, "vocals")
            self.assertEqual(paths.cover_mp3.parent.name, "cover")
            self.assertEqual(paths.body_mp3.parent.name, "song")
            self.assertEqual(paths.raw_mp3.parent.name, "master")

    def test_resolve_raw_mp3_prefers_master(self) -> None:
        """resolve_raw_mp3 finds v2 master/ layout."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            slug = "test-song"
            master = root / "master"
            master.mkdir(parents=True)
            raw = master / f"{slug}_raw.mp3"
            raw.write_bytes(b"x")
            self.assertEqual(resolve_raw_mp3(root, slug), raw)

    def test_fixed_melody_wav_created(self) -> None:
        """ensure_melody_wav writes a single-phrase WAV."""
        with tempfile.TemporaryDirectory() as tmp:
            wav = ensure_melody_wav(output=Path(tmp) / "hb.wav", bpm=128)
            self.assertTrue(wav.exists())
            self.assertGreater(phrase_duration_sec(bpm=128), 10.0)

    def test_create_verse1_stem(self) -> None:
        """Local Verse 1 stem is created before ACE cover mode."""
        row = SimpleNamespace(name="Suhani", bpm=128)
        with tempfile.TemporaryDirectory(dir=BATCH_ROOT / "output") as tmp:
            paths = PipelinePaths.for_slug(Path(tmp), "demo")
            meta = create_verse1_stem(row, paths=paths)
            self.assertTrue(paths.verse1_stem_wav.exists())
            self.assertIn("Happy birthday dear Suhani", meta["lyrics"])
            self.assertGreater(meta["duration_sec"], 10.0)

    def test_verse1_cover_payload(self) -> None:
        """Verse 1 is one cover pass on the deterministic source stem."""
        row = MagicMock(bpm=128)
        with tempfile.TemporaryDirectory(dir=BATCH_ROOT / "output") as tmp:
            root = Path(tmp)
            paths = PipelinePaths.for_slug(root, "demo")
            wav = paths.verse1_stem_wav
            ensure_melody_wav(output=wav, bpm=128)
            payload = build_verse1_cover_payload(
                row,
                src_wav=wav,
                paths=paths,
                lyrics="Happy birthday dear Demo",
                duration_sec=16.0,
                seed=123,
            )
            self.assertEqual(payload["task_type"], "cover")
            self.assertEqual(payload["time_signature"], "3")
            self.assertGreaterEqual(payload["audio_cover_strength"], 0.85)

    def test_body_payload_is_text2music(self) -> None:
        """Body generation uses text2music with party instruction."""
        row = MagicMock(bpm=128, language="hi")
        payload = build_body_payload(
            row,
            lyrics="[Verse 2]",
            duration_sec=130,
            seed=456,
        )
        self.assertEqual(payload["task_type"], "text2music")
        self.assertTrue(payload["thinking"])
        self.assertGreaterEqual(payload["guidance_scale"], 9.0)

    def test_verse1_lyrics_have_no_countdown(self) -> None:
        """Main pipeline keeps Verse 1 lyrics to the four HB lines only."""
        lyrics = build_verse1_lyrics("Suhani")
        self.assertNotIn("3!", lyrics)
        self.assertIn("Happy birthday dear Suhani", lyrics)

    def test_qc_rejects_silence(self) -> None:
        """QC fails silent generated files before merge."""
        with tempfile.TemporaryDirectory() as tmp:
            silent = Path(tmp) / "silent.wav"
            wavfile.write(str(silent), 48000, np.zeros(48000, dtype=np.int16))
            with self.assertRaises(AudioQCError):
                validate_audio(
                    silent,
                    label="silent",
                    min_duration_sec=0.5,
                    max_duration_sec=2.0,
                    min_rms_db=-40.0,
                )


if __name__ == "__main__":
    unittest.main()
