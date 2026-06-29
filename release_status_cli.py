"""CLI for release / upload tracking."""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from batch_birthday.orchestrator import BATCH_ROOT
from batch_birthday.release_tracker import (
    MARKABLE_FLAGS,
    UPLOAD_PLATFORMS,
    export_mp3s,
    filter_rows,
    init_from_world_names,
    load_rows,
    mark_uploaded,
    paths_for_slug,
    summarize,
    sync_mp3_ready,
)


def _print_summary() -> None:
    """Print dashboard counts."""
    rows = load_rows()
    if not rows:
        print("No release_status.csv yet — run: python -m batch_birthday release-status --init")
        return
    stats = summarize(rows)
    print("CelebrateVibes release tracker")
    print(f"  Songs in catalog:     {stats.total}")
    print(f"  MP3 ready (local):    {stats.mp3_ready}/{stats.total}")
    print(f"  Video exported:       {stats.video_ready}/{stats.total}")
    print(f"  YouTube uploaded:     {stats.youtube}/{stats.total}")
    print(f"  Instagram uploaded:   {stats.instagram}/{stats.total}")
    print(f"  Facebook uploaded:    {stats.facebook}/{stats.total}")
    print(f"  All 3 platforms done: {stats.fully_published}/{stats.total}")


def _print_table(rows: list[dict[str, str]]) -> None:
    """Print a compact status table."""
    if not rows:
        print("No matching rows.")
        return
    header = (
        f"{'NAME':<14} {'COUNTRY':<14} {'MP3':<5} {'VID':<4} {'YT':<4} "
        f"{'IG':<4} {'FB':<4} {'GENERATED':<12} SLUG"
    )
    print(header)
    print("-" * len(header))
    for row in rows:
        generated = (row.get("generated_at") or "")[:10]
        print(
            f"{row['name']:<14} {row['country']:<14} "
            f"{'yes' if row.get('mp3_ready') == 'true' else 'no':<5} "
            f"{'yes' if row.get('video_ready') == 'true' else 'no':<4} "
            f"{'yes' if row.get('youtube') == 'true' else 'no':<4} "
            f"{'yes' if row.get('instagram') == 'true' else 'no':<4} "
            f"{'yes' if row.get('facebook') == 'true' else 'no':<4} "
            f"{generated:<12} "
            f"{row['slug']}"
        )


def main() -> None:
    """CLI entry: init, sync, mark uploads, list pending."""
    parser = argparse.ArgumentParser(
        description="Track generated songs and platform upload status",
    )
    parser.add_argument("--init", action="store_true", help="Create CSV from world_names.csv")
    parser.add_argument("--sync", action="store_true", help="Refresh mp3_ready from output/")
    parser.add_argument(
        "--mark",
        nargs=2,
        metavar=("PLATFORM", "SLUG"),
        help=f"Mark flag: one of {MARKABLE_FLAGS}",
    )
    parser.add_argument("--unmark", nargs=2, metavar=("PLATFORM", "SLUG"), help="Clear upload flag")
    parser.add_argument("--note", default="", help="Optional note with --mark")
    parser.add_argument("--country", default="", help="Filter list by country")
    parser.add_argument(
        "--pending",
        default="",
        choices=(*MARKABLE_FLAGS, ""),
        help="List rows missing this flag (video, youtube, instagram, facebook)",
    )
    parser.add_argument("--needs-video", action="store_true", help="MP3 ready, no AE export yet")
    parser.add_argument(
        "--today",
        action="store_true",
        help="Only songs generated today (UTC date from generated_at)",
    )
    parser.add_argument(
        "--since",
        metavar="YYYY-MM-DD",
        default="",
        help="Only songs generated on this date",
    )
    parser.add_argument(
        "--export-mp3",
        nargs="?",
        const=str(BATCH_ROOT / "export" / "mp3"),
        metavar="DIR",
        help="Copy all ready MP3s to one folder (default: batch_birthday/export/mp3)",
    )
    parser.add_argument(
        "--symlink",
        action="store_true",
        help="With --export-mp3, symlink instead of copy",
    )
    parser.add_argument("--show", metavar="SLUG", default="", help="Print paths for After Effects import")
    parser.add_argument("--mp3-only", action="store_true", help="Only rows with local MP3")
    parser.add_argument("--list", action="store_true", help="Print full table (default if filters set)")
    args = parser.parse_args()

    if args.init:
        init_from_world_names()
        sync_mp3_ready()
        print("Initialized batch_birthday/state/release_status.csv")
        _print_summary()
        return

    if args.sync:
        sync_mp3_ready()
        print("Synced mp3_ready + video_ready + generated_at from output/")
        _print_summary()
        return

    if args.export_mp3 is not None:
        sync_mp3_ready()
        dest = Path(args.export_mp3)
        manifest, count = export_mp3s(dest, use_symlinks=args.symlink)
        print(f"Exported {count} MP3s → {dest}")
        print(f"Manifest: {manifest}")
        print("Upload this folder to Google Drive / Dropbox / external drive.")
        return

    if args.show:
        paths = paths_for_slug(args.show.strip())
        print(f"After Effects workflow — {args.show}")
        print(f"  Folder:         {paths['folder']}")
        print(f"  Import audio:   {paths['mp3']}")
        print(f"  Title/metadata: {paths['youtube_json'] or paths['lyrics_json']}")
        print(f"  Export YouTube: {paths['export_youtube']}")
        print(f"  Export Reel:    {paths['export_reel']}")
        return

    if args.mark:
        platform, slug = args.mark
        mark_uploaded(slug, platform, uploaded=True, notes=args.note)
        print(f"Marked {slug} → {platform}=uploaded")
        return

    if args.unmark:
        platform, slug = args.unmark
        mark_uploaded(slug, platform, uploaded=False)
        print(f"Cleared {slug} → {platform}")
        return

    rows = load_rows()
    if not rows:
        init_from_world_names()
        sync_mp3_ready()
        rows = load_rows()

    generated_on: date | None = None
    if args.today:
        generated_on = datetime.now(timezone.utc).date()
    elif args.since.strip():
        generated_on = date.fromisoformat(args.since.strip())

    filtered = filter_rows(
        rows,
        country=args.country,
        pending_platform=args.pending,
        mp3_only=args.mp3_only,
        needs_video=args.needs_video,
        generated_on=generated_on,
    )

    if (
        args.list
        or args.country
        or args.pending
        or args.mp3_only
        or args.needs_video
        or args.today
        or args.since.strip()
    ):
        _print_table(filtered)
        print()
        _print_summary()
        return

    _print_summary()


if __name__ == "__main__":
    main()
    sys.exit(0)
