"""Rhyming Hindi party lyrics for India CelebrateVibes songs.

Verse 1 stays English (Happy Birthday). Verse 2 onward uses the v3 Hindi template.
"""

from __future__ import annotations

from batch_birthday.name_pronunciation import NamePronunciation, build_pronunciation_instruction

# Appended to the standard English caption/instruction — same singer, Hindi lyrics only.
CELEBRATEVIBES_V2_INDIA_CAPTION_SUFFIX = (
    "Verse 2 onward party lyrics are Hindi only. Keep the exact same singer, vocal timbre, "
    "and festival EDM production as the standard English birthday anthem — only the language "
    "changes after Verse 1."
)

CELEBRATEVIBES_V2_INDIA_INSTRUCTION_SUFFIX = (
    "After Verse 1, sing the supplied Hindi Devanagari lyrics only with clear authentic "
    "Hindi diction. Same singer voice throughout — do not switch vocalist or vocal style. "
    "Hinglish lines like हैप्पी बर्थडे must sound natural at a birthday party."
)

CELEBRATEVIBES_V2_INDIA_CAPTION = CELEBRATEVIBES_V2_INDIA_CAPTION_SUFFIX
CELEBRATEVIBES_V2_INDIA_INSTRUCTION = CELEBRATEVIBES_V2_INDIA_INSTRUCTION_SUFFIX


def build_hindi_body_lyrics(name: str, *, variant: int = 0, native_name: str = "") -> str:
    """Return Hindi party body for India songs (CelebrateVibes template v3)."""
    from batch_birthday.hindi_lyrics_v3 import build_hindi_body_lyrics_v3

    return build_hindi_body_lyrics_v3(name, variant=variant, native_name=native_name or name)


def build_hindi_singing_instruction(pron: NamePronunciation) -> str:
    """ACE-Step instruction for India: same voice as English, Hindi body lyrics."""
    return (
        f"{CELEBRATEVIBES_V2_INDIA_INSTRUCTION_SUFFIX} "
        f"{build_pronunciation_instruction(pron)}"
    )
