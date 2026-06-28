"""Deterministic per-name variation for batch birthday generation.

Each name gets a unique seed and mastering fingerprint while keeping the same
template genre, lyrics structure, and overall sound.
"""

from __future__ import annotations

import hashlib
import zlib
from dataclasses import asdict, dataclass

BASE_TEMPLATE_SEED = 2_664_429_003
DEFAULT_GENRE = "celebratevibes_v2"
DEFAULT_BPM = 128


@dataclass(frozen=True)
class SongVariation:
    """Per-song generation knobs to avoid uniform batch fingerprints."""

    bpm: int
    lyrics_variant: int
    body_crossfade_sec: float
    opening_trim_hint_sec: float

    def to_dict(self) -> dict[str, float | int]:
        """Serialize for JSON sidecars."""
        return {
            "bpm": self.bpm,
            "lyrics_variant": self.lyrics_variant,
            "body_crossfade_sec": self.body_crossfade_sec,
            "opening_trim_hint_sec": self.opening_trim_hint_sec,
        }


@dataclass(frozen=True)
class MasterVariation:
    """Per-song ffmpeg mastering knobs derived from a stable name key."""

    pitch_rate: float
    eq_mid_db: float
    eq_high_db: float
    stereo_width: float
    softclip_threshold: float
    loudness_i: float
    lra_target: float

    @property
    def atempo(self) -> float:
        """Compensate tempo after micro pitch shift."""
        return 1.0 / self.pitch_rate

    def to_dict(self) -> dict[str, float]:
        """Serialize for JSON sidecars."""
        return asdict(self)


def _digest(key: str) -> bytes:
    """Stable hash bytes for a display name or slug."""
    normalized = key.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).digest()


def derive_seed(name: str, base_seed: int = BASE_TEMPLATE_SEED) -> str:
    """Return a deterministic ACE-Step seed unique to *name*."""
    crc = zlib.crc32(name.strip().lower().encode("utf-8")) & 0xFFFFFFFF
    value = (int(base_seed) + crc) % (2**32 - 1)
    return str(value)


def slug_for_name(name: str, country: str = "") -> str:
    """Build output slug, optionally prefixed with a country code."""
    ascii_name = name.strip().lower().replace(" ", "-")
    safe = "".join(ch if ch.isalnum() or ch == "-" else "" for ch in ascii_name)
    safe = safe.strip("-") or "birthday"
    country_codes = {
        "india": "in",
        "united states": "us",
        "usa": "us",
        "russia": "ru",
        "china": "cn",
    }
    code = country_codes.get(country.strip().lower(), "")
    if code:
        return f"{safe}-{code}-birthday-edm-party"
    return f"{safe}-birthday-edm-party"


def song_variation_for(name: str, country: str = "") -> SongVariation:
    """Compute unique BPM, lyrics, and merge variation per name."""
    digest = _digest(f"{country}:{name}".strip().lower())
    slots = [digest[index] / 255.0 for index in range(4)]
    bpm = 122 + int(slots[0] * 10)  # 122–132
    lyrics_variant = int(slots[1] * 4) % 4
    body_crossfade_sec = round(0.8 + slots[2] * 0.8, 2)  # 0.8–1.6
    opening_trim_hint_sec = round(12.5 + slots[3] * 4.0, 2)  # 12.5–16.5
    return SongVariation(
        bpm=bpm,
        lyrics_variant=lyrics_variant,
        body_crossfade_sec=body_crossfade_sec,
        opening_trim_hint_sec=opening_trim_hint_sec,
    )


def master_variation_for(name: str) -> MasterVariation:
    """Compute subtle mastering variation — same vibe, unique fingerprint."""
    digest = _digest(name)
    slots = [digest[i] / 255.0 for i in range(6)]

    pitch_rate = 0.978 + slots[0] * 0.012  # ~978–990 (±20 cents)
    eq_mid_db = -1.4 + slots[1] * 0.6
    eq_high_db = -2.3 + slots[2] * 0.8
    stereo_width = 1.010 + slots[3] * 0.012
    softclip_threshold = 0.895 + slots[4] * 0.05
    loudness_i = -14.2 + slots[5] * 0.6
    lra_target = 10.5 + (slots[0] + slots[3]) * 1.5

    return MasterVariation(
        pitch_rate=round(pitch_rate, 5),
        eq_mid_db=round(eq_mid_db, 2),
        eq_high_db=round(eq_high_db, 2),
        stereo_width=round(stereo_width, 4),
        softclip_threshold=round(softclip_threshold, 3),
        loudness_i=round(loudness_i, 2),
        lra_target=round(lra_target, 1),
    )


def build_distribute_filter(variation: MasterVariation) -> str:
    """Build ffmpeg ``-af`` chain for distribute-style mastering."""
    rate = variation.pitch_rate
    tempo = variation.atempo
    return (
        f"asetrate=48000*{rate},aresample=48000,atempo={tempo:.5f},"
        f"equalizer=f=2800:t=q:w=1.2:g={variation.eq_mid_db},"
        f"equalizer=f=6200:t=h:w=0.8:g={variation.eq_high_db},"
        f"asoftclip=type=tanh:threshold={variation.softclip_threshold}:output=1,"
        f"extrastereo=m={variation.stereo_width},"
        f"loudnorm=I={variation.loudness_i}:TP=-1.0:LRA={variation.lra_target}"
    )
