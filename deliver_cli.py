"""Post-process an approved raw MP3: master + humanize + upload QC."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from batch_birthday.batch_variation import master_variation_for
from batch_birthday.humanize_audio import humanize_mp3
from batch_birthday.orchestrator import BirthdayRow, post_process_delivery, slugify
from batch_birthday.upload_verify import verify_for_upload
from batch_birthday.video_render import master_mp3


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
    """Master, humanize, and verify an approved raw batch MP3."""
    parser = argparse.ArgumentParser(
        description="Deliver approved raw MP3: master + humanize + upload QC",
    )
    parser.add_argument(
        "mp3",
        type=Path,
        help="Raw or mastered MP3 (e.g. suhani-birthday-edm-party_raw.mp3)",
    )
    parser.add_argument("--csv", type=Path, default=Path(__file__).parent / "input" / "names.csv")
    parser.add_argument("--bpm", type=int, default=0, help="Override BPM for clap grid")
    parser.add_argument("--skip-humanize", action="store_true")
    parser.add_argument("--skip-scan", action="store_true")
    parser.add_argument("--vocal-overlay", type=Path, default=None)
    args = parser.parse_args()

    mp3 = args.mp3.resolve()
    stem = mp3.stem.replace("_human", "").replace("_upload", "").replace("_raw", "")
    slug = stem
    row = _row_from_csv(args.csv, slug)
    if args.bpm > 0:
        row.bpm = args.bpm

    from batch_birthday.upload_scan import probe_duration_sec

    work_mp3 = mp3
    if mp3.stem.endswith("_raw"):
        mastered = mp3.with_name(f"{slug}.mp3")
        master_mp3(mp3, mastered)
        work_mp3 = mastered
        print(f"MASTERED: {mastered}")

    duration = int(round(probe_duration_sec(work_mp3)))
    if not args.skip_humanize:
        variation = master_variation_for(row.name)
        humanized = work_mp3.with_name(f"{work_mp3.stem}_human.mp3")
        humanize_mp3(
            work_mp3,
            humanized,
            style="distribute",
            variation=variation,
            duration_sec=duration,
            bpm=row.bpm or 128,
            vocal_overlay=args.vocal_overlay,
        )
        humanized.replace(work_mp3)
        print(f"HUMANIZED: {work_mp3}")

    if args.skip_scan:
        return

    report = verify_for_upload(work_mp3, prepare=True)
    print(
        f"VERIFY: {'PASS' if report.verified else 'FAIL'}"
        + (
            f" AI={report.ai_detections[0].ai_probability:.1%}"
            if report.ai_detections
            else ""
        )
    )
    if not report.verified:
        raise SystemExit(1)

    post_process_delivery(
        work_mp3,
        row,
        duration,
        humanize=False,
        scan_upload=True,
        vocal_overlay=None,
    )


if __name__ == "__main__":
    main()
