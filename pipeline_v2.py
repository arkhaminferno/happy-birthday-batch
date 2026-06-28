"""CelebrateVibes v2 — single-pass EDM: intro tune → Happy Birthday → party body."""

from __future__ import annotations

import json
import zlib
from pathlib import Path
from typing import Any

from batch_birthday.audio_qc import validate_audio
from batch_birthday.batch_variation import song_variation_for
from batch_birthday.native_party_lyrics import build_native_body_lyrics
from batch_birthday.lyrics_builder import (
    build_body_lyrics,
    build_full_song_lyrics,
    build_verse1_lyrics,
    genre_duration_sec,
)
from batch_birthday.name_pronunciation import resolve_pronunciation
from batch_birthday.pipeline_paths import PipelinePaths
from batch_birthday.song_generator import FULL_SONG_DURATION_SEC, generate_full_song
from batch_birthday.video_render import master_mp3


def _parse_seed(row: Any) -> int | None:
    """Parse optional CSV seed into an integer."""
    raw = getattr(row, "seed", "") or ""
    if not str(raw).strip():
        return None
    return int(str(raw).strip())


def _step_seed(base_seed: int, step: str) -> int:
    """Derive a stable per-step seed from the row seed."""
    return zlib.crc32(f"{base_seed}:{step}".encode()) & 0xFFFFFFFF


def process_row_v2(
    row: Any,
    *,
    api_base: str,
    api_key: str,
    output_root: Path,
    state_file: Path,
    force: bool,
    raw_only: bool = True,
    humanize: bool = False,
    scan_upload: bool = False,
    vocal_overlay: Path | None = None,
    append_state_fn: Any,
    post_process_fn: Any,
) -> Path:
    """Run v2: single-pass EDM with intro tune → HB → party lyrics."""
    paths = PipelinePaths.for_slug(output_root, row.slug)
    if not force and paths.raw_mp3.exists() and paths.raw_mp3.stat().st_size > 0:
        print(f"SKIP (v2 raw exists): {paths.raw_mp3}")
        return paths.raw_mp3

    print(f"V2 PIPELINE: {row.name} ({row.language}) → {row.slug}")
    country = getattr(row, "country", "") or ""
    song_variation = song_variation_for(row.name, country)
    if row.bpm <= 0:
        row.bpm = song_variation.bpm
    pron = resolve_pronunciation(
        row.name,
        country,
        getattr(row, "pronunciation", "") or "",
    )
    print(f"PRONUNCIATION: {row.name} → {pron.phonetic}")

    base_seed = _parse_seed(row)
    song_seed = _step_seed(base_seed, "full") if base_seed is not None else None

    song_meta = generate_full_song(
        row,
        paths=paths,
        api_base=api_base,
        api_key=api_key,
        duration_sec=FULL_SONG_DURATION_SEC,
        seed=song_seed,
        lyrics_variant=song_variation.lyrics_variant,
    )
    song_qc = validate_audio(
        paths.body_mp3,
        label="full-song",
        min_duration_sec=120.0,
        max_duration_sec=float(FULL_SONG_DURATION_SEC + 30),
    )
    append_state_fn(state_file, {"slug": row.slug, "step": "full_song", "status": "done"})

    total_sec = float(genre_duration_sec("celebratevibes_v2", 165))
    master_mp3(paths.body_mp3, paths.raw_mp3)
    print(
        "OPENING: EDM beat → ~2-3s intro tune → Happy Birthday → party lyrics → "
        f"{paths.raw_mp3}"
    )

    meta = {
        "name": row.name,
        "slug": row.slug,
        "language": row.language,
        "country": country,
        "pronunciation": pron.phonetic,
        "genre_variant": "celebratevibes_v2",
        "pipeline": "celebratevibes_v2_single_pass_edm",
        "full_lyrics": build_full_song_lyrics(
            row.name,
            "en",
            variant=song_variation.lyrics_variant,
            country=country,
        ),
        "verse1_lyrics": build_verse1_lyrics(row.name),
        "body_lyrics": build_native_body_lyrics(
            row.name,
            country,
            variant=song_variation.lyrics_variant,
            native_name=pron.native_script,
            language=row.language,
        )
        if country.strip().lower() in ("india", "russia", "china")
        else build_body_lyrics(
            row.name,
            "en",
            variant=song_variation.lyrics_variant,
        ),
        "song_variation": song_variation.to_dict(),
        "song_task_id": song_meta["task_id"],
        "qc": {"full_song": song_qc.to_dict()},
        "seed": str(base_seed) if base_seed is not None else song_meta["track"].get("seed_value"),
        "duration_target_sec": int(total_sec),
        "task_type": "single_pass_v2",
        "stages": {
            "song": str(paths.body_mp3),
            "master": str(paths.raw_mp3),
        },
        "approval_status": "pending" if raw_only and not humanize else "delivered",
        "raw_mp3": str(paths.raw_mp3),
    }
    paths.sidecar_json.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    append_state_fn(state_file, {"slug": row.slug, "status": "done", "pipeline": "v2"})

    if raw_only and not humanize and not scan_upload:
        print(
            "Review the raw MP3 first. After approval run:\n"
            f"  python -m batch_birthday deliver {paths.raw_mp3}"
        )
        return paths.raw_mp3

    post_process_fn(
        paths.raw_mp3,
        row,
        int(total_sec),
        humanize=humanize,
        scan_upload=scan_upload,
        vocal_overlay=vocal_overlay,
    )
    return paths.raw_mp3
