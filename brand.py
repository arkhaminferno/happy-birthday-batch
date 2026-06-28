"""CelebrateVibes brand constants and human-style YouTube upload metadata."""

from __future__ import annotations

import hashlib

BRAND_NAME = "CelebrateVibes"
BRAND_FULL = "CelebrateVibes — Happy Birthday Songs with Names"
BRAND_TAGLINE = "Personalized happy birthday songs and videos for every name."
BRAND_WEBSITE = "https://celebratevibes.com"
BRAND_EMAIL = "hello@celebratevibes.com"
BRAND_YOUTUBE_HANDLE = "@CelebrateVibesOfficial"
BRAND_YOUTUBE_URL = "https://www.youtube.com/@CelebrateVibesOfficial"

# Natural artist credits — rotated per song to avoid uniform channel fingerprints.
_ARTIST_POOL = (
    "Birthday Celebration",
    "Party Music Channel",
    "Birthday Songs Studio",
    "Happy Birthday Music",
    "Birthday Party Mix",
)

_TITLE_TEMPLATES = (
    "{name} Happy Birthday Song | Happy Birthday To You",
    "Happy Birthday {name} | Birthday Song 2026",
    "{name} Birthday Song – Happy Birthday To You Music",
    "Happy Birthday Song for {name} | Party Birthday Music",
)

_DESCRIPTION_TEMPLATES = (
    """Happy Birthday {name}! 🎂

A fun birthday party song to celebrate {name}'s special day. Sing along, share with friends, and make their birthday unforgettable.

🎵 More birthday songs on our channel — search your name in the search bar.
👍 Like & subscribe for new birthday songs every week.

#HappyBirthday #BirthdaySong #{tag_name} #BirthdayParty #PartyMusic""",
    """Wish {name} a very Happy Birthday with this upbeat party song! 🎉

Perfect for birthday parties, surprises, and sharing on social media. Turn up the volume and celebrate together.

Subscribe for more name birthday songs — search our channel for your name.

#HappyBirthday #{tag_name} #BirthdayCelebration #BirthdayMusic #PartySong""",
    """{name}'s Happy Birthday Song is here! 🎈

Share this with {name} on their birthday. A lively party track made for dancing, singing, and celebrating with the people you love.

Find more names on our channel.

#HappyBirthday #BirthdaySong #{tag_name} #BirthdayVibes #Celebrate""",
)


def _digest_key(name: str, country: str = "") -> bytes:
    """Stable hash for per-upload metadata variation."""
    key = f"{country.strip().lower()}:{name.strip().lower()}"
    return hashlib.sha256(key.encode("utf-8")).digest()


def display_name_for_seo(name: str) -> str:
    """Return title-case name for readable titles."""
    return name.strip().title()


def youtube_title(name: str, *, country: str = "") -> str:
    """Build a varied SEO title — same niche, different wording per name."""
    digest = _digest_key(name, country)
    template = _TITLE_TEMPLATES[digest[0] % len(_TITLE_TEMPLATES)]
    return template.format(name=display_name_for_seo(name))


def youtube_artist(name: str, *, country: str = "") -> str:
    """Pick a natural artist tag that is not identical across every upload."""
    digest = _digest_key(name, country)
    return _ARTIST_POOL[digest[1] % len(_ARTIST_POOL)]


def youtube_description(name: str, *, country: str = "") -> str:
    """Human-style description without AI tool references."""
    digest = _digest_key(name, country)
    template = _DESCRIPTION_TEMPLATES[digest[2] % len(_DESCRIPTION_TEMPLATES)]
    clean = display_name_for_seo(name)
    tag_name = clean.replace(" ", "")
    return template.format(name=clean, tag_name=tag_name)


def youtube_tags(name: str, *, country: str = "") -> list[str]:
    """Name-focused tags; small set to avoid spammy repetition."""
    clean = name.strip().lower()
    title = display_name_for_seo(name)
    base = [
        "happy birthday",
        "happy birthday song",
        f"happy birthday {clean}",
        f"{title.lower()} birthday",
        "birthday song with name",
        "birthday party music",
        "birthday celebration",
        "party song",
    ]
    digest = _digest_key(name, country)
    extras = [
        "birthday music",
        "birthday dance song",
        "birthday edm",
        "birthday wishes",
        "birthday party song",
    ]
    extra = extras[digest[3] % len(extras)]
    if extra not in base:
        base.append(extra)
    return base[:9]


def upload_metadata(name: str, *, country: str = "") -> dict[str, object]:
    """Bundle title, artist, description, and tags for one YouTube upload."""
    return {
        "brand": BRAND_NAME,
        "name": name.strip(),
        "title": youtube_title(name, country=country),
        "artist": youtube_artist(name, country=country),
        "description": youtube_description(name, country=country),
        "tags": youtube_tags(name, country=country),
        "category": "Music",
        "privacy": "public",
    }
