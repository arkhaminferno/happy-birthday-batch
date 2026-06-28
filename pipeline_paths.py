"""Filesystem layout for CelebrateVibes v2 multi-stage pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

BATCH_ROOT = Path(__file__).resolve().parent
REPO_ROOT = BATCH_ROOT.parent

# Shared fixed assets (identical for every song).
SHARED_MELODY_DIR = BATCH_ROOT / "melody"
SHARED_LYRICS_DIR = BATCH_ROOT / "lyrics"
FIXED_MELODY_WAV = SHARED_MELODY_DIR / "happy_birthday_melody.wav"

# Per-run stage roots under output/{slug}/.
STAGE_DIRS = ("lyrics", "vocals", "cover", "song", "merge", "intro", "master", "upload")


@dataclass(frozen=True)
class PipelinePaths:
    """Resolved paths for one personalized birthday song."""

    slug: str
    root: Path

    @classmethod
    def for_slug(cls, output_root: Path, slug: str) -> PipelinePaths:
        """Build stage directories for a slug under the output root."""
        root = output_root / slug
        for stage in STAGE_DIRS:
            (root / stage).mkdir(parents=True, exist_ok=True)
        return cls(slug=slug, root=root)

    @property
    def verse1_lyrics(self) -> Path:
        return self.root / "lyrics" / f"{self.slug}_verse1.txt"

    @property
    def body_lyrics(self) -> Path:
        return self.root / "lyrics" / f"{self.slug}_body.txt"

    @property
    def intro_mp3(self) -> Path:
        return self.root / "intro" / f"{self.slug}_countdown.mp3"

    @property
    def verse1_stem_wav(self) -> Path:
        return self.root / "vocals" / f"{self.slug}_verse1_stem.wav"

    @property
    def vocal_mp3(self) -> Path:
        return self.root / "vocals" / f"{self.slug}_verse1_vocal.mp3"

    @property
    def cover_mp3(self) -> Path:
        return self.root / "cover" / f"{self.slug}_verse1_edm.mp3"

    @property
    def body_mp3(self) -> Path:
        return self.root / "song" / f"{self.slug}_body.mp3"

    @property
    def merged_mp3(self) -> Path:
        return self.root / "merge" / f"{self.slug}_merged.mp3"

    @property
    def raw_mp3(self) -> Path:
        return self.root / "master" / f"{self.slug}_raw.mp3"

    @property
    def sidecar_json(self) -> Path:
        return self.root / f"{self.slug}.json"

    def repo_relative(self, path: Path) -> str:
        """Return a path relative to the ACE-Step repo root for API payloads."""
        return str(path.resolve().relative_to(REPO_ROOT))


def resolve_raw_mp3(slug_dir: Path, slug: str) -> Path:
    """Return v2 master raw path if present, else legacy flat raw path."""
    v2_path = slug_dir / "master" / f"{slug}_raw.mp3"
    if v2_path.exists():
        return v2_path
    return slug_dir / f"{slug}_raw.mp3"
