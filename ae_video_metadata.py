"""Embed clean YouTube metadata into rendered MP4 files."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from loguru import logger


def _escape_ffmetadata(value: str) -> str:
    """Escape values for ffmpeg ffmetadata sidecar files."""
    return value.replace("\\", "\\\\").replace("=", "\\=").replace("\n", "\\n").replace(";", "\\;")


def _write_ffmetadata(
    path: Path,
    *,
    title: str,
    artist: str,
    description: str,
) -> None:
    """Write a small ffmetadata file for ffmpeg -map_metadata."""
    lines = [";FFMETADATA1", f"title={_escape_ffmetadata(title)}"]
    lines.append(f"artist={_escape_ffmetadata(artist)}")
    lines.append("encoder=CelebrateVibes")
    if description.strip():
        lines.append(f"comment={_escape_ffmetadata(description.strip())}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def embed_video_metadata(
    src_mp4: Path,
    dst_mp4: Path,
    *,
    title: str,
    artist: str,
    description: str = "",
) -> Path:
    """Write an upload-ready MP4 with stripped then re-applied metadata tags.

    Args:
        src_mp4: Rendered video from After Effects.
        dst_mp4: Destination path (can equal src_mp4 via temp swap).
        title: Title metadata tag.
        artist: Artist metadata tag.
        description: Optional comment/description tag.

    Returns:
        Path to the tagged MP4.
    """
    src_mp4 = src_mp4.resolve()
    dst_mp4 = dst_mp4.resolve()
    dst_mp4.parent.mkdir(parents=True, exist_ok=True)
    temp_out = dst_mp4.with_suffix(".tagged.mp4")

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".ffmeta",
        delete=False,
        encoding="utf-8",
    ) as handle:
        meta_path = Path(handle.name)
    try:
        _write_ffmetadata(meta_path, title=title, artist=artist, description=description)
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(src_mp4),
            "-i",
            str(meta_path),
            "-map_metadata",
            "-1",
            "-map",
            "0",
            "-map_metadata",
            "1",
            "-c",
            "copy",
            str(temp_out),
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        temp_out.replace(dst_mp4)
        return dst_mp4
    except subprocess.CalledProcessError as exc:
        logger.warning("ffmpeg metadata embed failed for {}: {}", src_mp4.name, exc.stderr or exc)
        if temp_out.exists():
            temp_out.unlink()
        return src_mp4
    finally:
        meta_path.unlink(missing_ok=True)


def load_youtube_meta(folder: Path, slug: str) -> dict[str, object]:
    """Load youtube sidecar metadata for one slug."""
    path = folder / f"{slug}.youtube.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))
