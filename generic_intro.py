"""Generate a universal Happy Birthday to You channel intro song and video."""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from batch_birthday.api_client import ensure_llm_ready
from batch_birthday.audio_qc import validate_audio
from batch_birthday.orchestrator import BATCH_ROOT, DEFAULT_API_BASE
from batch_birthday.pipeline_paths import PipelinePaths
from batch_birthday.song_generator import FULL_SONG_DURATION_SEC, generate_generic_full_song
from batch_birthday.video_render import master_mp3

GENERIC_SLUG = "happy-birthday-to-you-party"
GENERIC_DISPLAY_TEXT = "To You"
OUTPUT_ROOT = BATCH_ROOT / "output"


@dataclass(frozen=True)
class GenericIntroMeta:
    """Metadata for the universal channel intro asset."""

    slug: str
    title: str
    artist: str
    display_name: str

    @classmethod
    def default(cls) -> GenericIntroMeta:
        """Return default CelebrateVibes channel intro metadata."""
        return cls(
            slug=GENERIC_SLUG,
            title="Happy Birthday to You Song | Birthday Party Music 2026",
            artist="CelebrateVibes",
            display_name=GENERIC_DISPLAY_TEXT,
        )


def _generic_row(*, bpm: int) -> SimpleNamespace:
    """Minimal row object for song_generator."""
    return SimpleNamespace(
        name="You",
        slug=GENERIC_SLUG,
        language="en",
        country="Global",
        pronunciation="",
        bpm=bpm,
    )


def _write_sidecars(
    paths: PipelinePaths,
    meta: GenericIntroMeta,
    *,
    lyrics: str,
    task_id: str,
) -> None:
    """Write JSON sidecars for upload and AE rendering."""
    description = (
        "Happy Birthday to You! 🎂🎉\n\n"
        "A fun party birthday song for everyone — sing along, share with friends, "
        "and celebrate any special day.\n\n"
        "🌍 Personalized name songs & worldwide custom orders:\n"
        "https://celebratevibes.com\n\n"
        "🔔 Subscribe to CelebrateVibes for more birthday songs with names "
        "from around the world.\n\n"
        "#HappyBirthday #HappyBirthdayToYou #BirthdaySong #CelebrateVibes "
        "#BirthdayParty #BirthdayWishes"
    )
    youtube = {
        "brand": "CelebrateVibes",
        "name": "You",
        "display_name": meta.display_name,
        "title": meta.title,
        "artist": meta.artist,
        "description": description,
        "tags": [
            "happy birthday to you",
            "happy birthday song",
            "birthday song",
            "happy birthday",
            "birthday party song",
            "celebratevibes",
            "birthday music",
            "party birthday song",
            "birthday wishes",
            "birthday celebration",
        ],
        "category": "Music",
        "privacy": "public",
    }
    paths.root.mkdir(parents=True, exist_ok=True)
    (paths.root / f"{meta.slug}.youtube.json").write_text(
        json.dumps(youtube, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    paths.sidecar_json.write_text(
        json.dumps(
            {
                "slug": meta.slug,
                "name": "You",
                "display_name": meta.display_name,
                "pipeline": "generic_channel_intro",
                "full_lyrics": lyrics,
                "song_task_id": task_id,
                "youtube": youtube,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def generate_generic_intro_mp3(
    *,
    api_base: str = DEFAULT_API_BASE,
    api_key: str = "",
    bpm: int = 128,
    force: bool = False,
) -> Path:
    """Generate and master the universal Happy Birthday to You MP3."""
    meta = GenericIntroMeta.default()
    paths = PipelinePaths.for_slug(OUTPUT_ROOT, meta.slug)
    deliver_mp3 = paths.root / f"{meta.slug}.mp3"
    if not force and deliver_mp3.is_file() and deliver_mp3.stat().st_size > 100_000:
        print(f"SKIP (mp3 exists): {deliver_mp3}")
        return deliver_mp3

    ensure_llm_ready(api_base, api_key)
    row = _generic_row(bpm=bpm)
    song_meta = generate_generic_full_song(
        row,
        paths=paths,
        api_base=api_base,
        api_key=api_key,
        duration_sec=FULL_SONG_DURATION_SEC,
        seed=42_026_632,
        lyrics_variant=0,
    )
    lyrics = paths.body_lyrics.read_text(encoding="utf-8")
    validate_audio(
        paths.body_mp3,
        label="generic-full-song",
        min_duration_sec=120.0,
        max_duration_sec=float(FULL_SONG_DURATION_SEC + 30),
    )
    master_mp3(paths.body_mp3, paths.raw_mp3)
    shutil.copy2(paths.raw_mp3, deliver_mp3)
    _write_sidecars(paths, meta, lyrics=lyrics, task_id=str(song_meta.get("task_id", "")))
    print(f"GENERIC MP3 READY: {deliver_mp3}")
    return deliver_mp3


def main() -> None:
    """CLI: generate generic intro MP3 (and optionally AE video via ae-batch)."""
    parser = argparse.ArgumentParser(description="CelebrateVibes generic Happy Birthday to You")
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--api-key", default="")
    parser.add_argument("--bpm", type=int, default=128)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--video", action="store_true", help="Also render AE YouTube video")
    args = parser.parse_args()

    generate_generic_intro_mp3(
        api_base=args.api_base,
        api_key=args.api_key,
        bpm=args.bpm,
        force=args.force,
    )
    if args.video:
        from batch_birthday.ae_batch_cli import main as ae_main
        import sys

        sys.argv = [sys.argv[0], "--slug", GENERIC_SLUG, "--force"]
        ae_main()


if __name__ == "__main__":
    main()
