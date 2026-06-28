"""Tests for release upload tracker."""

import csv
import tempfile
import unittest
from pathlib import Path

from batch_birthday.release_tracker import (
    init_from_world_names,
    mark_uploaded,
    summarize,
    sync_mp3_ready,
)


class TestReleaseTracker(unittest.TestCase):
    """Release CSV tracks MP3 readiness and platform uploads."""

    def test_init_and_sync_mp3_ready(self) -> None:
        """Init from world names and detect local MP3 files."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            names_csv = root / "names.csv"
            status_csv = root / "release_status.csv"
            output_root = root / "output"
            names_csv.write_text(
                "name,language,country,gender,pronunciation,bpm,genre_variant,seed,enabled,locked,slug\n"
                "Aarav,en,India,boy,AA-ruhv,129,celebratevibes_v2,1,true,true,aarav-in-birthday-edm-party\n",
                encoding="utf-8",
            )
            mp3 = output_root / "aarav-in-birthday-edm-party" / "aarav-in-birthday-edm-party.mp3"
            mp3.parent.mkdir(parents=True)
            mp3.write_bytes(b"fake")

            init_from_world_names(names_csv=names_csv, path=status_csv)
            rows = sync_mp3_ready(output_root=output_root, path=status_csv)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["mp3_ready"], "true")

            stats = summarize(rows)
            self.assertEqual(stats.mp3_ready, 1)
            self.assertEqual(stats.youtube, 0)

    def test_mark_platform_upload(self) -> None:
        """Mark and persist one platform upload flag."""
        with tempfile.TemporaryDirectory() as tmp:
            status_csv = Path(tmp) / "release_status.csv"
            status_csv.write_text(
                "slug,name,country,language,gender,locked,mp3_ready,youtube,instagram,facebook,notes,updated_at\n"
                "demo,demo,India,en,boy,false,true,false,false,false,,2026-01-01T00:00:00Z\n",
                encoding="utf-8",
            )
            mark_uploaded("demo", "youtube", path=status_csv, notes="live")
            with status_csv.open(newline="", encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row["youtube"], "true")
            self.assertEqual(row["notes"], "live")


if __name__ == "__main__":
    unittest.main()
