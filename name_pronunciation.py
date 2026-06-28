"""Per-name pronunciation guides for ACE-Step vocals and local TTS stems."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NamePronunciation:
    """Display name plus phonetic guide for one country-specific entry."""

    name: str
    country: str
    phonetic: str
    native_script: str = ""


# Country + display name → pronunciation guide.
_PRONUNCIATIONS: dict[tuple[str, str], NamePronunciation] = {}


def _add(country: str, name: str, phonetic: str, native: str = "") -> None:
    """Register one pronunciation entry."""
    _PRONUNCIATIONS[(country.strip().lower(), name.strip())] = NamePronunciation(
        name=name.strip(),
        country=country.strip(),
        phonetic=phonetic.strip(),
        native_script=native.strip(),
    )


# India
for _name, _phon, _native in [
    ("Aarav", "AA-ruhv", "आरव"),
    ("Arjun", "AR-jun", "अर्जुन"),
    ("Vivaan", "vih-VAAN", "विवान"),
    ("Aditya", "aa-DIT-ya", "आदित्य"),
    ("Krishna", "KRISH-na", "कृष्ण"),
    ("Rohan", "ROH-hun", "रोहन"),
    ("Rahul", "RAA-hool", "राहुल"),
    ("Karan", "KUH-run", "करण"),
    ("Vikram", "VIK-rum", "विक्रम"),
    ("Aman", "UH-mun", "अमन"),
    ("Priya", "PREE-ya", "प्रिया"),
    ("Ananya", "uh-NUN-ya", "अनन्या"),
    ("Aanya", "AAN-ya", "आन्या"),
    ("Diya", "DEE-ya", "दिया"),
    ("Kavya", "KAAV-ya", "काव्या"),
    ("Neha", "NAY-ha", "नेहा"),
    ("Pooja", "POO-jaa", "पूजा"),
    ("Sneha", "SNAY-ha", "स्नेहा"),
    ("Riya", "REE-ya", "रिया"),
    ("Aditi", "uh-DIT-ee", "अदिति"),
]:
    _add("India", _name, _phon, _native)

# United States
for _name, _phon in [
    ("Liam", "LEE-um"),
    ("Noah", "NOH-uh"),
    ("James", "JAYMZ"),
    ("William", "WILL-yum"),
    ("Benjamin", "BEN-juh-min"),
    ("Lucas", "LOO-kus"),
    ("Henry", "HEN-ree"),
    ("Alexander", "AL-ig-ZAN-der"),
    ("Ethan", "EE-thun"),
    ("Michael", "MY-kul"),
    ("Olivia", "oh-LIV-ee-uh"),
    ("Emma", "EM-uh"),
    ("Charlotte", "SHAR-lut"),
    ("Amelia", "uh-MEE-lee-uh"),
    ("Sophia", "soh-FEE-uh"),
    ("Isabella", "iz-uh-BEL-uh"),
    ("Ava", "AY-vuh"),
    ("Mia", "MEE-uh"),
    ("Evelyn", "EV-uh-lin"),
    ("Harper", "HAR-per"),
]:
    _add("United States", _name, _phon)

# Russia
for _name, _phon, _native in [
    ("Alexander", "al-ek-SAN-dr", "Александр"),
    ("Dmitry", "DMEE-tree", "Дмитрий"),
    ("Ivan", "ee-VAHN", "Иван"),
    ("Maxim", "mak-SEEM", "Максим"),
    ("Mikhail", "mee-kha-EEL", "Михаил"),
    ("Nikita", "nee-KEE-ta", "Никита"),
    ("Sergey", "ser-GAY", "Сергей"),
    ("Vladimir", "vlah-DEE-meer", "Владимир"),
    ("Andrey", "an-DRAY", "Андрей"),
    ("Pavel", "PAH-vyel", "Павел"),
    ("Anastasia", "ah-nah-stah-SEE-ya", "Анастасия"),
    ("Maria", "mah-REE-ya", "Мария"),
    ("Anna", "AHN-na", "Анна"),
    ("Ekaterina", "ye-ka-te-REE-na", "Екатерина"),
    ("Sofia", "so-FEE-ya", "София"),
    ("Daria", "DAR-ya", "Дарья"),
    ("Olga", "OHL-ga", "Ольга"),
    ("Elena", "ye-LEN-a", "Елена"),
    ("Polina", "pa-LEE-na", "Полина"),
    ("Alina", "ah-LEE-na", "Алина"),
]:
    _add("Russia", _name, _phon, _native)

# China
for _name, _phon, _native in [
    ("Wei", "WAY", "伟"),
    ("Jun", "JWEEN", "军"),
    ("Hao", "HOW", "浩"),
    ("Ming", "MING", "明"),
    ("Lei", "LAY", "雷"),
    ("Jian", "JEE-en", "健"),
    ("Tao", "TOW", "涛"),
    ("Peng", "PUNG", "鹏"),
    ("Bo", "BWOH", "博"),
    ("Qiang", "CHYANG", "强"),
    ("Li", "LEE", "丽"),
    ("Jing", "JING", "静"),
    ("Fang", "FAHNG", "芳"),
    ("Na", "NAH", "娜"),
    ("Yan", "YEN", "艳"),
    ("Xia", "SHYAH", "夏"),
    ("Ling", "LING", "玲"),
    ("Mei", "MAY", "美"),
    ("Yu", "YOO", "玉"),
    ("Xiu", "SHYOH", "秀"),
]:
    _add("China", _name, _phon, _native)


def lookup_pronunciation(name: str, country: str = "") -> NamePronunciation | None:
    """Return the pronunciation guide for a name in *country*."""
    key = (country.strip().lower(), name.strip())
    return _PRONUNCIATIONS.get(key)


def resolve_pronunciation(name: str, country: str = "", phonetic: str = "") -> NamePronunciation:
    """Resolve pronunciation from CSV override or built-in table."""
    if phonetic.strip():
        return NamePronunciation(name=name.strip(), country=country.strip(), phonetic=phonetic.strip())
    found = lookup_pronunciation(name, country)
    if found:
        return found
    return NamePronunciation(name=name.strip(), country=country.strip(), phonetic=name.strip())


def tts_spoken_name(pron: NamePronunciation) -> str:
    """Convert hyphenated phonetic guide into macOS TTS friendly syllables."""
    return pron.phonetic.replace("-", " ").replace("  ", " ").strip()


def build_pronunciation_instruction(pron: NamePronunciation) -> str:
    """Instruction snippet forcing correct name pronunciation in ACE-Step."""
    parts = [
        f"Pronounce the name {pron.name} exactly as: {pron.phonetic}.",
        "Say the name clearly on every chorus and every name line.",
        "Do not Americanize or anglicize the name incorrectly.",
    ]
    if pron.native_script:
        parts.append(f"Native spelling reference: {pron.native_script}.")
    return " ".join(parts)
