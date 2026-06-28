"""CLI for release / upload tracking."""

from __future__ import annotations

import argparse
import sys

from batch_birthday.release_tracker import (
    UPLOAD_PLATFORMS,
    filter_rows,
    init_from_world_names,
    load_rows,
    mark_uploaded,
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
    print(f"  YouTube uploaded:     {stats.youtube}/{stats.total}")
    print(f"  Instagram uploaded:   {stats.instagram}/{stats.total}")
    print(f"  Facebook uploaded:    {stats.facebook}/{stats.total}")
    print(f"  All 3 platforms done: {stats.fully_published}/{stats.total}")


def _print_table(rows: list[dict[str, str]]) -> None:
    """Print a compact status table."""
    if not rows:
        print("No matching rows.")
        return
    header = f"{'NAME':<14} {'COUNTRY':<14} {'MP3':<5} {'YT':<4} {'IG':<4} {'FB':<4} SLUG"
    print(header)
    print("-" * len(header))
    for row in rows:
        print(
            f"{row['name']:<14} {row['country']:<14} "
            f"{'yes' if row.get('mp3_ready') == 'true' else 'no':<5} "
            f"{'yes' if row.get('youtube') == 'true' else 'no':<4} "
            f"{'yes' if row.get('instagram') == 'true' else 'no':<4} "
            f"{'yes' if row.get('facebook') == 'true' else 'no':<4} "
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
        help=f"Mark uploaded: platform one of {UPLOAD_PLATFORMS}",
    )
    parser.add_argument("--unmark", nargs=2, metavar=("PLATFORM", "SLUG"), help="Clear upload flag")
    parser.add_argument("--note", default="", help="Optional note with --mark")
    parser.add_argument("--country", default="", help="Filter list by country")
    parser.add_argument(
        "--pending",
        default="",
        choices=(*UPLOAD_PLATFORMS, ""),
        help="List songs not yet uploaded to this platform",
    )
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
        print("Synced mp3_ready flags from output/")
        _print_summary()
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

    filtered = filter_rows(
        rows,
        country=args.country,
        pending_platform=args.pending,
        mp3_only=args.mp3_only,
    )

    if args.list or args.country or args.pending or args.mp3_only:
        _print_table(filtered)
        print()
        _print_summary()
        return

    _print_summary()


if __name__ == "__main__":
    main()
    sys.exit(0)
