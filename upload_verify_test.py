"""Tests for AI music detector and upload verification gate."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

from batch_birthday.ai_music_detector import (
    FakeprintConfig,
    extract_fakeprint,
    predict_fakeprint_ai,
)
from batch_birthday.upload_verify import UploadVerifyReport, verify_for_upload


class TestFakeprintExtraction(unittest.TestCase):
    """Fakeprint vector shape and normalization."""

    def test_fakeprint_length_matches_lofcz_model(self) -> None:
        """Fakeprint should be 3585 bins for default lofcz preprocessing."""
        rng = np.random.default_rng(0)
        waveform = rng.normal(0, 0.05, size=(1, 16000 * 12)).astype(np.float32)
        cfg = FakeprintConfig()
        fp = extract_fakeprint(waveform, cfg.sample_rate, cfg)
        self.assertEqual(fp.shape[0], 3585)
        self.assertGreaterEqual(float(fp.max()), 0.99)


class TestPredictFakeprintAi(unittest.TestCase):
    """AI probability inference with mocked weights."""

    @patch("safetensors.numpy.load_file")
    @patch("batch_birthday.ai_music_detector._load_audio_mono")
    @patch("batch_birthday.ai_music_detector.ensure_detector_model")
    @patch("batch_birthday.ai_music_detector.extract_fakeprint")
    def test_high_logit_flags_ai(
        self,
        mock_extract: MagicMock,
        _ensure: MagicMock,
        mock_audio: MagicMock,
        mock_load_file: MagicMock,
    ) -> None:
        """Large positive logit should classify as likely AI."""
        mock_audio.return_value = (np.zeros((1, 160000), dtype=np.float32), 16000)
        mock_extract.return_value = np.ones(3585, dtype=np.float32)
        mock_load_file.return_value = {
            "weights": np.ones((1, 3585), dtype=np.float32) * 5.0,
            "bias": np.array([0.0], dtype=np.float32),
        }
        result = predict_fakeprint_ai(Path("/fake/song.mp3"), threshold=0.5)
        self.assertFalse(result.passed)
        self.assertGreater(result.ai_probability, 0.9)
        self.assertEqual(result.detector_id, "lofcz_fakeprint")


class TestUploadVerifyGate(unittest.TestCase):
    """verify_for_upload pass/fail aggregation."""

    @patch("batch_birthday.upload_verify.analyze_forensics")
    @patch("batch_birthday.upload_verify.run_ai_detectors")
    @patch("batch_birthday.upload_verify.scan_for_upload")
    @patch("batch_birthday.upload_verify.prepare_upload_copy")
    @patch("batch_birthday.upload_verify.probe_duration_sec", return_value=150.0)
    def test_blocks_when_ai_detector_fails(
        self,
        _dur: MagicMock,
        mock_prepare: MagicMock,
        mock_scan: MagicMock,
        mock_ai: MagicMock,
        mock_forensics: MagicMock,
    ) -> None:
        """Strict AI failure should set verified=False."""
        from batch_birthday.ai_music_detector import AiDetectionResult
        from batch_birthday.audio_forensics import ForensicMetrics
        from batch_birthday.upload_scan import UploadScanReport

        mock_forensics.return_value = ForensicMetrics(150.0, 0.2, 0.85, 9.0)

        with tempfile.TemporaryDirectory() as tmp:
            mp3 = Path(tmp) / "song.mp3"
            mp3.write_bytes(b"\x00")
            upload = Path(tmp) / "song_upload.mp3"
            mock_prepare.side_effect = lambda src, dst, **_: dst.write_bytes(b"\x00") or dst
            mock_scan.return_value = UploadScanReport(
                str(upload), 150.0, 10, "unknown", [], []
            )
            mock_ai.return_value = [
                AiDetectionResult(
                    "lofcz_fakeprint", 0.95, "likely_ai_generated", 0.5, False, {}
                )
            ]
            report = verify_for_upload(mp3, prepare=True, strict_ai=True)
            self.assertFalse(report.verified)
            self.assertTrue(any(c.check_id == "lofcz_fakeprint" and c.status == "fail" for c in report.checks))

    @patch("batch_birthday.upload_verify.analyze_forensics")
    @patch("batch_birthday.upload_verify.run_ai_detectors")
    @patch("batch_birthday.upload_verify.scan_for_upload")
    @patch("batch_birthday.upload_verify.prepare_upload_copy")
    @patch("batch_birthday.upload_verify.probe_duration_sec", return_value=150.0)
    def test_passes_when_all_checks_ok(
        self,
        _dur: MagicMock,
        mock_prepare: MagicMock,
        mock_scan: MagicMock,
        mock_ai: MagicMock,
        mock_forensics: MagicMock,
    ) -> None:
        """Clean metadata + low AI score should verify."""
        from batch_birthday.ai_music_detector import AiDetectionResult
        from batch_birthday.audio_forensics import ForensicMetrics
        from batch_birthday.upload_scan import UploadScanReport

        mock_forensics.return_value = ForensicMetrics(150.0, 0.2, 0.85, 9.0)

        with tempfile.TemporaryDirectory() as tmp:
            mp3 = Path(tmp) / "song.mp3"
            mp3.write_bytes(b"\x00")
            mock_prepare.side_effect = lambda src, dst, **_: dst.write_bytes(b"\x00") or dst
            mock_scan.return_value = UploadScanReport(
                str(mp3), 150.0, 5, "unknown", [], []
            )
            mock_ai.return_value = [
                AiDetectionResult("lofcz_fakeprint", 0.12, "likely_human", 0.5, True, {})
            ]
            report = verify_for_upload(mp3, prepare=True)
            self.assertTrue(report.verified)


class TestVerifyReportJson(unittest.TestCase):
    """JSON export round-trip."""

    def test_to_dict_includes_verified_flag(self) -> None:
        """to_dict should expose verified boolean."""
        report = UploadVerifyReport(
            source_mp3="/a.mp3",
            upload_mp3="/a_upload.mp3",
            verified=True,
        )
        data = report.to_dict()
        self.assertTrue(data["verified"])


if __name__ == "__main__":
    unittest.main()
