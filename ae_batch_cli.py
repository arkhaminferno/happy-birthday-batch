"""CLI: batch-render CelebrateVibes AE YouTube videos from output MP3s."""

from __future__ import annotations

import argparse
import sys

from batch_birthday.ae_config import TEMPLATE_AEP
from batch_birthday.ae_render_job import build_render_job, write_render_job
from batch_birthday.ae_launcher import SMOKE_PROJECT, write_smoke_script
from batch_birthday.ae_runner import prepare_project, render_job, run_active_script
from batch_birthday.ae_video_metadata import embed_video_metadata, load_youtube_meta
from batch_birthday.orchestrator import BATCH_ROOT
from batch_birthday.release_tracker import OUTPUT_ROOT, load_rows, sync_mp3_ready


def _row_from_output_folder(slug: str) -> dict[str, str] | None:
    """Build a minimal queue row when slug exists on disk but not in the tracker."""
    folder = OUTPUT_ROOT / slug
    mp3_path = folder / f"{slug}.mp3"
    if not mp3_path.is_file():
        return None
    youtube = load_youtube_meta(folder, slug)
    return {
        "slug": slug,
        "name": str(youtube.get("name") or slug),
    }


def _load_queue(
    *,
    slug: str,
    offset: int,
    limit: int,
    force: bool,
) -> list[dict[str, str]]:
    """Return release rows that need AE export."""
    rows = load_rows()
    if slug.strip():
        slug_value = slug.strip()
        rows = [row for row in rows if row["slug"] == slug_value]
        if not rows:
            fallback = _row_from_output_folder(slug_value)
            if fallback is not None:
                rows = [fallback]
    else:
        rows = [
            row
            for row in rows
            if row.get("mp3_ready") == "true" and (force or row.get("video_ready") != "true")
        ]
    if offset:
        rows = rows[offset:]
    if limit > 0:
        rows = rows[:limit]
    return rows


def main() -> None:
    """Batch AE render entrypoint."""
    parser = argparse.ArgumentParser(
        description="Batch render CelebrateVibes AE template videos (1080p YouTube)",
    )
    parser.add_argument("--slug", default="", help="Render one slug only")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--force", action="store_true", help="Re-render even if MP4 exists")
    parser.add_argument("--inspect", action="store_true", help="List comps/layers in template")
    parser.add_argument("--smoke", action="store_true", help="Test AE scripting without template")
    parser.add_argument("--dry-run", action="store_true", help="Write job JSON only, no AE")
    parser.add_argument("--prep-only", action="store_true", help="Run JSX prep but skip aerender")
    parser.add_argument("--cooldown", type=int, default=5, help="Seconds between renders")
    args = parser.parse_args()

    if not TEMPLATE_AEP.is_file():
        raise SystemExit(f"Template not found: {TEMPLATE_AEP}")

    if args.smoke:
        if SMOKE_PROJECT.exists():
            SMOKE_PROJECT.unlink()
        write_smoke_script()
        run_active_script(expect_project=SMOKE_PROJECT, timeout_sec=300)
        print("SMOKE TEST PASSED")
        return

    if args.inspect:
        raise SystemExit("Use --smoke first, then --slug for one render.")

    rows = _load_queue(slug=args.slug, offset=args.offset, limit=args.limit, force=args.force)
    if not rows:
        print("No songs queued for AE render.")
        return

    print(f"AE BATCH: {len(rows)} video(s) queued")
    done = 0
    for row in rows:
        slug = row["slug"]
        name = row["name"]
        folder = OUTPUT_ROOT / slug
        output_mp4 = folder / f"{slug}-youtube.mp4"
        if not args.force and output_mp4.is_file():
            print(f"SKIP (video exists): {name} → {output_mp4}")
            continue

        youtube = load_youtube_meta(folder, slug)
        title = str(youtube.get("title") or f"Happy Birthday {name}")
        artist = str(youtube.get("artist") or "Birthday Party Mix")
        display_name = str(youtube.get("display_name") or "").strip()
        job = build_render_job(
            slug=slug,
            name=name,
            title=title,
            artist=artist,
            display_name=display_name,
        )

        print(
            f"RENDER: {name} | theme={job.variation.theme_name} "
            f"({job.variation.theme_hue}°) | {job.duration_sec:.1f}s"
        )
        if args.dry_run:
            write_render_job(job)
            print(f"DRY RUN job: {job.job_json_path}")
            continue

        if args.prep_only:
            prepare_project(job)
            print(f"PREP DONE: {job.project_path}")
            continue

        raw_mp4 = render_job(job, cooldown_sec=args.cooldown)
        description = str(youtube.get("description") or "")
        embed_video_metadata(
            raw_mp4,
            raw_mp4,
            title=title,
            artist=artist,
            description=description,
        )
        done += 1
        print(f"VIDEO READY: {name} → {raw_mp4}")

    if done:
        sync_mp3_ready()
    print(f"AE BATCH COMPLETE: {done}/{len(rows)} rendered")


if __name__ == "__main__":
    main()
    sys.exit(0)
