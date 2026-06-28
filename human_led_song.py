"""Human-led ACE-Step flow: production bed first, then vocal cover.

Mirrors the hit-songwriter Suno workflow — AI assists production and vocal
rendering; humans supply exact lyrics and melody structure.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from batch_birthday.acestep_task import generate_to_file
from batch_birthday.hindi_party_lyrics import (
    CELEBRATEVIBES_V2_INDIA_CAPTION_SUFFIX,
    CELEBRATEVIBES_V2_INDIA_INSTRUCTION_SUFFIX,
)
from batch_birthday.lyrics_builder import (
    CELEBRATEVIBES_V2_FULL_CAPTION,
    CELEBRATEVIBES_V2_FULL_INSTRUCTION,
)
from batch_birthday.melody_generator import DEFAULT_BPM
from batch_birthday.name_pronunciation import (
    build_pronunciation_instruction,
    resolve_pronunciation,
)
from batch_birthday.pipeline_paths import PipelinePaths

FULL_SONG_DURATION_SEC = 165
PRODUCTION_BED_DURATION_SEC = FULL_SONG_DURATION_SEC
# Moderate cover strength — lock groove/chords, allow human lyrics and vocal melody.
VOCAL_COVER_STRENGTH = 0.50
BED_INFERENCE_STEPS = 10
COVER_INFERENCE_STEPS = 14

PRODUCTION_BED_CAPTION = (
    "128 BPM festival EDM instrumental bed, four-on-the-floor kick drum from bar one, "
    "bright supersaw synth hook, punchy sidechain bass, hand claps, commercial dance-pop "
    "production, glittery synth, party energy, strictly instrumental"
)

PRODUCTION_BED_INSTRUCTION = (
    "Instrumental production bed only. Beat and chords start immediately at second zero. "
    "NO vocals. NO humming. NO spoken words. NO lyrics. Clean festival EDM groove."
)


def _is_india(row: Any) -> bool:
    """Return True for India country rows."""
    return (getattr(row, "country", "") or "").strip().lower() == "india"


def _pronunciation_instruction(row: Any) -> str:
    """Name pronunciation snippet for ACE-Step instructions."""
    country = getattr(row, "country", "") or ""
    phonetic = getattr(row, "pronunciation", "") or ""
    pron = resolve_pronunciation(row.name, country, phonetic)
    return build_pronunciation_instruction(pron)


def _vocal_cover_caption(row: Any) -> str:
    """Caption for vocal cover pass — same production family as English anthem."""
    base = CELEBRATEVIBES_V2_FULL_CAPTION
    if _is_india(row):
        return f"{base} {CELEBRATEVIBES_V2_INDIA_CAPTION_SUFFIX}"
    return base


def _vocal_cover_instruction(row: Any) -> str:
    """Instruction for vocal cover — exact human lyrics, no AI improvisation."""
    base = (
        f"{CELEBRATEVIBES_V2_FULL_INSTRUCTION} "
        f"{_pronunciation_instruction(row)} "
        "Follow the supplied lyrics exactly. Do NOT invent new words. "
        "Do NOT improvise lyrics. Stick closely to the source production bed chords and groove."
    )
    if _is_india(row):
        return f"{base} {CELEBRATEVIBES_V2_INDIA_INSTRUCTION_SUFFIX}"
    return base


def build_instrumental_bed_lyrics(full_lyrics: str) -> str:
    """Mirror vocal song sections — every section is instrumental only."""
    sections: list[str] = []
    for block in re.split(r"\n\n+", full_lyrics.strip()):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines or not lines[0].startswith("["):
            continue
        sections.append(f"{lines[0]}\n[Instrumental]")
    return "\n\n".join(sections)


def build_production_bed_payload(
    row: Any,
    *,
    instrumental_lyrics: str,
    seed: int | None = None,
) -> dict[str, Any]:
    """Build text2music payload for a short instrumental EDM bed."""
    payload: dict[str, Any] = {
        "prompt": PRODUCTION_BED_CAPTION,
        "lyrics": instrumental_lyrics,
        "instruction": PRODUCTION_BED_INSTRUCTION,
        "thinking": False,
        "use_format": False,
        "use_cot_caption": False,
        "use_cot_language": False,
        "vocal_language": "en",
        "audio_duration": PRODUCTION_BED_DURATION_SEC,
        "bpm": row.bpm or DEFAULT_BPM,
        "key_scale": "C Major",
        "time_signature": "4",
        "inference_steps": BED_INFERENCE_STEPS,
        "guidance_scale": 8.0,
        "batch_size": 1,
        "use_random_seed": seed is None,
        "audio_format": "mp3",
        "model": "acestep-v15-turbo",
        "task_type": "text2music",
    }
    if seed is not None:
        payload["seed"] = seed
    return payload


def build_vocal_cover_payload(
    row: Any,
    *,
    bed_mp3: Path,
    paths: PipelinePaths,
    lyrics: str,
    duration_sec: int = FULL_SONG_DURATION_SEC,
    seed: int | None = None,
) -> dict[str, Any]:
    """Build cover payload: production bed → full song with human lyrics."""
    payload: dict[str, Any] = {
        "prompt": _vocal_cover_caption(row),
        "lyrics": lyrics,
        "instruction": _vocal_cover_instruction(row),
        "thinking": True,
        "use_format": False,
        "use_cot_caption": False,
        "use_cot_language": False,
        "vocal_language": "en",
        "audio_duration": duration_sec,
        "bpm": row.bpm or DEFAULT_BPM,
        "key_scale": "C Major",
        "time_signature": "4",
        "inference_steps": COVER_INFERENCE_STEPS,
        "batch_size": 1,
        "use_random_seed": seed is None,
        "audio_format": "mp3",
        "model": "acestep-v15-turbo",
        "task_type": "cover",
        "src_audio_path": paths.repo_relative(bed_mp3),
        "audio_cover_strength": VOCAL_COVER_STRENGTH,
    }
    if seed is not None:
        payload["seed"] = seed
    return payload


def generate_production_bed(
    row: Any,
    *,
    paths: PipelinePaths,
    api_base: str,
    api_key: str,
    instrumental_lyrics: str,
    seed: int | None = None,
) -> dict[str, Any]:
    """Stage 1 — full-length instrumental EDM bed (no vocals)."""
    bed_path = paths.root / "song" / f"{paths.slug}_bed.mp3"
    payload = build_production_bed_payload(
        row,
        instrumental_lyrics=instrumental_lyrics,
        seed=seed,
    )
    return generate_to_file(
        payload,
        api_base=api_base,
        api_key=api_key,
        out_path=bed_path,
        label="production-bed",
    )


def generate_vocal_cover(
    row: Any,
    *,
    bed_mp3: Path,
    paths: PipelinePaths,
    lyrics: str,
    api_base: str,
    api_key: str,
    duration_sec: int = FULL_SONG_DURATION_SEC,
    seed: int | None = None,
) -> dict[str, Any]:
    """Stage 2 — cover the bed with exact human lyrics and vocals."""
    payload = build_vocal_cover_payload(
        row,
        bed_mp3=bed_mp3,
        paths=paths,
        lyrics=lyrics,
        duration_sec=duration_sec,
        seed=seed,
    )
    return generate_to_file(
        payload,
        api_base=api_base,
        api_key=api_key,
        out_path=paths.body_mp3,
        label="vocal-cover",
    )
