"""Tests for CelebrateVibes brand and YouTube SEO helpers."""

import unittest

from batch_birthday.brand import (
    BRAND_NAME,
    upload_metadata,
    youtube_title,
)


class TestBrand(unittest.TestCase):
    """SEO title and metadata format."""

    def test_youtube_title_contains_name(self) -> None:
        """Title should include the birthday name."""
        title = youtube_title("Priya", country="India")
        self.assertIn("Priya", title)
        self.assertIn("Birthday", title)

    def test_upload_metadata_varies_by_country(self) -> None:
        """Same name in different countries can get different titles."""
        us = upload_metadata("Alexander", country="United States")
        ru = upload_metadata("Alexander", country="Russia")
        self.assertNotEqual(us["title"], ru["title"])

    def test_upload_metadata_includes_artist(self) -> None:
        """Metadata bundle should include a natural artist credit."""
        meta = upload_metadata("Arjun", country="India")
        self.assertEqual(meta["brand"], BRAND_NAME)
        self.assertIn("Arjun", meta["title"])
        self.assertTrue(meta["artist"])
        self.assertIsInstance(meta["tags"], list)
        self.assertLessEqual(len(meta["tags"]), 9)


if __name__ == "__main__":
    unittest.main()
