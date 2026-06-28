"""Generate the festival EDM countdown intro (separate from Verse 1)."""

from __future__ import annotations

from typing import Any

from batch_birthday.acestep_task import generate_to_file
from batch_birthday.lyrics_builder import (
    CELEBRATEVIBES_V2_INTRO_CAPTION,
    CELEBRATEVIBES_V2_INTRO_INSTRUCTION,
    build_intro_lyrics,
)
from batch_birthday.melody_generator import DEFAULT_BPM
from batch_birthday.pipeline_paths import PipelinePaths

INTRO_DURATION_SEC = 10
INTRO_GUIDANCE = 9.0
INTRO_STEPS = 12


def build_intro_payload(
    row: Any,
    *,
    duration_sec: int = INTRO_DURATION_SEC,
    seed: int | None = None,
) -> dict[str, Any]:
    """Build text2music payload for the 3-2-1-Go countdown over EDM kick."""
    payload: dict[str, Any] = {
        "prompt": CELEBRATEVIBES_V2_INTRO_CAPTION,
        "lyrics": build_intro_lyrics(),
        "instruction": CELEBRATEVIBES_V2_INTRO_INSTRUCTION,
        "thinking": True,
        "use_format": False,
        "use_cot_caption": False,
        "use_cot_language": False,
        "vocal_language": "en",
        "audio_duration": duration_sec,
        "bpm": row.bpm or DEFAULT_BPM,
        "key_scale": "C Major",
        "time_signature": "4",
        "inference_steps": INTRO_STEPS,
        "guidance_scale": INTRO_GUIDANCE,
        "batch_size": 1,
        "use_random_seed": seed is None,
        "audio_format": "mp3",
        "model": "acestep-v15-turbo",
        "task_type": "text2music",
    }
    if seed is not None:
        payload["seed"] = seed
    return payload


def generate_intro(
    row: Any,
    *,
    paths: PipelinePaths,
    api_base: str,
    api_key: str,
    seed: int | None = None,
) -> dict[str, Any]:
    """Generate a standalone EDM countdown intro clip."""
    payload = build_intro_payload(row, seed=seed)
    return generate_to_file(
        payload,
        api_base=api_base,
        api_key=api_key,
        out_path=paths.intro_mp3,
        label="intro-countdown",
    )
