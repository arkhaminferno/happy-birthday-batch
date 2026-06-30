"""Deterministic per-name video variation for AE template batch renders."""

from __future__ import annotations

from dataclasses import dataclass

from batch_birthday.batch_variation import _digest

# Cohesive party themes: one hue shift applied uniformly (like template gold everywhere).
# Index 0 keeps the editor's default gold look (0° offset).
_PARTY_THEMES: tuple[tuple[str, float], ...] = (
    ("gold", 0.0),
    ("champagne", 6.0),
    ("rose", 308.0),
    ("hot_pink", 278.0),
    ("magenta", 258.0),
    ("royal_purple", 233.0),
    ("coral", 330.0),
    ("sunset", 22.0),
    ("fuchsia", 288.0),
    ("blush", 298.0),
)


@dataclass(frozen=True)
class VideoVariation:
    """Per-element visual tweaks for the AE birthday template."""

    theme_name: str
    theme_hue: float
    cake_hue: float
    candle_hue: float
    firework_hue: float
    gradient_hue: float
    confetti_hue: float
    background_hue: float
    cake_speed: float
    candle_speed: float
    firework_speed: float
    confetti_speed: float
    background_speed: float

    def to_dict(self) -> dict[str, float | str]:
        """Serialize for AE job JSON."""
        return {
            "theme_name": self.theme_name,
            "theme_hue": self.theme_hue,
            "cake_hue": self.cake_hue,
            "candle_hue": self.candle_hue,
            "firework_hue": self.firework_hue,
            "gradient_hue": self.gradient_hue,
            "confetti_hue": self.confetti_hue,
            "background_hue": self.background_hue,
            "cake_speed": self.cake_speed,
            "candle_speed": self.candle_speed,
            "firework_speed": self.firework_speed,
            "confetti_speed": self.confetti_speed,
            "background_speed": self.background_speed,
        }


def _slot(digest: bytes, index: int) -> float:
    """Return a stable 0..1 scalar from digest bytes."""
    return digest[index] / 255.0


def _speed(slot: float) -> float:
    """Map slot to subtle layer speed multiplier."""
    return round(0.94 + slot * 0.12, 4)


def _pick_theme(digest: bytes) -> tuple[str, float]:
    """Pick one cohesive party palette for the whole video."""
    name, hue = _PARTY_THEMES[digest[0] % len(_PARTY_THEMES)]
    jitter = (digest[1] % 5) - 2
    return name, round((hue + jitter) % 360.0, 1)


def video_variation_for(slug: str) -> VideoVariation:
    """Derive a unified party theme plus motion tweaks from a song slug."""
    digest = _digest(slug)
    theme_name, theme_hue = _pick_theme(digest)
    return VideoVariation(
        theme_name=theme_name,
        theme_hue=theme_hue,
        cake_hue=theme_hue,
        candle_hue=theme_hue,
        firework_hue=theme_hue,
        gradient_hue=theme_hue,
        confetti_hue=theme_hue,
        background_hue=theme_hue,
        cake_speed=_speed(_slot(digest, 6)),
        candle_speed=_speed(_slot(digest, 13)),
        firework_speed=_speed(_slot(digest, 14)),
        confetti_speed=_speed(_slot(digest, 15)),
        background_speed=_speed(_slot(digest, 16)),
    )
