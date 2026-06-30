"""Generate full EDM birthday songs via ACE-Step text2music (single pass)."""

from __future__ import annotations

from typing import Any

from batch_birthday.acestep_task import generate_to_file
from batch_birthday.hindi_party_lyrics import (
    CELEBRATEVIBES_V2_INDIA_CAPTION_SUFFIX,
    CELEBRATEVIBES_V2_INDIA_INSTRUCTION_SUFFIX,
)
from batch_birthday.chinese_party_lyrics import (
    CELEBRATEVIBES_V2_CHINA_CAPTION_SUFFIX,
    CELEBRATEVIBES_V2_CHINA_INSTRUCTION_SUFFIX,
)
from batch_birthday.russian_party_lyrics import (
    CELEBRATEVIBES_V2_RUSSIA_CAPTION_SUFFIX,
    CELEBRATEVIBES_V2_RUSSIA_INSTRUCTION_SUFFIX,
)
from batch_birthday.lyrics_builder import (
    CELEBRATEVIBES_V2_FULL_CAPTION,
    CELEBRATEVIBES_V2_FULL_INSTRUCTION,
    build_full_song_lyrics,
    build_generic_full_song_lyrics,
)

GENERIC_SONG_CAPTION = (
    "Professional commercial 128 BPM festival EDM birthday anthem. "
    "Four-on-the-floor kick from beat one. Vocals MUST enter within 6 seconds — "
    "first vocal is a natural human Happy Birthday to You singalong over the dance "
    "beat, NOT an auto-tuned EDM pop hook. Warm female lead, crowd claps on 2 and 4. "
    "Then short drum riser and festival drop into party lyrics. "
    "NOT slow intro, NOT waltz, NOT instrumental opening longer than 3 seconds"
)

GENERIC_SONG_INSTRUCTION = (
    "CRITICAL TIMING: First sung vocals within 6 seconds of start. "
    "NO instrumental intro longer than 3 seconds. NO 40-second delay before vocals. "
    "Open with steady EDM beat, then immediately sing traditional Happy Birthday "
    "to You in a natural human party singalong style — simple clean melody, no "
    "improvisation, no melisma, no person's name. After one complete verse, short "
    "drum riser then festival drop into original party lyrics. Do not sing any "
    "person's name — only 'happy birthday to you' and generic celebration lyrics."
)
from batch_birthday.melody_generator import DEFAULT_BPM
from batch_birthday.name_pronunciation import (
    build_pronunciation_instruction,
    resolve_pronunciation,
)
from batch_birthday.pipeline_paths import PipelinePaths

FULL_SONG_DURATION_SEC = 165
BODY_DURATION_SEC = FULL_SONG_DURATION_SEC  # legacy alias
TEXT2MUSIC_GUIDANCE = 9.5
TEXT2MUSIC_STEPS = 14


_COUNTRY_VOCAL_LANGUAGE: dict[str, str] = {
    "india": "en",
    "united states": "en",
    "russia": "ru",
    "china": "zh",
}


def _country_key(row: Any) -> str:
    """Normalized country label from a batch row."""
    return (getattr(row, "country", "") or "").strip().lower()


def _full_song_instruction(row: Any) -> str:
    """Combine full-song rules with per-name pronunciation guidance."""
    country = getattr(row, "country", "") or ""
    phonetic = getattr(row, "pronunciation", "") or ""
    pron = resolve_pronunciation(row.name, country, phonetic)
    base = f"{CELEBRATEVIBES_V2_FULL_INSTRUCTION} {build_pronunciation_instruction(pron)}"
    key = _country_key(row)
    if key == "india":
        return f"{base} {CELEBRATEVIBES_V2_INDIA_INSTRUCTION_SUFFIX}"
    if key == "russia":
        return f"{base} {CELEBRATEVIBES_V2_RUSSIA_INSTRUCTION_SUFFIX}"
    if key == "china":
        return f"{base} {CELEBRATEVIBES_V2_CHINA_INSTRUCTION_SUFFIX}"
    return base


def _full_song_caption(row: Any) -> str:
    """Return ACE-Step caption with country-specific language suffix."""
    key = _country_key(row)
    if key == "india":
        return f"{CELEBRATEVIBES_V2_FULL_CAPTION} {CELEBRATEVIBES_V2_INDIA_CAPTION_SUFFIX}"
    if key == "russia":
        return f"{CELEBRATEVIBES_V2_FULL_CAPTION} {CELEBRATEVIBES_V2_RUSSIA_CAPTION_SUFFIX}"
    if key == "china":
        return f"{CELEBRATEVIBES_V2_FULL_CAPTION} {CELEBRATEVIBES_V2_CHINA_CAPTION_SUFFIX}"
    return CELEBRATEVIBES_V2_FULL_CAPTION


def _vocal_language(row: Any) -> str:
    """Map country to ACE-Step vocal_language — India stays en (locked mix)."""
    return _COUNTRY_VOCAL_LANGUAGE.get(_country_key(row), "en")


def build_full_song_payload(
    row: Any,
    *,
    lyrics: str,
    duration_sec: int,
    seed: int | None = None,
) -> dict[str, Any]:
    """Build text2music payload for a single-pass EDM birthday song."""
    payload: dict[str, Any] = {
        "prompt": _full_song_caption(row),
        "lyrics": lyrics,
        "instruction": _full_song_instruction(row),
        "thinking": True,
        "use_format": False,
        "use_cot_caption": False,
        "use_cot_language": False,
        "vocal_language": _vocal_language(row),
        "audio_duration": duration_sec,
        "bpm": row.bpm or DEFAULT_BPM,
        "key_scale": "C Major",
        "time_signature": "4",
        "inference_steps": TEXT2MUSIC_STEPS,
        "guidance_scale": TEXT2MUSIC_GUIDANCE,
        "batch_size": 1,
        "use_random_seed": seed is None,
        "audio_format": "mp3",
        "model": "acestep-v15-turbo",
        "task_type": "text2music",
    }
    if seed is not None:
        payload["seed"] = seed
    return payload


def build_body_payload(
    row: Any,
    *,
    lyrics: str,
    duration_sec: int,
    seed: int | None = None,
) -> dict[str, Any]:
    """Legacy alias — full song uses the same payload shape."""
    return build_full_song_payload(row, lyrics=lyrics, duration_sec=duration_sec, seed=seed)


def generate_full_song(
    row: Any,
    *,
    paths: PipelinePaths,
    api_base: str,
    api_key: str,
    duration_sec: int = FULL_SONG_DURATION_SEC,
    seed: int | None = None,
    lyrics_variant: int = 0,
) -> dict[str, Any]:
    """Generate one beat-driven EDM song: intro tune → HB → party lyrics."""
    country = getattr(row, "country", "") or ""
    lyrics = build_full_song_lyrics(
        row.name,
        getattr(row, "language", "en") or "en",
        variant=lyrics_variant,
        country=country,
    )
    paths.body_lyrics.write_text(lyrics + "\n", encoding="utf-8")
    payload = build_full_song_payload(row, lyrics=lyrics, duration_sec=duration_sec, seed=seed)
    return generate_to_file(
        payload,
        api_base=api_base,
        api_key=api_key,
        out_path=paths.body_mp3,
        label="full-song-text2music",
    )


def generate_body(
    row: Any,
    *,
    paths: PipelinePaths,
    api_base: str,
    api_key: str,
    duration_sec: int = FULL_SONG_DURATION_SEC,
    seed: int | None = None,
    lyrics_variant: int = 0,
) -> dict[str, Any]:
    """Legacy alias for generate_full_song."""
    return generate_full_song(
        row,
        paths=paths,
        api_base=api_base,
        api_key=api_key,
        duration_sec=duration_sec,
        seed=seed,
        lyrics_variant=lyrics_variant,
    )


def generate_generic_full_song(
    row: Any,
    *,
    paths: PipelinePaths,
    api_base: str,
    api_key: str,
    duration_sec: int = FULL_SONG_DURATION_SEC,
    seed: int | None = None,
    lyrics_variant: int = 0,
) -> dict[str, Any]:
    """Generate a universal Happy Birthday to You EDM song (no personal name)."""
    lyrics = build_generic_full_song_lyrics(variant=lyrics_variant)
    paths.body_lyrics.write_text(lyrics + "\n", encoding="utf-8")
    payload = build_full_song_payload(row, lyrics=lyrics, duration_sec=duration_sec, seed=seed)
    payload["instruction"] = GENERIC_SONG_INSTRUCTION
    payload["prompt"] = GENERIC_SONG_CAPTION
    payload["vocal_language"] = "en"
    return generate_to_file(
        payload,
        api_base=api_base,
        api_key=api_key,
        out_path=paths.body_mp3,
        label="generic-full-song",
    )
