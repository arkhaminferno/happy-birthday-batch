"""Build JSON job specs for one AE render."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from batch_birthday.ae_config import (
    ADJUST_LAYER_NAME,
    AE_JOBS_DIR,
    AE_PROJECTS_DIR,
    EDIT_COMP_FALLBACKS,
    EDIT_COMP_NAME,
    NAME_TEXT_LAYER,
    RENDER_COMP_NAME,
    TEMPLATE_AEP,
)
from batch_birthday.ae_video_variation import VideoVariation, video_variation_for
from batch_birthday.orchestrator import BATCH_ROOT
from batch_birthday.upload_scan import probe_duration_sec

OUTPUT_ROOT = BATCH_ROOT / "output"


@dataclass(frozen=True)
class RenderJob:
    """One personalized AE render request."""

    slug: str
    name: str
    display_name: str
    mp3_path: Path
    output_mp4: Path
    project_path: Path
    job_json_path: Path
    duration_sec: float
    variation: VideoVariation
    title: str
    artist: str

    def to_dict(self) -> dict[str, object]:
        """Serialize for ExtendScript JSON loader."""
        return {
            "template_aep": str(TEMPLATE_AEP.resolve()),
            "project_path": str(self.project_path.resolve()),
            "mp3_path": str(self.mp3_path.resolve()),
            "output_mp4": str(self.output_mp4.resolve()),
            "slug": self.slug,
            "name": self.name,
            "display_name": self.display_name,
            "duration_sec": self.duration_sec,
            "edit_comp": EDIT_COMP_NAME,
            "edit_comp_fallbacks": list(EDIT_COMP_FALLBACKS),
            "render_comp": RENDER_COMP_NAME,
            "name_text_layer": NAME_TEXT_LAYER,
            "adjust_layer": ADJUST_LAYER_NAME,
            "variation": self.variation.to_dict(),
            "title": self.title,
            "artist": self.artist,
        }


def build_render_job(
    *,
    slug: str,
    name: str,
    title: str,
    artist: str,
    display_name: str = "",
    output_root: Path = OUTPUT_ROOT,
) -> RenderJob:
    """Resolve paths and variation for one slug."""
    folder = output_root / slug
    mp3_path = folder / f"{slug}.mp3"
    if not mp3_path.is_file():
        raise FileNotFoundError(f"Missing MP3: {mp3_path}")

    AE_JOBS_DIR.mkdir(parents=True, exist_ok=True)
    AE_PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    job_json_path = AE_JOBS_DIR / f"{slug}.json"
    project_path = AE_PROJECTS_DIR / f"{slug}.aep"
    output_mp4 = folder / f"{slug}-youtube.mp4"
    duration_sec = probe_duration_sec(mp3_path)
    resolved_display = display_name.strip() or name.strip().title()

    return RenderJob(
        slug=slug,
        name=name.strip(),
        display_name=resolved_display,
        mp3_path=mp3_path,
        output_mp4=output_mp4,
        project_path=project_path,
        job_json_path=job_json_path,
        duration_sec=duration_sec,
        variation=video_variation_for(slug),
        title=title,
        artist=artist,
    )


def write_render_job(job: RenderJob) -> Path:
    """Persist job JSON for the ExtendScript runner."""
    job.job_json_path.write_text(
        json.dumps(job.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return job.job_json_path
