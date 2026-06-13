"""Tests for CelebrateVibes brand and YouTube SEO helpers."""

import unittest

from batch_birthday.brand import (
    BRAND_NAME,
    upload_metadata,
    youtube_title,
)


class TestBrand(unittest.TestCase):
    """SEO title and metadata format."""

    def test_youtube_title_matches_competitor_format(self) -> None:
        """Title should mirror established birthday channel pattern."""
        title = youtube_title("Priya")
        self.assertEqual(title, "PRIYA Happy Birthday Song – Happy Birthday to You")

    def test_upload_metadata_includes_brand(self) -> None:
        """Metadata bundle should include brand and tags."""
        meta = upload_metadata("Arjun")
        self.assertEqual(meta["brand"], BRAND_NAME)
        self.assertIn("ARJUN", meta["title"])
        self.assertIsInstance(meta["tags"], list)
        self.assertTrue(len(meta["tags"]) >= 5)


if __name__ == "__main__":
    unittest.main()
