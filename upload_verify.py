"""Unified pre-upload verification gate for batch_birthday tracks.

Combines metadata/provenance scanning (``upload_scan``) with AI-music detectors
(``ai_music_detector``). Returns a pass/fail checklist before YouTube upload.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from batch_birthday.ai_music_detector import (
    DEFAULT_THRESHOLD,
    MIN_AUDIO_SEC,
    AiDetectionResult,
    run_ai_detectors,
)
from batch_birthday.audio_forensics import (
    LRA_FAIL,
    LRA_WARN,
    SPECTRAL_FLATNESS_FAIL,
    SPECTRAL_FLATNESS_WARN,
    STEREO_CORR_FAIL,
    STEREO_CORR_WARN,
    ForensicMetrics,
    analyze_forensics,
)
from batch_birthday.upload_scan import (
    ScanFinding,
    UploadScanReport,
    prepare_upload_copy,
    probe_duration_sec,
    scan_for_upload,
)

DEFAULT_METADATA_RISK_MAX = 35
SUSPICIOUS_NAME_TOKENS = ("acestep", "suno", "udio", "text2music", "ai-generated", "generated-by")


@dataclass
class VerifyCheck:
    """One item in the upload verification checklist."""

    check_id: str
    status: str  # pass | warn | fail | skip
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class UploadVerifyReport:
    """Full pre-upload verification report."""

    source_mp3: str
    upload_mp3: str | None
    verified: bool
    checks: list[VerifyCheck] = field(default_factory=list)
    metadata_scan: UploadScanReport | None = None
    ai_detections: list[AiDetectionResult] = field(default_factory=list)
    forensic_metrics: ForensicMetrics | None = None
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSON export."""
        return {
            "source_mp3": self.source_mp3,
            "upload_mp3": self.upload_mp3,
            "verified": self.verified,
            "checks": [asdict(c) for c in self.checks],
            "metadata_scan": self.metadata_scan.to_dict() if self.metadata_scan else None,
            "ai_detections": [d.to_dict() for d in self.ai_detections],
            "forensic_metrics": self.forensic_metrics.to_dict() if self.forensic_metrics else None,
            "recommendations": self.recommendations,
        }


def _status_from_finding(severity: str) -> str:
    """Map upload_scan severities to verify statuses."""
    if severity == "fail":
        return "fail"
    if severity == "warn":
        return "warn"
    return "pass"


def _behavioral_filename_check(path: Path) -> VerifyCheck:
    """Warn when upload filename exposes generator tooling (behavioral DSP flags)."""
    stem = path.stem.lower()
    hits = [token for token in SUSPICIOUS_NAME_TOKENS if token in stem]
    if hits:
        return VerifyCheck(
            "behavioral_filename",
            "warn",
            f"Filename contains generator-like tokens: {hits}",
            {"tokens": hits},
        )
    return VerifyCheck(
        "behavioral_filename",
        "pass",
        "Upload filename has no obvious AI-tool tokens",
    )


def _forensic_checks(metrics: ForensicMetrics) -> list[VerifyCheck]:
    """Map streaming-platform forensic signals to pass/warn/fail checks."""
    results: list[VerifyCheck] = []

    flat = metrics.spectral_flatness_mean
    if flat >= SPECTRAL_FLATNESS_FAIL:
        flat_status = "fail"
    elif flat >= SPECTRAL_FLATNESS_WARN:
        flat_status = "warn"
    else:
        flat_status = "pass"
    results.append(
        VerifyCheck(
            "spectral_flatness",
            flat_status,
            f"Spectral flatness {flat:.3f} — lower is more human-like (warn ≥ {SPECTRAL_FLATNESS_WARN})",
            {"value": flat},
        )
    )

    if metrics.stereo_correlation is not None:
        corr = abs(metrics.stereo_correlation)
        if corr >= STEREO_CORR_FAIL:
            corr_status = "fail"
        elif corr >= STEREO_CORR_WARN:
            corr_status = "warn"
        else:
            corr_status = "pass"
        results.append(
            VerifyCheck(
                "stereo_phase_coherence",
                corr_status,
                f"L/R correlation {metrics.stereo_correlation:.3f} — very high can indicate synthetic stereo",
                {"correlation": metrics.stereo_correlation},
            )
        )

    if metrics.loudness_range_lu is not None:
        lra = metrics.loudness_range_lu
        if lra <= LRA_FAIL:
            lra_status = "fail"
        elif lra <= LRA_WARN:
            lra_status = "warn"
        else:
            lra_status = "pass"
        results.append(
            VerifyCheck(
                "loudness_dynamics",
                lra_status,
                f"Loudness range {lra:.1f} LU — wider dynamics read more human (warn ≤ {LRA_WARN} LU)",
                {"lra_lu": lra},
            )
        )

    return results


def _distributor_guidance() -> list[str]:
    """Practical distributor/platform guidance from industry detection practices."""
    return [
        "Never upload raw ACE-Step exports — run humanize --style distribute first.",
        "Credit yourself as artist/writer; do not credit Suno, ACE-Step, or AI as performer.",
        "Upload the *_upload.mp3 only — never attach .json sidecars or generator metadata.",
        "Use DDEX/DDEX-style AI disclosure via your distributor when AI assisted vocals or instruments.",
        "Cross-check with external tools (e.g. ACRCloud/Ghost Production detector) before DistroKid/TuneCore.",
        "Keep ACE-Step sidecar JSON + project notes as authorship evidence if a false flag occurs.",
        "Space releases and vary track lengths to avoid mass-upload behavioral flags.",
    ]


def verify_for_upload(
    mp3_path: Path,
    *,
    prepare: bool = True,
    ai_threshold: float = DEFAULT_THRESHOLD,
    metadata_risk_max: int = DEFAULT_METADATA_RISK_MAX,
    strict_ai: bool = True,
    include_veridex: bool = True,
    title: str | None = None,
) -> UploadVerifyReport:
    """Run full pre-upload verification on one MP3.

    Args:
        mp3_path: Source mastered MP3 to verify.
        prepare: Write a metadata-stripped ``*_upload.mp3`` copy before scanning.
        ai_threshold: Max AI probability (0–1) to pass spectral detectors.
        metadata_risk_max: Max metadata/provenance risk score (0–100).
        strict_ai: Fail when any AI detector exceeds ``ai_threshold``.
        include_veridex: Try optional Veridex SpectralSignal if installed.
        title: Optional title tag for the upload copy.

    Returns:
        UploadVerifyReport with ``verified=True`` only when all required checks pass.
    """
    mp3_path = mp3_path.resolve()
    checks: list[VerifyCheck] = []
    recommendations: list[str] = []
    upload_mp3: Path | None = None

    if not mp3_path.exists():
        checks.append(
            VerifyCheck("file_exists", "fail", f"Audio file not found: {mp3_path}")
        )
        return UploadVerifyReport(str(mp3_path), None, False, checks, recommendations=recommendations)

    checks.append(VerifyCheck("file_exists", "pass", "Audio file found"))

    duration = probe_duration_sec(mp3_path)
    if duration < MIN_AUDIO_SEC:
        checks.append(
            VerifyCheck(
                "duration",
                "warn",
                f"Track is {duration:.0f}s — AI detectors work best with {MIN_AUDIO_SEC:.0f}s+",
                {"duration_sec": duration},
            )
        )
    else:
        checks.append(
            VerifyCheck(
                "duration",
                "pass",
                f"Duration {duration:.1f}s meets minimum for AI scan",
                {"duration_sec": duration},
            )
        )

    sidecar = mp3_path.with_suffix(".json")
    if sidecar.exists():
        checks.append(
            VerifyCheck(
                "sidecar_isolation",
                "warn",
                "Companion .json sidecar exists — do NOT upload it to YouTube",
                {"sidecar": str(sidecar)},
            )
        )
        recommendations.append("Upload the MP3 only; keep the .json sidecar local.")
    else:
        checks.append(
            VerifyCheck("sidecar_isolation", "pass", "No ACE-Step sidecar JSON beside MP3")
        )

    scan_target = mp3_path
    if prepare:
        upload_mp3 = mp3_path.with_name(f"{mp3_path.stem}_upload.mp3")
        prepare_upload_copy(mp3_path, upload_mp3, title=title)
        scan_target = upload_mp3
        checks.append(
            VerifyCheck(
                "upload_copy",
                "pass",
                f"Prepared metadata-stripped upload copy: {upload_mp3.name}",
            )
        )

    metadata_scan = scan_for_upload(scan_target)
    if metadata_scan.risk_score > metadata_risk_max:
        checks.append(
            VerifyCheck(
                "metadata_risk",
                "fail",
                f"Metadata risk {metadata_scan.risk_score}/100 exceeds limit {metadata_risk_max}",
                {"risk_score": metadata_scan.risk_score},
            )
        )
    elif metadata_scan.risk_score > 0:
        checks.append(
            VerifyCheck(
                "metadata_risk",
                "warn",
                f"Metadata risk {metadata_scan.risk_score}/100 (limit {metadata_risk_max})",
                {"risk_score": metadata_scan.risk_score},
            )
        )
    else:
        checks.append(
            VerifyCheck(
                "metadata_risk",
                "pass",
                f"Metadata risk {metadata_scan.risk_score}/100",
                {"risk_score": metadata_scan.risk_score},
            )
        )

    for finding in metadata_scan.findings:
        if finding.check_id in {"provenance_sidecar", "metadata_tags"}:
            checks.append(
                VerifyCheck(
                    finding.check_id,
                    _status_from_finding(finding.severity),
                    finding.message,
                )
            )

    ai_detections = run_ai_detectors(
        scan_target,
        threshold=ai_threshold,
        include_veridex=include_veridex,
    )
    for det in ai_detections:
        ai_status = "pass" if det.passed else ("fail" if strict_ai else "warn")
        checks.append(
            VerifyCheck(
                det.detector_id,
                ai_status,
                (
                    f"AI probability {det.ai_probability:.1%} "
                    f"(threshold {det.threshold:.0%}) — {det.label}"
                ),
                det.to_dict(),
            )
        )

    if not any(c.check_id == "veridex_spectral" for c in checks):
        checks.append(
            VerifyCheck(
                "veridex_spectral",
                "skip",
                "Veridex not installed — optional: pip install veridex[audio]",
            )
        )

    checks.append(_behavioral_filename_check(scan_target))
    forensic_metrics = analyze_forensics(scan_target)
    checks.extend(_forensic_checks(forensic_metrics))

    recommendations.extend(metadata_scan.recommendations)
    recommendations.extend(_distributor_guidance())
    recommendations.append(
        "Disclose AI-assisted or synthetic audio on YouTube when required by policy."
    )
    recommendations.append(
        "Third-party detectors (TuneCore, distributors, etc.) may use different models — "
        "treat this report as local QC, not a platform guarantee."
    )

    verified = not any(c.status == "fail" for c in checks)
    return UploadVerifyReport(
        source_mp3=str(mp3_path),
        upload_mp3=str(upload_mp3) if upload_mp3 else None,
        verified=verified,
        checks=checks,
        metadata_scan=metadata_scan,
        ai_detections=ai_detections,
        forensic_metrics=forensic_metrics,
        recommendations=list(dict.fromkeys(recommendations)),
    )


def print_verify_report(report: UploadVerifyReport) -> None:
    """Print a human-readable verification summary."""
    status = "VERIFIED — OK TO UPLOAD" if report.verified else "BLOCKED — FIX ISSUES FIRST"
    print(f"\n{'=' * 60}")
    print(f"UPLOAD VERIFY: {status}")
    print(f"  source: {report.source_mp3}")
    if report.upload_mp3:
        print(f"  upload copy: {report.upload_mp3}")
    print(f"{'=' * 60}")
    print("CHECKLIST:")
    for item in report.checks:
        icon = {"pass": "✓", "warn": "!", "fail": "✗", "skip": "-"}.get(item.status, "?")
        print(f"  [{icon}] {item.check_id}: {item.message}")
    if report.recommendations:
        print("RECOMMENDATIONS:")
        for rec in report.recommendations:
            print(f"  - {rec}")
    print(f"{'=' * 60}\n")


def write_verify_json(report: UploadVerifyReport, out_path: Path) -> None:
    """Persist verification report as JSON."""
    out_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")


def main() -> None:
    """CLI: full pre-upload verification gate."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Pre-upload verification: metadata scan + AI music detectors",
    )
    parser.add_argument("mp3", type=Path, help="Mastered MP3 to verify")
    parser.add_argument(
        "--no-prepare",
        action="store_true",
        help="Skip writing metadata-stripped *_upload.mp3",
    )
    parser.add_argument(
        "--ai-threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"Max AI probability to pass (default {DEFAULT_THRESHOLD})",
    )
    parser.add_argument(
        "--metadata-risk-max",
        type=int,
        default=DEFAULT_METADATA_RISK_MAX,
        help=f"Max metadata risk score (default {DEFAULT_METADATA_RISK_MAX})",
    )
    parser.add_argument(
        "--warn-only-ai",
        action="store_true",
        help="Do not fail on AI detector scores (warn only)",
    )
    parser.add_argument(
        "--no-veridex",
        action="store_true",
        help="Skip optional Veridex detector",
    )
    parser.add_argument(
        "--harden",
        action="store_true",
        help="Run distribute humanize pass before verify (from raw ACE-Step MP3)",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Title tag for prepared upload MP3",
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=None,
        help="Write verify report JSON (default: <mp3>.verify.json)",
    )
    args = parser.parse_args()

    mp3_path = args.mp3.resolve()
    if args.harden and not mp3_path.stem.endswith("_human"):
        from batch_birthday.humanize_audio import humanize_mp3

        hardened = mp3_path.with_name(f"{mp3_path.stem}_human.mp3")
        humanize_mp3(mp3_path, hardened, style="distribute")
        print(f"HARDENED: {hardened}")
        mp3_path = hardened

    report = verify_for_upload(
        mp3_path,
        prepare=not args.no_prepare,
        ai_threshold=args.ai_threshold,
        metadata_risk_max=args.metadata_risk_max,
        strict_ai=not args.warn_only_ai,
        include_veridex=not args.no_veridex,
        title=args.title,
    )
    print_verify_report(report)

    json_out = args.json or args.mp3.with_suffix(".verify.json")
    write_verify_json(report, json_out)
    print(f"REPORT: {json_out}")

    if not report.verified:
        sys.exit(1)


if __name__ == "__main__":
    main()
