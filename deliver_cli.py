"""Post-process an existing mastered MP3: humanize + upload QC without regenerating."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from batch_birthday.humanize_audio import humanize_mp3
from batch_birthday.orchestrator import BirthdayRow, post_process_delivery, slugify


def _row_from_csv(csv_path: Path, slug: str) -> BirthdayRow:
    """Load one CSV row by slug for deliver metadata."""
    with csv_path.open(newline="", encoding="utf-8") as handle:
        for item in csv.DictReader(handle):
            name = item["name"].strip()
            row_slug = (item.get("slug") or slugify(name)).strip()
            if row_slug != slug:
                continue
            return BirthdayRow(
                name=name,
                language=item.get("language", "en").strip().lower(),
                slug=row_slug,
                bpm=int(item.get("bpm") or 128),
                genre_variant=(item.get("genre_variant") or "").strip(),
            )
    return BirthdayRow(name=slug, language="en", slug=slug, bpm=128, genre_variant="")


def main() -> None:
    """Humanize and scan an existing output MP3 (same song, no ACE-Step regen)."""
    parser = argparse.ArgumentParser(
        description="Humanize + upload QC on existing batch_birthday MP3",
    )
    parser.add_argument("mp3", type=Path, help="Mastered MP3 (e.g. sarah-birthday-edm-party.mp3)")
    parser.add_argument("--csv", type=Path, default=Path(__file__).parent / "input" / "names.csv")
    parser.add_argument("--bpm", type=int, default=0, help="Override BPM for clap grid")
    parser.add_argument("--skip-humanize", action="store_true")
    parser.add_argument("--skip-scan", action="store_true")
    parser.add_argument("--vocal-overlay", type=Path, default=None)
    args = parser.parse_args()

    mp3 = args.mp3.resolve()
    slug = mp3.stem.replace("_human", "").replace("_upload", "")
    row = _row_from_csv(args.csv, slug)
    if args.bpm > 0:
        row.bpm = args.bpm

    from batch_birthday.upload_scan import probe_duration_sec

    duration = int(round(probe_duration_sec(mp3)))
    post_process_delivery(
        mp3,
        row,
        duration,
        humanize=not args.skip_humanize,
        scan_upload=not args.skip_scan,
        vocal_overlay=args.vocal_overlay,
    )


if __name__ == "__main__":
    main()
