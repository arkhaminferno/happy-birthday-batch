"""CSV-driven batch birthday song generator: ACE-Step API → MP3 → MP4."""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from batch_birthday.api_client import (
    download_audio,
    ensure_llm_ready,
    parse_track_result,
    poll_task,
    submit_task,
)
from batch_birthday.ingest_reference import (
    PREPARED_WAV,
    prepare_reference,
    probe_duration_sec,
    resolve_user_reference,
)
from batch_birthday.audio_edit import stitch_crossfade
from batch_birthday.lyrics_builder import (
    DEFAULT_BIRTHDAY_BPM,
    FAST_BIRTHDAY_BPM,
    GENRE_CAPTIONS,
    HYBRID_BODY_SEC,
    HYBRID_CROSSFADE_SEC,
    HYBRID_INTRO_REFERENCE_STRENGTH,
    HYBRID_INTRO_SEC,
    HYBRID_VOCAL_INSTRUCTION,
    LANGUAGE_MAP,
    TRADITIONAL_COVER_STRENGTH,
    USER_TEMPLATE_COVER_STRENGTH,
    USER_TEMPLATE_REFERENCE_STRENGTH,
    SONG_COVER_STRENGTH,
    GUITAR_COVER_STRENGTH,
    GUITAR_COVER_INSTRUCTION,
    BIRTHDAY_ANTHEM_VOCAL_INSTRUCTION,
    BIRTHDAY_CLASSIC_EXTENDED_INSTRUCTION,
    BIRTHDAY_RESTAURANT_PARTY_INSTRUCTION,
    BIRTHDAY_EDM_PARTY_INSTRUCTION,
    BIRTHDAY_EDM_PARTY_V2_INSTRUCTION,
    BIRTHDAY_EDM_PARTY_V3_INSTRUCTION,
    BIRTHDAY_EDM_PARTY_V4_INSTRUCTION,
    BIRTHDAY_EDM_PARTY_V5_INSTRUCTION,
    BIRTHDAY_EDM_MELODY_REFERENCE_STRENGTH,
    BIRTHDAY_EDM_PARTY_V4_REFERENCE_STRENGTH,
    GENRE_MELODY_REFERENCE_STRENGTH,
    GENRE_MELODY_REFERENCE_FILE,
    resolve_melody_reference_file,
    BIRTHDAY_ANTHEM_GENRES,
    MELODY_FIRST_BIRTHDAY_GENRES,
    VOCAL_FORWARD_BIRTHDAY_GENRES,
    CLASSIC_BIRTHDAY_GENRES,
    EDM_BIRTHDAY_GENRES,
    NO_MELODY_REFERENCE_GENRES,
    genre_duration_sec,
    genre_caption,
    ANTHEM_SLUG_SUFFIXES,
    build_lyrics,
    genre_time_signature,
)
from batch_birthday.video_render import master_mp3, master_mp3_vocal_forward, render_video
from batch_birthday.humanize_audio import humanize_mp3
from batch_birthday.upload_scan import (
    prepare_upload_copy,
    print_report,
    scan_for_upload,
    write_report_json,
)

AUDIO_DURATION_SEC = 240
DEFAULT_BPM = DEFAULT_BIRTHDAY_BPM
DEFAULT_API_BASE = "http://127.0.0.1:8001"
BATCH_ROOT = Path(__file__).resolve().parent
MELODY_REFERENCE_WAV = BATCH_ROOT / "templates" / "audio" / "happy_birthday_reference.wav"
COVER_STRENGTH = TRADITIONAL_COVER_STRENGTH
TEXT2MUSIC_GUIDANCE = 8.5
TEXT2MUSIC_STEPS = 12
HYBRID_GUIDANCE = 9.5
HYBRID_STEPS = 14


def post_process_delivery(
    mastered_mp3: Path,
    row: BirthdayRow,
    duration_sec: int,
    *,
    humanize: bool,
    scan_upload: bool,
    vocal_overlay: Path | None,
) -> Path:
    """Optional humanize + upload QC; returns best file for YouTube upload."""
    deliverable = mastered_mp3
    if humanize:
        human_mp3 = mastered_mp3.with_name(f"{mastered_mp3.stem}_human.mp3")
        humanize_mp3(
            mastered_mp3,
            human_mp3,
            duration_sec=duration_sec,
            bpm=row.bpm or DEFAULT_BPM,
            vocal_overlay=vocal_overlay,
        )
        deliverable = human_mp3
        print(f"HUMANIZED: {human_mp3}")

    if scan_upload:
        upload_mp3 = deliverable.with_name(f"{deliverable.stem}_upload.mp3")
        prepare_upload_copy(
            deliverable,
            upload_mp3,
            title=f"Happy Birthday {row.name}",
        )
        report = scan_for_upload(upload_mp3)
        report_path = upload_mp3.with_suffix(".scan.json")
        write_report_json(report, report_path)
        print_report(report)
        print(f"UPLOAD READY: {upload_mp3}")
        print(f"SCAN REPORT: {report_path}")
        return upload_mp3

    return deliverable


@dataclass
class BirthdayRow:
    """One row from the input CSV."""

    name: str
    language: str
    slug: str
    bpm: int
    genre_variant: str
    age: str = ""
    city: str = ""
    hobby: str = ""
    relationship: str = ""
    seed: str = ""


def resolve_slug(name: str, slug: str, genre_variant: str) -> str:
    """Build output slug; auto-suffix commercial anthem variants when slug is empty."""
    if slug.strip():
        return slug.strip()
    base = slugify(name)
    suffix = ANTHEM_SLUG_SUFFIXES.get(genre_variant)
    if suffix:
        return f"{base}-{suffix}"
    return base or "birthday-song"


def slugify(text: str) -> str:
    """Create a filesystem-safe slug from a display name."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower()
    return slug or "birthday-song"


def load_csv(path: Path) -> list[BirthdayRow]:
    """Load enabled rows from the names CSV."""
    rows: list[BirthdayRow] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for item in csv.DictReader(handle):
            if item.get("enabled", "true").lower() not in ("1", "true", "yes"):
                continue
            genre = (item.get("genre_variant") or "happy_birthday_fast").strip()
            name = item["name"].strip()
            rows.append(
                BirthdayRow(
                    name=name,
                    language=item.get("language", "en").strip().lower(),
                    slug=resolve_slug(name, item.get("slug") or "", genre),
                    bpm=int(item.get("bpm") or DEFAULT_BPM),
                    genre_variant=genre,
                    age=(item.get("age") or "").strip(),
                    city=(item.get("city") or "").strip(),
                    hobby=(item.get("hobby") or "").strip(),
                    relationship=(item.get("relationship") or "").strip(),
                    seed=(item.get("seed") or "").strip(),
                )
            )
    return rows


def build_payload(
    row: BirthdayRow,
    *,
    use_cover: bool,
    duration_sec: int,
    cover_src: Path | None = None,
    cover_strength: float | None = None,
    genre_override: str | None = None,
    reference_src: Path | None = None,
    reference_strength: float | None = None,
    lyrics_override: str | None = None,
    guidance_scale: float | None = None,
    inference_steps: int | None = None,
    instruction: str | None = None,
) -> dict[str, Any]:
    """Build ACE-Step /release_task JSON body for one birthday song."""
    vocal_lang = LANGUAGE_MAP.get(row.language, row.language)
    genre = genre_override or row.genre_variant
    caption = genre_caption(genre, row.language)
    bpm = row.bpm if row.bpm else FAST_BIRTHDAY_BPM
    cover_mode = use_cover
    strength = cover_strength if cover_strength is not None else TRADITIONAL_COVER_STRENGTH
    lyrics = lyrics_override or build_lyrics(
        row.name,
        row.language,
        genre_variant=genre,
        age=row.age,
        city=row.city,
        hobby=row.hobby,
        relationship=row.relationship,
    )
    is_vocal_forward = genre in VOCAL_FORWARD_BIRTHDAY_GENRES
    payload: dict[str, Any] = {
        "prompt": caption,
        "lyrics": lyrics,
        "thinking": True,
        "use_format": False,
        "use_cot_caption": False,
        "use_cot_language": False,
        "vocal_language": vocal_lang,
        "audio_duration": duration_sec,
        "bpm": bpm,
        "key_scale": "C Major",
        "time_signature": genre_time_signature(genre),
        "inference_steps": (
            inference_steps
            if inference_steps is not None
            else (HYBRID_STEPS if is_vocal_forward else TEXT2MUSIC_STEPS)
        ),
        "guidance_scale": (
            guidance_scale
            if guidance_scale is not None
            else (HYBRID_GUIDANCE if is_vocal_forward else TEXT2MUSIC_GUIDANCE)
        ),
        "batch_size": 1,
        "use_random_seed": True,
        "audio_format": "mp3",
        "model": "acestep-v15-turbo",
        "task_type": "text2music",
    }
    if row.seed:
        payload["use_random_seed"] = False
        payload["seed"] = row.seed
    if genre == "birthday_edm_party_v5" and not instruction:
        payload["instruction"] = BIRTHDAY_EDM_PARTY_V5_INSTRUCTION
    elif genre == "birthday_edm_party_v4" and not instruction:
        payload["instruction"] = BIRTHDAY_EDM_PARTY_V4_INSTRUCTION
    elif genre == "birthday_edm_party_v3" and not instruction:
        payload["instruction"] = BIRTHDAY_EDM_PARTY_V3_INSTRUCTION
    elif genre == "birthday_edm_party_v2" and not instruction:
        payload["instruction"] = BIRTHDAY_EDM_PARTY_V2_INSTRUCTION
    elif genre == "birthday_edm_party_v1" and not instruction:
        payload["instruction"] = BIRTHDAY_EDM_PARTY_INSTRUCTION
    elif genre == "birthday_restaurant_party_v1" and not instruction:
        payload["instruction"] = BIRTHDAY_RESTAURANT_PARTY_INSTRUCTION
    elif genre == "birthday_classic_extended" and not instruction:
        payload["instruction"] = BIRTHDAY_CLASSIC_EXTENDED_INSTRUCTION
    elif genre in BIRTHDAY_ANTHEM_GENRES and not instruction:
        payload["instruction"] = BIRTHDAY_ANTHEM_VOCAL_INSTRUCTION
    if instruction:
        payload["instruction"] = instruction
    if cover_mode:
        src = cover_src or MELODY_REFERENCE_WAV
        payload["thinking"] = False
        payload["inference_steps"] = 10
        payload.pop("guidance_scale", None)
        if not src.exists():
            raise FileNotFoundError(f"Cover reference missing: {src}")
        rel_ref = src.relative_to(BATCH_ROOT.parent)
        if genre == "user_template_cover":
            cover_instruction = (
                "Cover the source recording. Preserve the exact melody, tempo, and duet vocal style. "
                "Sing the new birthday lyrics clearly with two voices (male and female) like the source."
            )
        elif genre == "song_cover":
            cover_instruction = (
                "Cover the source recording faithfully. Preserve the exact melody, tempo, mood, "
                "and arrangement. Sing the Hindi lyrics clearly with the same emotional delivery."
            )
        elif genre == "song_guitar_cover":
            cover_instruction = GUITAR_COVER_INSTRUCTION
        else:
            cover_instruction = (
                "Cover and preserve the exact Happy Birthday to You melody from the source. "
                "Sing the lyrics clearly with a warm adult female voice."
            )
        if instruction:
            cover_instruction = instruction
        payload.update(
            {
                "task_type": "cover",
                "src_audio_path": str(rel_ref),
                "audio_cover_strength": strength,
                "instruction": cover_instruction,
            }
        )
    elif reference_src is not None:
        if not reference_src.exists():
            raise FileNotFoundError(f"Reference audio missing: {reference_src}")
        rel_ref = reference_src.relative_to(BATCH_ROOT.parent)
        ref_strength = (
            reference_strength
            if reference_strength is not None
            else USER_TEMPLATE_REFERENCE_STRENGTH
        )
        payload["reference_audio_path"] = str(rel_ref)
        payload["audio_cover_strength"] = ref_strength
    return payload


def _generate_segment(
    row: BirthdayRow,
    *,
    api_base: str,
    api_key: str,
    out_path: Path,
    duration_sec: int,
    genre: str,
    lyrics: str,
    reference_src: Path | None = None,
    reference_strength: float | None = None,
) -> dict[str, Any]:
    """Submit one ACE-Step job, download audio, return track metadata."""
    vocal_instruction = HYBRID_VOCAL_INSTRUCTION if genre.startswith("party_dance") else None
    payload = build_payload(
        row,
        use_cover=False,
        duration_sec=duration_sec,
        genre_override=genre,
        reference_src=reference_src,
        reference_strength=reference_strength,
        lyrics_override=lyrics,
        guidance_scale=HYBRID_GUIDANCE,
        inference_steps=HYBRID_STEPS,
        instruction=vocal_instruction,
    )
    task_id = submit_task(api_base, payload, api_key)
    print(f"POLL: {task_id} ({genre}, {duration_sec}s)")
    result = poll_task(api_base, task_id, api_key)
    tracks = parse_track_result(result)
    if not tracks:
        raise RuntimeError(f"No audio tracks for {genre} segment")
    download_audio(api_base, tracks[0]["file"], str(out_path), api_key)
    return {"task_id": task_id, "track": tracks[0], "payload": payload}


def process_row_hybrid(
    row: BirthdayRow,
    *,
    api_base: str,
    api_key: str,
    output_root: Path,
    state_file: Path,
    skip_video: bool,
    video_bg: Path | None,
    force: bool,
    template_src: Path | None,
    total_duration_sec: int,
) -> Path:
    """Two-pass hybrid: beat-first HB intro + former dance body, stitched."""
    out_dir = output_root / row.slug
    out_dir.mkdir(parents=True, exist_ok=True)
    final_mp3 = out_dir / f"{row.slug}.mp3"
    if not force and final_mp3.exists() and final_mp3.stat().st_size > 0:
        print(f"SKIP (exists): {final_mp3}")
        return final_mp3

    reference_src: Path | None = None
    if template_src is not None:
        prepare_reference(template_src)
        reference_src = PREPARED_WAV
        print(f"INTRO REF: {template_src.name} (melody hint strength {HYBRID_INTRO_REFERENCE_STRENGTH})")

    intro_lyrics = build_lyrics(row.name, row.language, genre_variant="party_dance_intro")
    body_lyrics = build_lyrics(row.name, row.language, genre_variant="party_dance_body")

    print(f"HYBRID SUBMIT: {row.name} → intro {HYBRID_INTRO_SEC}s + body {HYBRID_BODY_SEC}s")
    intro_meta = _generate_segment(
        row,
        api_base=api_base,
        api_key=api_key,
        out_path=out_dir / f"{row.slug}_intro_raw.mp3",
        duration_sec=HYBRID_INTRO_SEC,
        genre="party_dance_intro",
        lyrics=intro_lyrics,
        reference_src=reference_src,
        reference_strength=HYBRID_INTRO_REFERENCE_STRENGTH,
    )
    body_meta = _generate_segment(
        row,
        api_base=api_base,
        api_key=api_key,
        out_path=out_dir / f"{row.slug}_body_raw.mp3",
        duration_sec=HYBRID_BODY_SEC,
        genre="party_dance_body",
        lyrics=body_lyrics,
    )

    stitched = out_dir / f"{row.slug}_stitched.mp3"
    stitch_crossfade(
        out_dir / f"{row.slug}_intro_raw.mp3",
        out_dir / f"{row.slug}_body_raw.mp3",
        stitched,
        crossfade_sec=HYBRID_CROSSFADE_SEC,
        total_duration_sec=float(total_duration_sec),
    )
    master_mp3_vocal_forward(stitched, final_mp3)

    meta = {
        "name": row.name,
        "slug": row.slug,
        "language": row.language,
        "genre_variant": "party_dance_hybrid",
        "hybrid": True,
        "intro_sec": HYBRID_INTRO_SEC,
        "body_sec": HYBRID_BODY_SEC,
        "intro_task_id": intro_meta["task_id"],
        "body_task_id": body_meta["task_id"],
        "intro_lyrics": intro_lyrics,
        "body_lyrics": body_lyrics,
        "template_source": str(template_src) if template_src else None,
        "duration_target_sec": total_duration_sec,
        "task_type": "text2music_hybrid",
    }
    (out_dir / f"{row.slug}.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    append_state(state_file, {"slug": row.slug, "status": "done", "hybrid": True})
    print(f"DONE (hybrid edit): {final_mp3}")
    return final_mp3


def append_state(state_file: Path, record: dict[str, Any]) -> None:
    """Append one JSON line to the job state log."""
    state_file.parent.mkdir(parents=True, exist_ok=True)
    with state_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def process_row(
    row: BirthdayRow,
    *,
    api_base: str,
    api_key: str,
    output_root: Path,
    state_file: Path,
    video_bg: Path | None,
    skip_video: bool,
    force: bool,
    use_cover: bool,
    duration_sec: int,
    cover_src: Path | None = None,
    cover_strength: float | None = None,
    genre_override: str | None = None,
    reference_src: Path | None = None,
    reference_strength: float | None = None,
    vocal_forward_master: bool = False,
    humanize: bool = False,
    scan_upload: bool = False,
    vocal_overlay: Path | None = None,
) -> Path:
    """Generate one birthday song and optional video for a CSV row."""
    out_dir = output_root / row.slug
    out_dir.mkdir(parents=True, exist_ok=True)
    final_mp3 = out_dir / f"{row.slug}.mp3"
    out_mp4 = out_dir / f"{row.slug}.mp4"

    if not force and final_mp3.exists() and final_mp3.stat().st_size > 0:
        print(f"SKIP (exists): {final_mp3}")
        return final_mp3

    print(f"SUBMIT: {row.name} ({row.language}) → {row.slug}")
    cover_mode = use_cover
    payload = build_payload(
        row,
        use_cover=use_cover,
        duration_sec=duration_sec,
        cover_src=cover_src,
        cover_strength=cover_strength,
        genre_override=genre_override,
        reference_src=reference_src,
        reference_strength=reference_strength,
    )
    task_id = submit_task(api_base, payload, api_key)
    append_state(state_file, {"slug": row.slug, "task_id": task_id, "status": "submitted"})

    mins = duration_sec // 60
    if cover_mode:
        mode = "cover+melody"
    elif reference_src is not None:
        mode = "text2music+reference+vocals"
    else:
        mode = "text2music+vocals"
    print(f"POLL: {task_id} ({mode}, ~{mins} min — expect 10–30 min on Mac)")
    result = poll_task(api_base, task_id, api_key)
    tracks = parse_track_result(result)
    if not tracks:
        raise RuntimeError(f"No audio tracks in result for {row.slug}")

    raw_mp3 = out_dir / f"{row.slug}_raw.mp3"
    download_audio(api_base, tracks[0]["file"], str(raw_mp3), api_key)
    if vocal_forward_master:
        master_mp3_vocal_forward(raw_mp3, final_mp3)
    else:
        master_mp3(raw_mp3, final_mp3)

    meta = {
        "name": row.name,
        "slug": row.slug,
        "language": row.language,
        "genre_variant": genre_override or row.genre_variant,
        "task_id": task_id,
        "prompt": tracks[0].get("prompt"),
        "lyrics": tracks[0].get("lyrics"),
        "seed": tracks[0].get("seed_value"),
        "duration_target_sec": duration_sec,
        "task_type": "cover" if cover_mode else "text2music",
        "cover_strength": cover_strength if cover_mode else reference_strength,
        "reference_source": str(cover_src or reference_src) if (cover_src or reference_src) else None,
    }
    (out_dir / f"{row.slug}.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    if not skip_video:
        render_video(final_mp3, row.name, out_mp4, AUDIO_DURATION_SEC, video_bg)
        print(f"VIDEO: {out_mp4}")

    append_state(state_file, {"slug": row.slug, "task_id": task_id, "status": "done"})
    post_process_delivery(
        final_mp3,
        row,
        duration_sec,
        humanize=humanize,
        scan_upload=scan_upload,
        vocal_overlay=vocal_overlay,
    )
    print(f"DONE: {final_mp3}")
    return final_mp3


def main() -> None:
    """CLI entry: process all enabled rows in the input CSV serially."""
    parser = argparse.ArgumentParser(description="Batch birthday songs via ACE-Step API")
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path(__file__).resolve().parent / "input" / "names.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "output",
    )
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--api-key", default="")
    parser.add_argument("--limit", type=int, default=0, help="Max rows (0 = all)")
    parser.add_argument(
        "--skip-video",
        action="store_true",
        default=True,
        help="Skip MP4 rendering (default: on)",
    )
    parser.add_argument(
        "--with-video",
        action="store_true",
        help="Also render MP4 video",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=AUDIO_DURATION_SEC,
        help="Target audio length in seconds (default: 240)",
    )
    parser.add_argument("--force", action="store_true", help="Regenerate even if output exists")
    parser.add_argument(
        "--reference",
        type=Path,
        default=None,
        help="User MP3/WAV template (auto-detects default in templates/audio/)",
    )
    parser.add_argument(
        "--cover",
        action="store_true",
        help="Cover mode: loop template as src_audio (melody lock, weak name swap)",
    )
    parser.add_argument(
        "--no-hybrid",
        action="store_true",
        help="Single-pass generation (party_dance default uses hybrid intro+body edit)",
    )
    parser.add_argument(
        "--no-reference",
        action="store_true",
        help="Ignore user MP3 template (hybrid intro will have no melody hint)",
    )
    parser.add_argument("--video-bg", type=Path, default=None)
    parser.add_argument(
        "--humanize",
        action="store_true",
        help="Layer room tone + claps and warm master after generation",
    )
    parser.add_argument(
        "--scan-upload",
        action="store_true",
        help="Run upload QC scan and write *_upload.mp3 with clean tags",
    )
    parser.add_argument(
        "--vocal-overlay",
        type=Path,
        default=None,
        help="Optional live vocal WAV/MP3 blended during --humanize",
    )
    args = parser.parse_args()

    batch_root = BATCH_ROOT
    state_file = batch_root / "state" / "jobs.jsonl"
    video_bg = args.video_bg or (batch_root / "templates" / "video" / "background.mp4")

    rows = load_csv(args.csv)
    if args.limit > 0:
        rows = rows[: args.limit]

    if not rows:
        raise SystemExit(f"No enabled rows in {args.csv}")

    template_src = None if args.no_reference else resolve_user_reference(args.reference)
    use_hybrid_default = not args.no_hybrid

    if not args.cover:
        ensure_llm_ready(args.api_base, args.api_key)

    skip_video = not args.with_video
    for row in rows:
        if row.genre_variant == "party_dance" and use_hybrid_default and not args.cover:
            process_row_hybrid(
                row,
                api_base=args.api_base,
                api_key=args.api_key,
                output_root=args.output,
                state_file=state_file,
                skip_video=skip_video,
                video_bg=video_bg if video_bg.exists() else None,
                force=args.force,
                template_src=template_src,
                total_duration_sec=args.duration,
            )
            continue

        cover_src: Path | None = None
        reference_src: Path | None = None
        cover_strength: float | None = None
        reference_strength: float | None = None
        genre_override: str | None = None
        duration_sec = genre_duration_sec(row.genre_variant, args.duration)
        if duration_sec != args.duration:
            print(f"DURATION: {duration_sec}s (template default)")
        use_cover = args.cover or row.genre_variant in ("song_cover", "song_guitar_cover")

        if row.genre_variant in GENRE_MELODY_REFERENCE_STRENGTH:
            hb_ref = resolve_melody_reference_file(row.genre_variant, BATCH_ROOT)
            if hb_ref is not None:
                prepare_reference(hb_ref)
                reference_src = PREPARED_WAV
                reference_strength = GENRE_MELODY_REFERENCE_STRENGTH[row.genre_variant]
                print(
                    f"MELODY BLUEPRINT: {hb_ref.name} "
                    f"(strength {reference_strength})"
                )
            else:
                print(f"WARN: melody reference missing for {row.genre_variant}")
        elif row.genre_variant in ("song_cover", "song_guitar_cover"):
            song_path = args.reference
            if song_path is None or not song_path.exists():
                song_path = BATCH_ROOT / "templates" / "audio" / "Jaaniya Haunted 128 Kbps.mp3"
            if not song_path.exists():
                raise FileNotFoundError(f"Cover source not found: {song_path}")
            print(f"COVER SOURCE: {song_path.name}")
            prepare_reference(song_path)
            duration_sec = int(round(probe_duration_sec(song_path)))
            cover_src = PREPARED_WAV
            if row.genre_variant == "song_guitar_cover":
                cover_strength = GUITAR_COVER_STRENGTH
                genre_override = "song_guitar_cover"
                print(
                    f"GUITAR COVER: cover mode, melody lock {cover_strength} "
                    f"({duration_sec}s)"
                )
            else:
                cover_strength = SONG_COVER_STRENGTH
                print(f"PREPARED: {cover_src} ({duration_sec}s, strength {cover_strength})")
        elif (
            template_src
            and not args.no_reference
            and row.genre_variant not in NO_MELODY_REFERENCE_GENRES
        ):
            print(f"TEMPLATE: {template_src.name}")
            src_duration = probe_duration_sec(template_src)
            print(f"  source length: {src_duration:.1f}s")
            if use_cover:
                ref_duration = prepare_reference(
                    template_src,
                    loop_to_duration_sec=float(args.duration),
                )
                duration_sec = int(round(ref_duration))
                cover_src = PREPARED_WAV
                cover_strength = USER_TEMPLATE_COVER_STRENGTH
                print(f"PREPARED (looped cover): {cover_src} ({ref_duration:.1f}s)")
            else:
                prepare_reference(template_src)
                reference_src = PREPARED_WAV
                reference_strength = USER_TEMPLATE_REFERENCE_STRENGTH
                print(f"PREPARED (style reference): {reference_src}")
            genre_override = "user_template_cover"

        process_row(
            row,
            api_base=args.api_base,
            api_key=args.api_key,
            output_root=args.output,
            state_file=state_file,
            video_bg=video_bg if video_bg.exists() else None,
            skip_video=skip_video,
            force=args.force,
            use_cover=use_cover,
            duration_sec=duration_sec,
            cover_src=cover_src,
            cover_strength=cover_strength,
            genre_override=genre_override,
            reference_src=reference_src,
            reference_strength=reference_strength,
            vocal_forward_master=row.genre_variant in VOCAL_FORWARD_BIRTHDAY_GENRES
                or row.genre_variant == "song_guitar_cover",
            humanize=args.humanize,
            scan_upload=args.scan_upload,
            vocal_overlay=args.vocal_overlay,
        )


if __name__ == "__main__":
    main()
