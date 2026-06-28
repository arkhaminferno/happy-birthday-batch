"""Track which birthday songs are generated and uploaded per platform."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
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
    "youtube",
    "instagram",
    "facebook",
    "notes",
    "updated_at",
)

UPLOAD_PLATFORMS = ("youtube", "instagram", "facebook")


@dataclass(frozen=True)
class ReleaseSummary:
    """Aggregate counts for a release-status report."""

    total: int
    mp3_ready: int
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


def load_rows(path: Path = RELEASE_STATUS_CSV) -> list[dict[str, str]]:
    """Load release rows from CSV."""
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def save_rows(rows: list[dict[str, str]], path: Path = RELEASE_STATUS_CSV) -> None:
    """Persist release rows to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


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
                    "youtube": prior.get("youtube", "false"),
                    "instagram": prior.get("instagram", "false"),
                    "facebook": prior.get("facebook", "false"),
                    "notes": prior.get("notes", ""),
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
    """Refresh mp3_ready flags by scanning output folders."""
    rows = load_rows(path)
    if not rows:
        rows = init_from_world_names(path=path)
    for row in rows:
        slug = row["slug"]
        ready = (output_root / slug / f"{slug}.mp3").is_file()
        row["mp3_ready"] = _bool_str(ready)
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
    if platform not in UPLOAD_PLATFORMS:
        raise ValueError(f"Unknown platform {platform!r}; use one of {UPLOAD_PLATFORMS}")

    rows = load_rows(path)
    if not rows:
        rows = init_from_world_names(path=path)

    match = next((row for row in rows if row["slug"] == slug), None)
    if match is None:
        raise KeyError(f"Unknown slug: {slug}")

    match[platform] = _bool_str(uploaded)
    if notes:
        match["notes"] = notes.strip()
    match["updated_at"] = _now_iso()
    save_rows(rows, path)
    return match


def summarize(rows: list[dict[str, str]]) -> ReleaseSummary:
    """Compute dashboard counts."""
    total = len(rows)
    mp3_ready = sum(1 for row in rows if _parse_bool(row.get("mp3_ready", "")))
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
) -> list[dict[str, str]]:
    """Filter rows for CLI list views."""
    country_key = country.strip().lower()
    platform = pending_platform.strip().lower()
    result = rows
    if country_key:
        result = [row for row in result if row.get("country", "").lower() == country_key]
    if mp3_only:
        result = [row for row in result if _parse_bool(row.get("mp3_ready", ""))]
    if platform:
        if platform not in UPLOAD_PLATFORMS:
            raise ValueError(f"Unknown platform {platform!r}")
        result = [row for row in result if not _parse_bool(row.get(platform, ""))]
    return result
