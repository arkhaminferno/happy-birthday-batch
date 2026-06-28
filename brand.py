"""CelebrateVibes brand constants and YouTube SEO metadata helpers."""

from __future__ import annotations

BRAND_NAME = "CelebrateVibes"
BRAND_FULL = "CelebrateVibes — Happy Birthday Songs with Names"
BRAND_TAGLINE = "Personalized happy birthday songs and videos for every name."
BRAND_WEBSITE = "https://celebratevibes.com"
BRAND_EMAIL = "hello@celebratevibes.com"
BRAND_YOUTUBE_HANDLE = "@CelebrateVibesOfficial"
BRAND_YOUTUBE_URL = "https://www.youtube.com/@CelebrateVibesOfficial"

# Competitor-aligned title for name search (e.g. "PRIYA Happy Birthday Song – …").
YOUTUBE_TITLE_SUFFIX = "Happy Birthday Song – Happy Birthday to You"


def display_name_for_seo(name: str) -> str:
    """Return uppercase name for titles, matching established birthday channels."""
    return name.strip().upper()


def youtube_title(name: str) -> str:
    """Build SEO title: ``PRIYA Happy Birthday Song – Happy Birthday to You``."""
    return f"{display_name_for_seo(name)} {YOUTUBE_TITLE_SUFFIX}"


def youtube_description(name: str) -> str:
    """Standard video description with brand links and search keywords."""
    seo_name = display_name_for_seo(name)
    return f"""{seo_name} Happy Birthday Song – Happy Birthday to You

Wish {name.strip()} a very happy birthday with this personalized EDM party birthday song from {BRAND_NAME}.

🎂 Find more names on our channel — use the search bar to look up your name.
🎵 Music by {BRAND_NAME}
🌐 {BRAND_WEBSITE}

#HappyBirthday #{seo_name.replace(' ', '')} #BirthdaySong #CelebrateVibes #BirthdayParty #EDM

© {BRAND_NAME}. All rights reserved.
"""


def youtube_tags(name: str) -> list[str]:
    """Suggested YouTube tags for a personalized birthday upload."""
    clean = name.strip()
    upper = display_name_for_seo(clean)
    return [
        "happy birthday",
        "happy birthday song",
        f"happy birthday {clean.lower()}",
        f"{upper} happy birthday",
        "birthday song with name",
        "personalized birthday song",
        BRAND_NAME.lower(),
        "birthday party song",
        "edm birthday",
    ]


def upload_metadata(name: str) -> dict[str, object]:
    """Bundle title, description, and tags for one upload."""
    return {
        "brand": BRAND_NAME,
        "name": name.strip(),
        "title": youtube_title(name),
        "description": youtube_description(name),
        "tags": youtube_tags(name),
    }
