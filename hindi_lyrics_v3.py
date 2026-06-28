"""CelebrateVibes Hindi EDM lyrics v3 — hook-first with per-name variants."""

from __future__ import annotations


def build_hindi_body_lyrics_v3(
    name: str,
    *,
    variant: int = 0,
    native_name: str = "",
) -> str:
    """Tighter v3 body with rotating templates — variant 0 is the locked Aarav template."""
    nm = (native_name or name).strip()
    variant = variant % 4

    if variant == 0:
        verse2 = """आज की रात है तेरे नाम
सपनों को दे नई उड़ान
हर चेहरा मुस्कुराए
दिल से सब ये गुनगुनाए"""
        chorus = f"""ओ... ओ... ओ...
{nm}!
आज की रात तेरे नाम
सब मिल बोलें
हैप्पी बर्थडे!
ओ... ओ... ओ...
{nm}!
दिल से दिल ये गाए
हैप्पी बर्थडे!"""
    elif variant == 1:
        verse2 = """बीट बजे, लाइट्स चमके
दोस्त सब मिलकर झूमे
हँसी-खुशी का माहौल
आज की रात है कमाल"""
        chorus = f"""हे! हे! {nm}!
हाथ ऊपर करो सब
हैप्पी बर्थडे {nm}!
नाचो सुबह तक
हे! हे! {nm}!
ये तेरा जश्न है
हैप्पी बर्थडे!"""
    elif variant == 2:
        verse2 = """तारे चमके तेरे नाम
खुशियाँ बरसे आज
हर दिल में उत्साह
सब गाएं एक साथ"""
        chorus = f"""ओ... ओ... ओ...
{nm}!
आज तू है सितारा
सब मिलकर गाएँ
हैप्पी बर्थडे!
ओ... ओ... ओ...
{nm}!
धड़कन में रhythm
हैप्पी बर्थडे!"""
    else:
        verse2 = """नियॉन लाइट, बास गूँजे
तू है आज का हीरो
मुस्कान हर चेहरे पर
नाचो, बजता रहे ये गाना"""
        chorus = f"""ओ... ओ... ओ...
{nm}!
आज की रात तेरी
सब चिल्लाएँ साथ
हैप्पी बर्थडे!
ओ... ओ... ओ...
{nm}!
खुशियाँ बाँटो सब
हैप्पी बर्थडे!"""

    verse3 = """हर दुआ तेरे साथ चले
हर खुशी तेरे पास रहे
हर सुबह नई रोशनी हो
हर कदम कामयाबी हो"""
    verse4 = """सपने सारे पूरे हों
हर मंज़िल आसान हो
हर पल तेरा जश्न बने
दुनिया तेरे संग झूमे"""
    final_chorus = f"""ओ... ओ... ओ...
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
