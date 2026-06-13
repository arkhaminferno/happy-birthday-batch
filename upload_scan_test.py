"""Tests for batch_birthday upload_scan module."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from batch_birthday.upload_scan import (
    ScanFinding,
    UploadScanReport,
    _sidecar_ai_provenance,
    scan_for_upload,
)


class TestSidecarProvenance(unittest.TestCase):
    """Sidecar JSON provenance classification."""

    def test_confirmed_acestep_when_task_id_present(self) -> None:
        """JSON with task_id should classify as confirmed ACE-Step."""
        meta = {"task_id": "abc", "task_type": "text2music"}
        self.assertEqual(_sidecar_ai_provenance(meta), "confirmed_acestep")

    def test_none_when_meta_missing(self) -> None:
        """Missing metadata should return none."""
        self.assertEqual(_sidecar_ai_provenance(None), "none")


class TestScanForUpload(unittest.TestCase):
    """scan_for_upload behavior with mocked probes."""

    def test_missing_file_returns_fail_finding(self) -> None:
        """Missing MP3 should produce a fail finding and high risk."""
        report = scan_for_upload(Path("/nonexistent/track.mp3"))
        self.assertEqual(report.risk_score, 100)
        self.assertTrue(any(f.check_id == "file_missing" for f in report.findings))

    @patch("batch_birthday.upload_scan.probe_duration_sec", return_value=150.0)
    @patch("batch_birthday.upload_scan._ebur128_lra", return_value=8.0)
    @patch("batch_birthday.upload_scan._ffprobe_tags", return_value={})
    def test_sidecar_increases_risk(
        self,
        _tags: object,
        _lra: object,
        _dur: object,
    ) -> None:
        """ACE-Step sidecar JSON should raise risk and add provenance finding."""
        with tempfile.TemporaryDirectory() as tmp:
            mp3 = Path(tmp) / "song.mp3"
            mp3.write_bytes(b"\x00")
            sidecar = mp3.with_suffix(".json")
            sidecar.write_text(
                json.dumps({"task_id": "x", "task_type": "text2music"}),
                encoding="utf-8",
            )
            report = scan_for_upload(mp3)
            self.assertEqual(report.ai_provenance, "confirmed_acestep")
            self.assertGreaterEqual(report.risk_score, 40)
            self.assertTrue(any(f.check_id == "provenance_sidecar" for f in report.findings))


class TestReportSerialization(unittest.TestCase):
    """Report JSON export."""

    def test_to_dict_includes_findings(self) -> None:
        """to_dict should serialize nested findings."""
        report = UploadScanReport(
            mp3_path="/a.mp3",
            duration_sec=120.0,
            risk_score=10,
            ai_provenance="none",
            findings=[ScanFinding("test", "info", "ok")],
        )
        data = report.to_dict()
        self.assertEqual(data["findings"][0]["check_id"], "test")


if __name__ == "__main__":
    unittest.main()
