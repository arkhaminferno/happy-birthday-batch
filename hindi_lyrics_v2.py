"""CelebrateVibes Hindi EDM lyrics template v2 for India party sections."""

from __future__ import annotations


def build_hindi_body_lyrics_v2(name: str, *, native_name: str = "") -> str:
    """Return Verse 2–Final Chorus using the approved v2 Hindi template.

    Args:
        name: Latin display name (e.g. Aarav).
        native_name: Devanagari name for Hindi chorus (e.g. आरव).

    Returns:
        Section-tagged Hindi body lyrics for ACE-Step.
    """
    nm = (native_name or name).strip()

    verse2 = """आज की रात है तेरे नाम
सपनों को दे नई उड़ान
हर चेहरा मुस्कुराए
दिल से सब ये गुनगुनाए"""

    chorus = f"""ओ ओ ओ...
{nm}!
आज की रात तेरे नाम
ओ ओ ओ...
{nm}!
सब मिल बोलें
हैप्पी बर्थडे!
ओ ओ ओ...
{nm}!
दिल से दिल ये गाए
हैप्पी बर्थडे!"""

    verse3 = """हर दुआ तेरे साथ चले
हर खुशी तेरे पास रहे
हर सुबह नई रोशनी हो
हर कदम कामयाबी हो"""

    verse4 = """सपने सारे पूरे हों
हर मंज़िल आसान हो
हर पल तेरा जश्न बने
दुनिया तेरे संग झूमे"""

    final_chorus = f"""ओ ओ ओ...
{nm}!
आज की रात तेरे नाम
सब मिलकर गाएँ
हैप्पी बर्थडे!
हैप्पी बर्थडे!
हैप्पी बर्थडे!
{nm}!"""

    return f"""[Verse 2]
{verse2}

[Chorus]
{chorus}

[Verse 3]
{verse3}

[Verse 4]
{verse4}

[Final Chorus]
{final_chorus}"""
