"""Mass-batch Indian (and other) names: generate, vary fingerprint, verify, export."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from batch_birthday.brand import upload_metadata
from batch_birthday.batch_variation import (
    BASE_TEMPLATE_SEED,
    DEFAULT_BPM,
    DEFAULT_GENRE,
    derive_seed,
    master_variation_for,
    slug_for_name,
)
from batch_birthday.humanize_audio import humanize_mp3
from batch_birthday.orchestrator import (
    BATCH_ROOT,
    BirthdayRow,
    DEFAULT_API_BASE,
    append_state,
    ensure_llm_ready,
    genre_duration_sec,
    process_row,
)
from batch_birthday.upload_verify import verify_for_upload

DEFAULT_NAMES_FILE = BATCH_ROOT / "input" / "indian_names.txt"
STATE_FILE = BATCH_ROOT / "state" / "mass_batch.jsonl"


def load_names(path: Path) -> list[str]:
    """Load one display name per non-empty, non-comment line."""
    names: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        item = line.strip()
        if not item or item.startswith("#"):
            continue
        names.append(item)
    return names


def finalize_output_dir(out_dir: Path, slug: str) -> None:
    """Keep only upload artifacts: mp3, sidecar json, and youtube metadata."""
    keep = {f"{slug}.mp3", f"{slug}.json", f"{slug}.youtube.json"}
    for path in out_dir.iterdir():
        if path.name in keep:
            continue
        if path.is_file():
            path.unlink()


def _update_sidecar(
    json_path: Path,
    *,
    name: str,
    variation: object,
    verify_report: object,
) -> None:
    """Append batch export metadata to the generation sidecar."""
    meta = json.loads(json_path.read_text(encoding="utf-8"))
    ai_prob = None
    if verify_report.ai_detections:
        ai_prob = verify_report.ai_detections[0].ai_probability
    meta["batch"] = {
        "name": name,
        "seed": meta.get("seed"),
        "variation": variation.to_dict() if hasattr(variation, "to_dict") else variation,
        "verified": verify_report.verified,
        "ai_probability": ai_prob,
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    json_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def process_name(
    name: str,
    *,
    api_base: str,
    api_key: str,
    output_root: Path,
    force: bool,
    skip_verify: bool,
) -> dict[str, object]:
    """Generate one birthday song for *name* with unique seed + mastering variation."""
    slug = slug_for_name(name)
    seed = derive_seed(name, BASE_TEMPLATE_SEED)
    variation = master_variation_for(name)
    out_dir = output_root / slug
    final_mp3 = out_dir / f"{slug}.mp3"
    sidecar = out_dir / f"{slug}.json"

    row = BirthdayRow(
        name=name,
        language="en",
        slug=slug,
        bpm=DEFAULT_BPM,
        genre_variant=DEFAULT_GENRE,
        seed=seed,
    )
    duration_sec = genre_duration_sec(DEFAULT_GENRE)

    if not force and final_mp3.exists() and sidecar.exists():
        print(f"SKIP (exists): {name} → {final_mp3}")
        return {"name": name, "slug": slug, "status": "skipped"}

    print(f"BATCH: {name} | seed={seed} | pitch={variation.pitch_rate}")
    raw_mp3 = process_row(
        row,
        api_base=api_base,
        api_key=api_key,
        output_root=output_root,
        state_file=STATE_FILE,
        video_bg=None,
        skip_video=True,
        force=force,
        use_cover=False,
        duration_sec=duration_sec,
        humanize=False,
        scan_upload=False,
    )

    hardened = out_dir / f"{slug}_hardened.mp3"
    humanize_mp3(raw_mp3, hardened, style="distribute", variation=variation)
    hardened.replace(final_mp3)

    report = verify_for_upload(final_mp3, prepare=False)
    ai_prob = report.ai_detections[0].ai_probability if report.ai_detections else None
    if not skip_verify:
        print(
            f"VERIFY: {name} → {'PASS' if report.verified else 'FAIL'}"
            + (f" AI={ai_prob:.1%}" if ai_prob is not None else "")
        )
        if not report.verified:
            append_state(STATE_FILE, {"name": name, "slug": slug, "status": "verify_failed"})
            return {
                "name": name,
                "slug": slug,
                "status": "verify_failed",
                "ai_probability": ai_prob,
            }

    if sidecar.exists():
        _update_sidecar(sidecar, name=name, variation=variation, verify_report=report)

    youtube_meta_path = out_dir / f"{slug}.youtube.json"
    youtube_meta_path.write_text(
        json.dumps(upload_metadata(name), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    finalize_output_dir(out_dir, slug)
    append_state(
        STATE_FILE,
        {"name": name, "slug": slug, "seed": seed, "status": "done", "ai_probability": ai_prob},
    )
    print(f"DONE: {name} → {final_mp3}")
    return {"name": name, "slug": slug, "status": "done", "seed": seed, "ai_probability": ai_prob}


def main() -> None:
    """CLI: mass-generate birthday songs from a names list."""
    parser = argparse.ArgumentParser(
        description="Mass-batch Happy Birthday songs with per-name fingerprint variation",
    )
    parser.add_argument(
        "--names",
        type=Path,
        default=DEFAULT_NAMES_FILE,
        help="Text file: one name per line",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=BATCH_ROOT / "output",
    )
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--api-key", default="")
    parser.add_argument("--offset", type=int, default=0, help="Skip first N names")
    parser.add_argument("--limit", type=int, default=0, help="Max names (0 = all)")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--skip-verify", action="store_true")
    args = parser.parse_args()

    names = load_names(args.names)
    if args.offset:
        names = names[args.offset :]
    if args.limit > 0:
        names = names[: args.limit]

    if not names:
        raise SystemExit(f"No names found in {args.names}")

    ensure_llm_ready(args.api_base, args.api_key)
    print(f"MASS BATCH: {len(names)} names from {args.names.name}")

    results: list[dict[str, object]] = []
    for name in names:
        results.append(
            process_name(
                name,
                api_base=args.api_base,
                api_key=args.api_key,
                output_root=args.output,
                force=args.force,
                skip_verify=args.skip_verify,
            )
        )

    done = sum(1 for r in results if r.get("status") == "done")
    print(f"MASS BATCH COMPLETE: {done}/{len(names)} succeeded")


if __name__ == "__main__":
    main()
