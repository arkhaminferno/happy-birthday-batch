"""Single ACE-Step cover pass — EDM under traditional 3/4 Happy Birthday Verse 1."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from batch_birthday.acestep_task import generate_to_file
from batch_birthday.lyrics_builder import (
    CELEBRATEVIBES_V2_VERSE1_COVER_CAPTION,
    CELEBRATEVIBES_V2_VERSE1_COVER_INSTRUCTION,
)
from batch_birthday.melody_generator import DEFAULT_BPM
from batch_birthday.name_pronunciation import (
    build_pronunciation_instruction,
    resolve_pronunciation,
)
from batch_birthday.pipeline_paths import PipelinePaths

# High strength — lock the real HB melody; one pass only (no vocal pre-pass).
VERSE1_COVER_STRENGTH = 0.86
VERSE1_DURATION_PAD_SEC = 1.0


def _verse1_instruction(row: Any) -> str:
    """Cover instruction with per-name pronunciation."""
    country = getattr(row, "country", "") or ""
    phonetic = getattr(row, "pronunciation", "") or ""
    pron = resolve_pronunciation(row.name, country, phonetic)
    return f"{CELEBRATEVIBES_V2_VERSE1_COVER_INSTRUCTION} {build_pronunciation_instruction(pron)}"


def build_verse1_cover_payload(
    row: Any,
    *,
    src_wav: Path,
    paths: PipelinePaths,
    lyrics: str,
    duration_sec: float,
    seed: int | None = None,
) -> dict[str, Any]:
    """Build cover payload: BPM-aligned HB recording → EDM-backed singalong."""
    payload: dict[str, Any] = {
        "prompt": CELEBRATEVIBES_V2_VERSE1_COVER_CAPTION,
        "lyrics": lyrics,
        "instruction": _verse1_instruction(row),
        "thinking": False,
        "use_format": False,
        "use_cot_caption": False,
        "use_cot_language": False,
        "vocal_language": "en",
        "audio_duration": max(12, int(round(duration_sec + VERSE1_DURATION_PAD_SEC))),
        "bpm": row.bpm or DEFAULT_BPM,
        "key_scale": "C Major",
        "time_signature": "3",
        "inference_steps": 10,
        "batch_size": 1,
        "use_random_seed": seed is None,
        "audio_format": "mp3",
        "model": "acestep-v15-turbo",
        "task_type": "cover",
        "src_audio_path": paths.repo_relative(src_wav),
        "audio_cover_strength": VERSE1_COVER_STRENGTH,
    }
    if seed is not None:
        payload["seed"] = seed
    return payload


def generate_verse1_cover(
    row: Any,
    *,
    src_wav: Path,
    paths: PipelinePaths,
    lyrics: str,
    duration_sec: float,
    api_base: str,
    api_key: str,
    seed: int | None = None,
) -> dict[str, Any]:
    """One cover pass from the prepared HB recording — swap name, keep melody."""
    payload = build_verse1_cover_payload(
        row,
        src_wav=src_wav,
        paths=paths,
        lyrics=lyrics,
        duration_sec=duration_sec,
        seed=seed,
    )
    return generate_to_file(
        payload,
        api_base=api_base,
        api_key=api_key,
        out_path=paths.cover_mp3,
        label="verse1-cover",
    )
