"""Mass-batch Indian (and other) names: raw generate first, deliver after approval."""

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
)
from batch_birthday.pipeline_paths import resolve_raw_mp3
from batch_birthday.pipeline_v2 import process_row_v2
from batch_birthday.upload_verify import verify_for_upload
from batch_birthday.video_render import master_mp3

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


def finalize_output_dir(out_dir: Path, slug: str, *, raw_only: bool) -> None:
    """Keep raw+json pending approval, or full deliver set after --deliver."""
    if raw_only:
        keep = {f"{slug}.json", f"{slug}_raw.mp3", f"master/{slug}_raw.mp3"}
    else:
        keep = {f"{slug}.mp3", f"{slug}.json", f"{slug}.youtube.json"}
    for path in out_dir.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(out_dir).as_posix()
        if rel in keep:
            continue
        path.unlink()


def _update_sidecar(
    json_path: Path,
    *,
    name: str,
    variation: object,
    verify_report: object | None,
) -> None:
    """Append batch export metadata to the generation sidecar."""
    meta = json.loads(json_path.read_text(encoding="utf-8"))
    ai_prob = None
    if verify_report and verify_report.ai_detections:
        ai_prob = verify_report.ai_detections[0].ai_probability
    meta["batch"] = {
        "name": name,
        "seed": meta.get("seed"),
        "variation": variation.to_dict() if hasattr(variation, "to_dict") else variation,
        "verified": verify_report.verified if verify_report else None,
        "ai_probability": ai_prob,
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    if verify_report and verify_report.verified:
        meta["approval_status"] = "delivered"
    json_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def deliver_raw(
    raw_mp3: Path,
    *,
    name: str,
    slug: str,
    variation: object,
) -> Path:
    """Master, humanize, and verify an approved raw MP3."""
    out_dir = raw_mp3.parent
    final_mp3 = out_dir / f"{slug}.mp3"
    master_mp3(raw_mp3, final_mp3)
    humanize_mp3(final_mp3, final_mp3, style="distribute", variation=variation)
    report = verify_for_upload(final_mp3, prepare=False)
    ai_prob = report.ai_detections[0].ai_probability if report.ai_detections else None
    print(
        f"VERIFY: {name} → {'PASS' if report.verified else 'FAIL'}"
        + (f" AI={ai_prob:.1%}" if ai_prob is not None else "")
    )
    if not report.verified:
        raise RuntimeError(f"Verify failed for {name}")
    return final_mp3


def process_name(
    name: str,
    *,
    language: str,
    api_base: str,
    api_key: str,
    output_root: Path,
    force: bool,
    deliver: bool,
) -> dict[str, object]:
    """Generate raw birthday song; optionally deliver after approval."""
    slug = slug_for_name(name)
    seed = derive_seed(name, BASE_TEMPLATE_SEED)
    variation = master_variation_for(name)
    out_dir = output_root / slug
    raw_mp3 = resolve_raw_mp3(out_dir, slug)
    final_mp3 = out_dir / f"{slug}.mp3"
    sidecar = out_dir / f"{slug}.json"

    row = BirthdayRow(
        name=name,
        language=language,
        slug=slug,
        bpm=DEFAULT_BPM,
        genre_variant=DEFAULT_GENRE,
        seed=seed,
    )
    duration_sec = genre_duration_sec(DEFAULT_GENRE)

    if not force and raw_mp3.exists() and sidecar.exists() and not deliver:
        print(f"SKIP (raw exists): {name} → {raw_mp3}")
        return {"name": name, "slug": slug, "status": "skipped"}

    if not deliver:
        print(f"BATCH RAW: {name} | seed={seed} | lang={language}")
        process_row_v2(
            row,
            api_base=api_base,
            api_key=api_key,
            output_root=output_root,
            state_file=STATE_FILE,
            force=force,
            raw_only=True,
            append_state_fn=append_state,
            post_process_fn=lambda *a, **k: None,
        )
        finalize_output_dir(out_dir, slug, raw_only=True)
        append_state(STATE_FILE, {"name": name, "slug": slug, "seed": seed, "status": "raw"})
        print(f"RAW DONE: {name} → {raw_mp3}")
        return {"name": name, "slug": slug, "status": "raw", "seed": seed}

    if not raw_mp3.exists():
        raise FileNotFoundError(f"Missing raw MP3 for deliver: {raw_mp3}")

    print(f"BATCH DELIVER: {name} | pitch={variation.pitch_rate}")
    deliver_raw(raw_mp3, name=name, slug=slug, variation=variation)
    report = verify_for_upload(final_mp3, prepare=False)
    ai_prob = report.ai_detections[0].ai_probability if report.ai_detections else None

    if sidecar.exists():
        _update_sidecar(sidecar, name=name, variation=variation, verify_report=report)

    youtube_meta_path = out_dir / f"{slug}.youtube.json"
    youtube_meta_path.write_text(
        json.dumps(upload_metadata(name), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    finalize_output_dir(out_dir, slug, raw_only=False)
    append_state(
        STATE_FILE,
        {"name": name, "slug": slug, "seed": seed, "status": "done", "ai_probability": ai_prob},
    )
    print(f"DELIVERED: {name} → {final_mp3}")
    return {"name": name, "slug": slug, "status": "done", "seed": seed, "ai_probability": ai_prob}


def main() -> None:
    """CLI: mass-generate raw songs; use --deliver after approval."""
    parser = argparse.ArgumentParser(
        description="Mass-batch Happy Birthday songs — raw first, deliver after approval",
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
    parser.add_argument("--language", default="en", help="Vocal language code (en, hi, …)")
    parser.add_argument("--offset", type=int, default=0, help="Skip first N names")
    parser.add_argument("--limit", type=int, default=0, help="Max names (0 = all)")
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--deliver",
        action="store_true",
        help="Humanize + verify approved raw MP3s (no ACE-Step regen)",
    )
    args = parser.parse_args()

    names = load_names(args.names)
    if args.offset:
        names = names[args.offset :]
    if args.limit > 0:
        names = names[: args.limit]

    if not names:
        raise SystemExit(f"No names found in {args.names}")

    if not args.deliver:
        ensure_llm_ready(args.api_base, args.api_key)
    print(f"MASS BATCH: {len(names)} names from {args.names.name} ({'deliver' if args.deliver else 'raw'})")

    results: list[dict[str, object]] = []
    for name in names:
        results.append(
            process_name(
                name,
                language=args.language,
                api_base=args.api_base,
                api_key=args.api_key,
                output_root=args.output,
                force=args.force,
                deliver=args.deliver,
            )
        )

    done = sum(1 for r in results if r.get("status") in ("done", "raw"))
    print(f"MASS BATCH COMPLETE: {done}/{len(names)} succeeded")


if __name__ == "__main__":
    main()
