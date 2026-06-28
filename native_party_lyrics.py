"""Route party body lyrics by country — native language after English Verse 1."""

from __future__ import annotations

from batch_birthday.chinese_party_lyrics import build_chinese_body_lyrics
from batch_birthday.hindi_party_lyrics import build_hindi_body_lyrics
from batch_birthday.russian_party_lyrics import build_russian_body_lyrics


def build_native_body_lyrics(
    name: str,
    country: str,
    *,
    variant: int = 0,
    native_name: str = "",
    language: str = "en",
) -> str:
    """Return party body lyrics in the country's native language."""
    key = country.strip().lower()
    if key == "india":
        return build_hindi_body_lyrics(name, variant=variant, native_name=native_name or name)
    if key == "russia":
        return build_russian_body_lyrics(name, variant=variant, native_name=native_name or name)
    if key == "china":
        return build_chinese_body_lyrics(name, variant=variant, native_name=native_name or name)
    from batch_birthday.lyrics_builder import build_body_lyrics

    return build_body_lyrics(name, language, variant=variant)
