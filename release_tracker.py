"""Track which birthday songs are generated and uploaded per platform."""

from __future__ import annotations

import csv
import json
import shutil
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from batch_birthday.orchestrator import BATCH_ROOT

RELEASE_STATUS_CSV = BATCH_ROOT / "state" / "release_status.csv"
WORLD_NAMES_CSV = BATCH_ROOT / "input" / "world_names.csv"
OUTPUT_ROOT = BATCH_ROOT / "output"

FIELDNAMES = (
    "slug",
    "name",
    "country",
    "language",
    "gender",
    "locked",
    "mp3_ready",
    "video_ready",
    "youtube",
    "instagram",
    "facebook",
    "notes",
    "generated_at",
    "updated_at",
)

UPLOAD_PLATFORMS = ("youtube", "instagram", "facebook")
MARKABLE_FLAGS = ("video", *UPLOAD_PLATFORMS)


@dataclass(frozen=True)
class ReleaseSummary:
    """Aggregate counts for a release-status report."""

    total: int
    mp3_ready: int
    video_ready: int
    youtube: int
    instagram: int
    facebook: int
    fully_published: int


def _now_iso() -> str:
    """Return UTC timestamp for CSV updates."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _bool_str(value: bool) -> str:
    """Serialize booleans for CSV storage."""
    return "true" if value else "false"


def _parse_bool(raw: str) -> bool:
    """Parse CSV boolean fields."""
    return str(raw or "").strip().lower() in ("1", "true", "yes", "y")


def _upload_mp3(slug: str) -> Path:
    """Return expected upload-ready MP3 path for a slug."""
    return OUTPUT_ROOT / slug / f"{slug}.mp3"


def _video_mp4(slug: str) -> Path:
    """Return preferred YouTube export path (save AE export here)."""
    return OUTPUT_ROOT / slug / f"{slug}-youtube.mp4"


def _reel_mp4(slug: str) -> Path:
    """Return preferred 9:16 Reel export path."""
    return OUTPUT_ROOT / slug / f"{slug}-reel.mp4"


def _sidecar_json(slug: str, output_root: Path = OUTPUT_ROOT) -> Path:
    """Return expected sidecar JSON path for a slug."""
    return output_root / slug / f"{slug}.json"


def _read_generated_at(slug: str, output_root: Path = OUTPUT_ROOT) -> str:
    """Read generation timestamp from sidecar JSON or MP3 mtime."""
    mp3 = output_root / slug / f"{slug}.mp3"
    if not mp3.is_file():
        return ""

    sidecar = _sidecar_json(slug, output_root)
    if sidecar.is_file():
        try:
            meta = json.loads(sidecar.read_text(encoding="utf-8"))
            exported = (meta.get("batch") or {}).get("exported_at", "").strip()
            if exported:
                return exported
        except (json.JSONDecodeError, OSError, TypeError):
            pass

    mtime = datetime.fromtimestamp(mp3.stat().st_mtime, tz=timezone.utc)
    return mtime.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_generated_date(raw: str) -> date | None:
    """Parse generated_at to a calendar date (UTC)."""
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None


def _has_video_export(slug: str, output_root: Path = OUTPUT_ROOT) -> bool:
    """True if any expected AE export exists in the slug folder."""
    folder = output_root / slug
    candidates = (
        folder / f"{slug}-youtube.mp4",
        folder / f"{slug}-reel.mp4",
        folder / f"{slug}.mp4",
    )
    return any(path.is_file() for path in candidates)


def paths_for_slug(slug: str, output_root: Path = OUTPUT_ROOT) -> dict[str, str]:
    """Return absolute paths for manual After Effects import workflow."""
    folder = output_root / slug
    sidecar = folder / f"{slug}.json"
    youtube_meta = folder / f"{slug}.youtube.json"
    return {
        "folder": str(folder.resolve()),
        "mp3": str((folder / f"{slug}.mp3").resolve()),
        "lyrics_json": str(sidecar.resolve()) if sidecar.is_file() else "",
        "youtube_json": str(youtube_meta.resolve()) if youtube_meta.is_file() else "",
        "export_youtube": str((folder / f"{slug}-youtube.mp4").resolve()),
        "export_reel": str((folder / f"{slug}-reel.mp4").resolve()),
    }


def _normalize_row(row: dict[str, str]) -> dict[str, str]:
    """Ensure every CSV row has all columns (handles older files)."""
    normalized = {field: row.get(field, "") for field in FIELDNAMES}
    for flag in ("locked", "mp3_ready", "video_ready", *UPLOAD_PLATFORMS):
        if not normalized.get(flag):
            normalized[flag] = "false"
    return normalized


def load_rows(path: Path = RELEASE_STATUS_CSV) -> list[dict[str, str]]:
    """Load release rows from CSV."""
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [_normalize_row(row) for row in csv.DictReader(handle)]


def save_rows(rows: list[dict[str, str]], path: Path = RELEASE_STATUS_CSV) -> None:
    """Persist release rows to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows([_normalize_row(row) for row in rows])


def init_from_world_names(
    *,
    names_csv: Path = WORLD_NAMES_CSV,
    path: Path = RELEASE_STATUS_CSV,
) -> list[dict[str, str]]:
    """Seed release_status.csv from world_names.csv."""
    existing = {row["slug"]: row for row in load_rows(path)}
    rows: list[dict[str, str]] = []
    with names_csv.open(newline="", encoding="utf-8") as handle:
        for item in csv.DictReader(handle):
            if item.get("enabled", "true").lower() not in ("1", "true", "yes"):
                continue
            slug = item["slug"].strip()
            prior = existing.get(slug, {})
            mp3_ready = _upload_mp3(slug).is_file()
            rows.append(
                {
                    "slug": slug,
                    "name": item["name"].strip(),
                    "country": item.get("country", "").strip(),
                    "language": item.get("language", "en").strip(),
                    "gender": item.get("gender", "").strip(),
                    "locked": item.get("locked", "false").strip().lower() or "false",
                    "mp3_ready": _bool_str(mp3_ready or _parse_bool(prior.get("mp3_ready", ""))),
                    "video_ready": prior.get("video_ready", "false"),
                    "youtube": prior.get("youtube", "false"),
                    "instagram": prior.get("instagram", "false"),
                    "facebook": prior.get("facebook", "false"),
                    "notes": prior.get("notes", ""),
                    "generated_at": prior.get("generated_at", ""),
                    "updated_at": prior.get("updated_at", _now_iso()),
                }
            )
    save_rows(rows, path)
    return rows


def sync_mp3_ready(
    *,
    output_root: Path = OUTPUT_ROOT,
    path: Path = RELEASE_STATUS_CSV,
) -> list[dict[str, str]]:
    """Refresh mp3_ready and video_ready flags by scanning output folders."""
    rows = load_rows(path)
    if not rows:
        rows = init_from_world_names(path=path)
    for row in rows:
        slug = row["slug"]
        mp3_path = output_root / slug / f"{slug}.mp3"
        row["mp3_ready"] = _bool_str(mp3_path.is_file())
        row["video_ready"] = _bool_str(_has_video_export(slug, output_root))
        if mp3_path.is_file():
            row["generated_at"] = _read_generated_at(slug, output_root)
        row["updated_at"] = _now_iso()
    save_rows(rows, path)
    return rows


def mark_uploaded(
    slug: str,
    platform: str,
    *,
    uploaded: bool = True,
    notes: str = "",
    path: Path = RELEASE_STATUS_CSV,
) -> dict[str, str]:
    """Mark one platform upload status for a slug."""
    platform = platform.strip().lower()
    if platform == "video":
        field = "video_ready"
    elif platform in UPLOAD_PLATFORMS:
        field = platform
    else:
        raise ValueError(f"Unknown platform {platform!r}; use one of {MARKABLE_FLAGS}")

    rows = load_rows(path)
    if not rows:
        rows = init_from_world_names(path=path)

    match = next((row for row in rows if row["slug"] == slug), None)
    if match is None:
        raise KeyError(f"Unknown slug: {slug}")

    match[field] = _bool_str(uploaded)
    if notes:
        match["notes"] = notes.strip()
    match["updated_at"] = _now_iso()
    save_rows(rows, path)
    return match


def summarize(rows: list[dict[str, str]]) -> ReleaseSummary:
    """Compute dashboard counts."""
    total = len(rows)
    mp3_ready = sum(1 for row in rows if _parse_bool(row.get("mp3_ready", "")))
    video_ready = sum(1 for row in rows if _parse_bool(row.get("video_ready", "")))
    youtube = sum(1 for row in rows if _parse_bool(row.get("youtube", "")))
    instagram = sum(1 for row in rows if _parse_bool(row.get("instagram", "")))
    facebook = sum(1 for row in rows if _parse_bool(row.get("facebook", "")))
    fully = sum(
        1
        for row in rows
        if all(_parse_bool(row.get(p, "")) for p in UPLOAD_PLATFORMS)
    )
    return ReleaseSummary(
        total=total,
        mp3_ready=mp3_ready,
        video_ready=video_ready,
        youtube=youtube,
        instagram=instagram,
        facebook=facebook,
        fully_published=fully,
    )


def filter_rows(
    rows: list[dict[str, str]],
    *,
    country: str = "",
    pending_platform: str = "",
    mp3_only: bool = False,
    needs_video: bool = False,
    generated_on: date | None = None,
) -> list[dict[str, str]]:
    """Filter rows for CLI list views."""
    country_key = country.strip().lower()
    platform = pending_platform.strip().lower()
    result = rows
    if country_key:
        result = [row for row in result if row.get("country", "").lower() == country_key]
    if mp3_only:
        result = [row for row in result if _parse_bool(row.get("mp3_ready", ""))]
    if needs_video:
        result = [
            row
            for row in result
            if _parse_bool(row.get("mp3_ready", "")) and not _parse_bool(row.get("video_ready", ""))
        ]
    if generated_on is not None:
        result = [
            row
            for row in result
            if _parse_generated_date(row.get("generated_at", "")) == generated_on
        ]
    if platform:
        if platform == "video":
            result = [row for row in result if not _parse_bool(row.get("video_ready", ""))]
        elif platform in UPLOAD_PLATFORMS:
            result = [row for row in result if not _parse_bool(row.get(platform, ""))]
        else:
            raise ValueError(f"Unknown platform {platform!r}")
    return result


def export_mp3s(
    dest_dir: Path,
    *,
    output_root: Path = OUTPUT_ROOT,
    path: Path = RELEASE_STATUS_CSV,
    use_symlinks: bool = False,
) -> tuple[Path, int]:
    """Copy or symlink all upload-ready MP3s into one flat folder for cloud upload.

    Args:
        dest_dir: Destination folder (created if missing).
        output_root: Per-slug output root.
        path: Release tracker CSV path.
        use_symlinks: If True, symlink instead of copy (faster, stays on same disk).

    Returns:
        Tuple of manifest CSV path and number of files exported.
    """
    rows = load_rows(path)
    if not rows:
        rows = init_from_world_names(path=path)
        sync_mp3_ready(output_root=output_root, path=path)
        rows = load_rows(path)

    dest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = dest_dir / "manifest.csv"
    exported = 0
    manifest_rows: list[dict[str, str]] = []

    for row in rows:
        if not _parse_bool(row.get("mp3_ready", "")):
            continue
        slug = row["slug"]
        src = output_root / slug / f"{slug}.mp3"
        if not src.is_file():
            continue
        dest = dest_dir / f"{slug}.mp3"
        if use_symlinks:
            if dest.exists() or dest.is_symlink():
                dest.unlink()
            dest.symlink_to(src.resolve())
        else:
            shutil.copy2(src, dest)
        exported += 1
        manifest_rows.append(
            {
                "slug": slug,
                "name": row.get("name", ""),
                "country": row.get("country", ""),
                "mp3": str(dest.resolve()),
                "generated_at": row.get("generated_at", ""),
            }
        )

    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("slug", "name", "country", "mp3", "generated_at"),
        )
        writer.writeheader()
        writer.writerows(manifest_rows)

    return manifest_path, exported
