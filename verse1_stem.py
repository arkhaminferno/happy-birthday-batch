"""Create a deterministic Verse 1 guide stem for ACE cover mode.

The stem is generated locally before ACE-Step runs. It combines the fixed
Happy Birthday melody guide with a dry spoken name/lyric guide when macOS
``say`` is available. ACE cover mode then has one clear source file to follow.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
from scipy.io import wavfile

from batch_birthday.lyrics_builder import build_verse1_lyrics
from batch_birthday.melody_generator import DEFAULT_BPM, SAMPLE_RATE, build_phrase
from batch_birthday.name_pronunciation import (
    resolve_pronunciation,
    tts_spoken_name,
)
from batch_birthday.pipeline_paths import PipelinePaths

DEFAULT_TTS_VOICE = "Samantha"
TTS_RATE = 145


def _strip_section_tags(lyrics: str) -> str:
    """Return only singable lines from a section-tagged lyric block."""
    lines = []
    for line in lyrics.splitlines():
        stripped = line.strip()
        if not stripped or (stripped.startswith("[") and stripped.endswith("]")):
            continue
        lines.append(stripped)
    return ". ".join(lines)


def _write_melody_guide(dst: Path, *, bpm: int) -> float:
    """Write the fixed melody guide as a stereo WAV and return duration."""
    mono = build_phrase(bpm=bpm)
    stereo = np.stack([mono, mono], axis=1)
    peak = float(np.max(np.abs(stereo)))
    if peak > 0:
        stereo = stereo / peak * 0.55
    wavfile.write(str(dst), SAMPLE_RATE, (stereo * 32767).astype(np.int16))
    return len(mono) / SAMPLE_RATE


def _try_say_to_aiff(text: str, dst: Path) -> bool:
    """Generate a dry macOS TTS guide if the local ``say`` command exists."""
    if shutil.which("say") is None:
        return False
    cmd = [
        "say",
        "-v",
        DEFAULT_TTS_VOICE,
        "-r",
        str(TTS_RATE),
        "-o",
        str(dst),
        text,
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError):
        return False
    return dst.exists() and dst.stat().st_size > 0


def _mix_guides(melody_wav: Path, speech_aiff: Path, dst: Path, *, duration_sec: float) -> None:
    """Mix melody guide and dry TTS guide into one cover source WAV."""
    filter_complex = (
        f"[0:a]volume=0.50[m];"
        f"[1:a]volume=0.85,apad,atrim=0:{duration_sec:.3f}[s];"
        "[m][s]amix=inputs=2:duration=first:normalize=0,"
        "loudnorm=I=-18:TP=-2:LRA=8[out]"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(melody_wav),
        "-i",
        str(speech_aiff),
        "-filter_complex",
        filter_complex,
        "-map",
        "[out]",
        "-ar",
        str(SAMPLE_RATE),
        "-ac",
        "2",
        str(dst),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def _verse1_tts_text(row: Any, lyrics: str) -> str:
    """Build TTS guide with phonetic name on the dear-name line."""
    country = getattr(row, "country", "") or ""
    phonetic = getattr(row, "pronunciation", "") or ""
    pron = resolve_pronunciation(row.name, country, phonetic)
    spoken_name = tts_spoken_name(pron)
    lines = []
    for line in lyrics.splitlines():
        stripped = line.strip()
        if not stripped or (stripped.startswith("[") and stripped.endswith("]")):
            continue
        if stripped.lower().startswith("happy birthday dear"):
            lines.append(f"Happy birthday dear {spoken_name}")
        else:
            lines.append(stripped)
    return ". ".join(lines)


def create_verse1_stem(row: Any, *, paths: PipelinePaths) -> dict[str, Any]:
    """Create a deterministic Verse 1 source stem and return metadata."""
    paths.verse1_stem_wav.parent.mkdir(parents=True, exist_ok=True)
    lyrics = build_verse1_lyrics(row.name)
    paths.verse1_lyrics.write_text(lyrics + "\n", encoding="utf-8")

    bpm = row.bpm or DEFAULT_BPM
    text = _verse1_tts_text(row, lyrics)
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        melody_wav = tmp / "melody.wav"
        speech_aiff = tmp / "speech.aiff"
        duration_sec = _write_melody_guide(melody_wav, bpm=bpm)
        used_tts = _try_say_to_aiff(text, speech_aiff)
        if used_tts:
            _mix_guides(melody_wav, speech_aiff, paths.verse1_stem_wav, duration_sec=duration_sec)
        else:
            shutil.copyfile(melody_wav, paths.verse1_stem_wav)

    pron = resolve_pronunciation(
        row.name,
        getattr(row, "country", "") or "",
        getattr(row, "pronunciation", "") or "",
    )
    return {
        "path": str(paths.verse1_stem_wav),
        "lyrics": lyrics,
        "duration_sec": duration_sec,
        "pronunciation": pron.phonetic,
        "tts_voice": DEFAULT_TTS_VOICE if used_tts else None,
    }
