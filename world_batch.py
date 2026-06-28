"""Mass-batch world names: upload-ready delivery and per-song variation."""

from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from batch_birthday.ai_stealth import STEALTH_AI_TARGET, harden_for_upload
from batch_birthday.brand import upload_metadata
from batch_birthday.batch_variation import (
    BASE_TEMPLATE_SEED,
    DEFAULT_GENRE,
    derive_seed,
    master_variation_for,
    slug_for_name,
    song_variation_for,
)
from batch_birthday.name_pronunciation import resolve_pronunciation
from batch_birthday.humanize_audio import humanize_mp3
from batch_birthday.orchestrator import (
    BATCH_ROOT,
    BirthdayRow,
    DEFAULT_API_BASE,
    append_state,
    ensure_llm_ready,
    resolve_slug,
)
from batch_birthday.pipeline_paths import resolve_raw_mp3
from batch_birthday.pipeline_v2 import process_row_v2
from batch_birthday.upload_scan import prepare_upload_copy
from batch_birthday.upload_verify import verify_for_upload
from batch_birthday.video_render import master_mp3

DEFAULT_CSV = BATCH_ROOT / "input" / "world_names.csv"
STATE_FILE = BATCH_ROOT / "state" / "world_batch.jsonl"

PHASE_ORDER = ("India", "United States", "Russia", "China")
# One song at a time — safest for M4 Pro 24GB with local ACE-Step inference.
DEFAULT_COOLDOWN_SEC = 20


def load_csv_rows(path: Path, *, country: str = "") -> list[BirthdayRow]:
    """Load enabled rows from the world names CSV."""
    rows: list[BirthdayRow] = []
    country_filter = country.strip().lower()
    with path.open(newline="", encoding="utf-8") as handle:
        for item in csv.DictReader(handle):
            if item.get("enabled", "true").lower() not in ("1", "true", "yes"):
                continue
            if item.get("locked", "").lower() in ("1", "true", "yes"):
                continue
            row_country = (item.get("country") or "").strip()
            if country_filter and row_country.lower() != country_filter:
                continue
            name = item["name"].strip()
            genre = (item.get("genre_variant") or DEFAULT_GENRE).strip()
            variation = song_variation_for(name, row_country)
            pron = resolve_pronunciation(
                name,
                row_country,
                (item.get("pronunciation") or "").strip(),
            )
            slug = (item.get("slug") or "").strip() or slug_for_name(name, row_country)
            if not slug.endswith("birthday-edm-party"):
                slug = resolve_slug(name, slug, genre)
            seed = (item.get("seed") or "").strip() or derive_seed(
                f"{row_country}:{name}",
                BASE_TEMPLATE_SEED,
            )
            rows.append(
                BirthdayRow(
                    name=name,
                    language=(item.get("language") or "en").strip().lower(),
                    slug=slug,
                    bpm=int(item.get("bpm") or variation.bpm),
                    genre_variant=genre,
                    seed=seed,
                    country=row_country,
                    gender=(item.get("gender") or "").strip(),
                    pronunciation=pron.phonetic,
                )
            )
    return rows


def finalize_upload_dir(out_dir: Path, slug: str) -> None:
    """Keep only the upload MP3, sidecar JSON, and YouTube metadata."""
    keep = {f"{slug}.mp3", f"{slug}.json", f"{slug}.youtube.json"}
    for path in out_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.name in keep:
            continue
        path.unlink()
    for path in list(out_dir.iterdir()):
        if path.is_dir():
            for child in path.rglob("*"):
                if child.is_file():
                    child.unlink()
            path.rmdir()


def deliver_upload_ready(
    raw_mp3: Path,
    *,
    row: BirthdayRow,
    output_root: Path,
) -> Path:
    """Humanize, embed clean tags, and verify one upload-ready MP3."""
    out_dir = output_root / row.slug
    final_mp3 = out_dir / f"{row.slug}.mp3"
    work_mp3 = out_dir / f"{row.slug}_work.mp3"
    human_mp3 = out_dir / f"{row.slug}_human.mp3"
    stealth_mp3 = out_dir / f"{row.slug}_stealth.mp3"
    youtube = upload_metadata(row.name, country=row.country)
    variation = master_variation_for(row.name)

    master_mp3(raw_mp3, work_mp3)
    humanize_mp3(
        work_mp3,
        human_mp3,
        style="distribute",
        variation=variation,
        bpm=row.bpm,
    )
    _, stealth_rate, _ai_prob = harden_for_upload(
        human_mp3,
        stealth_mp3,
        name=row.name,
        target_ai=STEALTH_AI_TARGET,
    )
    prepare_upload_copy(
        stealth_mp3,
        final_mp3,
        title=str(youtube["title"]),
        artist=str(youtube["artist"]),
    )
    for temp in (work_mp3, human_mp3, stealth_mp3):
        if temp.exists():
            temp.unlink()

    report = verify_for_upload(final_mp3, prepare=False)
    ai_prob = report.ai_detections[0].ai_probability if report.ai_detections else None
    print(
        f"VERIFY: {row.name} → {'PASS' if report.verified else 'FAIL'}"
        + (f" AI={ai_prob:.1%}" if ai_prob is not None else "")
        + f" stealth_rate={stealth_rate}"
    )
    if not report.verified:
        ai_prob = report.ai_detections[0].ai_probability if report.ai_detections else None
        print(f"VERIFY WARN: {row.name} — continuing with best-effort upload copy")
        if ai_prob is not None:
            print(f"  AI probability: {ai_prob:.1%}")
        for check in report.checks:
            if check.status == "fail":
                print(f"  FAIL {check.check_id}: {check.message}")
    return final_mp3


def process_row(
    row: BirthdayRow,
    *,
    api_base: str,
    api_key: str,
    output_root: Path,
    force: bool,
    upload_ready: bool,
) -> dict[str, object]:
    """Generate one song; optionally finish as a single upload-ready MP3."""
    out_dir = output_root / row.slug
    final_mp3 = out_dir / f"{row.slug}.mp3"
    sidecar = out_dir / f"{row.slug}.json"
    youtube_path = out_dir / f"{row.slug}.youtube.json"

    if not force and upload_ready and final_mp3.exists() and sidecar.exists():
        print(f"SKIP (upload exists): {row.name} → {final_mp3}")
        return {"name": row.name, "slug": row.slug, "status": "skipped"}

    print(
        f"WORLD BATCH: {row.name} ({row.country}) | bpm={row.bpm} | seed={row.seed}"
    )
    process_row_v2(
        row,
        api_base=api_base,
        api_key=api_key,
        output_root=output_root,
        state_file=STATE_FILE,
        force=force,
        raw_only=not upload_ready,
        humanize=False,
        scan_upload=False,
        append_state_fn=append_state,
        post_process_fn=lambda *args, **kwargs: None,
    )

    if not upload_ready:
        raw_mp3 = resolve_raw_mp3(out_dir, row.slug)
        print(f"RAW DONE: {row.name} → {raw_mp3}")
        return {"name": row.name, "slug": row.slug, "status": "raw"}

    raw_mp3 = resolve_raw_mp3(out_dir, row.slug)
    final_mp3 = deliver_upload_ready(raw_mp3, row=row, output_root=output_root)
    youtube = upload_metadata(row.name, country=row.country)
    youtube_path.write_text(
        json.dumps(youtube, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    if sidecar.exists():
        meta = json.loads(sidecar.read_text(encoding="utf-8"))
        meta["batch"] = {
            "country": row.country,
            "gender": row.gender,
            "upload_mp3": str(final_mp3),
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }
        meta["approval_status"] = "delivered"
        meta["youtube"] = youtube
        sidecar.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    finalize_upload_dir(out_dir, row.slug)
    append_state(STATE_FILE, {"name": row.name, "slug": row.slug, "status": "done"})
    print(f"UPLOAD READY: {row.name} → {final_mp3}")
    return {"name": row.name, "slug": row.slug, "status": "done", "mp3": str(final_mp3)}


def main() -> None:
    """CLI: generate world batch songs as upload-ready MP3s."""
    parser = argparse.ArgumentParser(
        description="World mass batch — varied party songs, one upload MP3 each",
    )
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--output", type=Path, default=BATCH_ROOT / "output")
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--api-key", default="")
    parser.add_argument(
        "--country",
        default="",
        help="Run one country phase only (e.g. India, United States, Russia, China)",
    )
    parser.add_argument(
        "--phase",
        choices=[p.lower().replace(" ", "-") for p in PHASE_ORDER],
        default="",
        help="Alias for --country (india, united-states, russia, china)",
    )
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--cooldown",
        type=int,
        default=DEFAULT_COOLDOWN_SEC,
        help="Seconds to pause between songs (memory/thermal recovery)",
    )
    parser.add_argument(
        "--raw-only",
        action="store_true",
        help="Generate raw review files only (skip humanize/verify/cleanup)",
    )
    args = parser.parse_args()

    country = args.country.strip()
    if not country and args.phase:
        phase_map = {
            "india": "India",
            "united-states": "United States",
            "russia": "Russia",
            "china": "China",
        }
        country = phase_map.get(args.phase, args.phase)

    rows = load_csv_rows(args.csv, country=country)
    if args.offset:
        rows = rows[args.offset :]
    if args.limit > 0:
        rows = rows[: args.limit]
    if not rows:
        label = country or "all countries"
        raise SystemExit(f"No enabled rows for {label} in {args.csv}")

    ensure_llm_ready(args.api_base, args.api_key)
    upload_ready = not args.raw_only
    print(
        f"WORLD BATCH: {len(rows)} names | country={country or 'ALL'} | "
        f"mode={'upload-ready' if upload_ready else 'raw-only'} | "
        f"cooldown={args.cooldown}s"
    )

    results: list[dict[str, object]] = []
    for index, row in enumerate(rows):
        if index > 0 and args.cooldown > 0:
            print(f"COOLDOWN: {args.cooldown}s before next song…")
            time.sleep(args.cooldown)
        results.append(
            process_row(
                row,
                api_base=args.api_base,
                api_key=args.api_key,
                output_root=args.output,
                force=args.force,
                upload_ready=upload_ready,
            )
        )

    done = sum(1 for item in results if item.get("status") in ("done", "raw"))
    print(f"WORLD BATCH COMPLETE: {done}/{len(rows)} succeeded ({country or 'ALL'})")


if __name__ == "__main__":
    main()
