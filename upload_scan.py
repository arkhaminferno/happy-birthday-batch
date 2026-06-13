"""Pre-upload scan for batch-generated birthday tracks.

Estimates AI-generation signals and upload readiness. This does NOT guarantee
that any platform will fail to detect AI content — use results for QC and
compliance (including YouTube synthetic-media disclosure when required).
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# Sidecar JSON from batch_birthday/orchestrator.py declares ACE-Step provenance.
ACESTEP_MARKERS = ("acestep", "text2music", "task_id", "dit_model", "lm_model")


@dataclass
class ScanFinding:
    """One check result."""

    check_id: str
    severity: str  # info | warn | fail
    message: str


@dataclass
class UploadScanReport:
    """Aggregated pre-upload scan for one MP3."""

    mp3_path: str
    duration_sec: float
    risk_score: int  # 0 = cleanest, 100 = highest AI/provenance exposure
    ai_provenance: str  # none | likely_acestep | confirmed_acestep
    findings: list[ScanFinding] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSON export."""
        data = asdict(self)
        data["findings"] = [asdict(f) for f in self.findings]
        return data


def probe_duration_sec(path: Path) -> float:
    """Return media duration via ffprobe."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(path),
    ]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return float(json.loads(result.stdout)["format"]["duration"])


def _ffprobe_tags(path: Path) -> dict[str, str]:
    """Read format/stream tags from an audio file."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format_tags",
        "-of",
        "json",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {}
    tags = json.loads(result.stdout).get("format", {}).get("tags", {}) or {}
    return {str(k).lower(): str(v) for k, v in tags.items()}


def _load_sidecar_json(mp3_path: Path) -> dict[str, Any] | None:
    """Load batch_birthday metadata JSON if it sits beside the MP3."""
    sidecar = mp3_path.with_suffix(".json")
    if not sidecar.exists():
        return None
    try:
        return json.loads(sidecar.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _sidecar_ai_provenance(meta: dict[str, Any] | None) -> str:
    """Classify ACE-Step provenance from orchestrator sidecar."""
    if not meta:
        return "none"
    blob = json.dumps(meta).lower()
    if any(marker in blob for marker in ACESTEP_MARKERS):
        return "confirmed_acestep"
    return "none"


def _ebur128_lra(path: Path) -> float | None:
    """Measure loudness range (LRA) — very low LRA can indicate heavy limiting."""
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i",
        str(path),
        "-af",
        "ebur128=framelog=verbose",
        "-f",
        "null",
        "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    for line in result.stderr.splitlines():
        if "LRA:" in line:
            try:
                return float(line.split("LRA:")[1].split("LU")[0].strip())
            except (IndexError, ValueError):
                continue
    return None


def scan_for_upload(mp3_path: Path) -> UploadScanReport:
    """Run pre-upload checks on one mastered MP3.

    Args:
        mp3_path: Path to the final MP3 intended for YouTube.

    Returns:
        UploadScanReport with risk score, findings, and recommendations.
    """
    mp3_path = mp3_path.resolve()
    findings: list[ScanFinding] = []
    recommendations: list[str] = []
    risk = 0

    if not mp3_path.exists():
        findings.append(
            ScanFinding("file_missing", "fail", f"Audio file not found: {mp3_path}")
        )
        return UploadScanReport(str(mp3_path), 0.0, 100, "none", findings, recommendations)

    duration = probe_duration_sec(mp3_path)
    meta = _load_sidecar_json(mp3_path)
    provenance = _sidecar_ai_provenance(meta)

    if provenance == "confirmed_acestep":
        risk += 45
        findings.append(
            ScanFinding(
                "provenance_sidecar",
                "warn",
                "Companion JSON shows ACE-Step / text2music generation metadata.",
            )
        )
        recommendations.append(
            "Do not upload the .json sidecar to YouTube — upload the MP3 only."
        )
        recommendations.append(
            "YouTube may require disclosure for realistic AI-generated or "
            "synthetic audio; check current YouTube synthetic-media policy."
        )

    tags = _ffprobe_tags(mp3_path)
    suspicious_tags = [
        (k, v)
        for k, v in tags.items()
        if any(m in k or m in v.lower() for m in ("acestep", "ai", "generated", "diffusion"))
    ]
    if suspicious_tags:
        risk += 20
        findings.append(
            ScanFinding(
                "metadata_tags",
                "warn",
                f"MP3 embeds generator-like tags: {suspicious_tags[:3]}",
            )
        )
        recommendations.append(
            "Run prepare_upload_copy() to strip embedded tags before upload."
        )

    lra = _ebur128_lra(mp3_path)
    if lra is not None and lra < 4.0:
        risk += 10
        findings.append(
            ScanFinding(
                "loudness_range",
                "info",
                f"Very low loudness range (LRA {lra:.1f} LU) — heavy limiting/mastering.",
            )
        )

    if duration < 60:
        findings.append(
            ScanFinding("duration", "info", f"Short track ({duration:.0f}s) — fine for clips.")
        )
    elif duration > 600:
        risk += 5
        findings.append(
            ScanFinding("duration", "warn", f"Long track ({duration:.0f}s) — verify engagement.")
        )

    if meta and meta.get("task_type") == "text2music":
        findings.append(
            ScanFinding(
                "generation_mode",
                "info",
                f"Generated via text2music ({meta.get('genre_variant', 'unknown')}).",
            )
        )

    if not recommendations:
        recommendations.append(
            "No critical metadata leaks found; still disclose AI assistance if platform requires it."
        )

    recommendations.append(
        "No local scan can guarantee passing third-party AI detectors — treat score as QC only."
    )

    risk = min(100, risk)
    final_provenance = provenance if provenance != "none" else "unknown"
    return UploadScanReport(
        str(mp3_path),
        duration,
        risk,
        final_provenance,
        findings,
        recommendations,
    )


def prepare_upload_copy(
    src_mp3: Path,
    dst_mp3: Path,
    *,
    title: str | None = None,
    artist: str = "Birthday Celebration",
) -> Path:
    """Write a upload-ready MP3 with clean metadata (no ACE-Step sidecar copied).

    Re-encodes lightly and sets only title/artist tags suitable for YouTube.

    Args:
        src_mp3: Source mastered MP3.
        dst_mp3: Destination path for the upload copy.
        title: Optional title tag; defaults to source stem.
        artist: Artist tag for the upload file.

    Returns:
        Path to the prepared MP3.
    """
    src_mp3 = src_mp3.resolve()
    dst_mp3 = dst_mp3.resolve()
    dst_mp3.parent.mkdir(parents=True, exist_ok=True)
    tag_title = title or src_mp3.stem.replace("-", " ").title()

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(src_mp3),
        "-map_metadata",
        "-1",
        "-metadata",
        f"title={tag_title}",
        "-metadata",
        f"artist={artist}",
        "-c:a",
        "libmp3lame",
        "-b:a",
        "192k",
        "-ar",
        "48000",
        str(dst_mp3),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return dst_mp3


def print_report(report: UploadScanReport) -> None:
    """Print a human-readable scan summary to stdout."""
    print(f"SCAN: {report.mp3_path}")
    print(f"  duration: {report.duration_sec:.1f}s")
    print(f"  ai_provenance: {report.ai_provenance}")
    print(f"  risk_score: {report.risk_score}/100 (lower = fewer metadata/leak signals)")
    for item in report.findings:
        print(f"  [{item.severity.upper()}] {item.check_id}: {item.message}")
    print("  recommendations:")
    for rec in report.recommendations:
        print(f"    - {rec}")


def write_report_json(report: UploadScanReport, out_path: Path) -> None:
    """Persist scan report as JSON beside the track."""
    out_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")


def main() -> None:
    """CLI: scan and optionally prepare an upload-ready copy."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Pre-upload AI/provenance scan for batch_birthday MP3s",
    )
    parser.add_argument("mp3", type=Path, help="Path to final MP3")
    parser.add_argument(
        "--prepare",
        action="store_true",
        help="Write *_upload.mp3 with stripped metadata",
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=None,
        help="Write scan report JSON (default: <mp3>.scan.json)",
    )
    args = parser.parse_args()

    report = scan_for_upload(args.mp3)
    print_report(report)

    json_out = args.json or args.mp3.with_suffix(".scan.json")
    write_report_json(report, json_out)
    print(f"REPORT: {json_out}")

    if args.prepare:
        upload_path = args.mp3.with_name(f"{args.mp3.stem}_upload.mp3")
        prepare_upload_copy(args.mp3, upload_path)
        upload_report = scan_for_upload(upload_path)
        print(f"PREPARED: {upload_path} (risk {upload_report.risk_score}/100)")


if __name__ == "__main__":
    main()
