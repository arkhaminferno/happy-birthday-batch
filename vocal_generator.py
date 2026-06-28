"""Generate Verse 1 vocals from the fixed Happy Birthday melody."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from batch_birthday.acestep_task import generate_to_file
from batch_birthday.lyrics_builder import (
    CELEBRATEVIBES_V2_VOCAL_CAPTION,
    CELEBRATEVIBES_V2_VOCAL_INSTRUCTION,
    build_verse1_lyrics,
)
from batch_birthday.melody_generator import DEFAULT_BPM
from batch_birthday.pipeline_paths import PipelinePaths

# High strength — lock the real Happy Birthday melody while swapping the name.
VOCAL_COVER_STRENGTH = 0.82
VOCAL_DURATION_PAD_SEC = 1.0


def build_vocal_payload(
    row: Any,
    *,
    melody_wav: Path,
    paths: PipelinePaths,
    lyrics: str,
    duration_sec: float,
    seed: int | None = None,
) -> dict[str, Any]:
    """Build ACE-Step cover payload to sing Verse 1 on the fixed melody."""
    payload: dict[str, Any] = {
        "prompt": CELEBRATEVIBES_V2_VOCAL_CAPTION,
        "lyrics": lyrics,
        "instruction": CELEBRATEVIBES_V2_VOCAL_INSTRUCTION,
        "thinking": False,
        "use_format": False,
        "use_cot_caption": False,
        "use_cot_language": False,
        "vocal_language": "en",
        "audio_duration": max(12, int(round(duration_sec + VOCAL_DURATION_PAD_SEC))),
        "bpm": row.bpm or DEFAULT_BPM,
        "key_scale": "C Major",
        "time_signature": "4",
        "inference_steps": 10,
        "batch_size": 1,
        "use_random_seed": seed is None,
        "audio_format": "mp3",
        "model": "acestep-v15-turbo",
        "task_type": "cover",
        "src_audio_path": paths.repo_relative(melody_wav),
        "audio_cover_strength": VOCAL_COVER_STRENGTH,
    }
    if seed is not None:
        payload["seed"] = seed
    return payload


def generate_verse1_vocal(
    row: Any,
    *,
    melody_wav: Path,
    paths: PipelinePaths,
    duration_sec: float,
    api_base: str,
    api_key: str,
    seed: int | None = None,
) -> dict[str, Any]:
    """Cover the real Happy Birthday recording to sing Verse 1 with the new name."""
    lyrics = build_verse1_lyrics(row.name)
    paths.verse1_lyrics.write_text(lyrics + "\n", encoding="utf-8")
    payload = build_vocal_payload(
        row,
        melody_wav=melody_wav,
        paths=paths,
        lyrics=lyrics,
        duration_sec=duration_sec,
        seed=seed,
    )
    return generate_to_file(
        payload,
        api_base=api_base,
        api_key=api_key,
        out_path=paths.vocal_mp3,
        label="verse1-vocal",
    )
