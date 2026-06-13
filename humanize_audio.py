"""Post-process generated MP3s for a more natural, listenable master.

Default ``distribute`` style: distributor-hardened master — breaks neural decoder
fingerprints, restores stereo/harmonic variation, no echo or synthetic beds.
``natural`` is a lighter pass; ``party`` keeps the legacy room/clap/echo mix.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from batch_birthday.batch_variation import MasterVariation, build_distribute_filter

SAMPLE_RATE = 48000
HUMANIZE_STYLES = ("natural", "distribute", "party")


def _write_room_bed_wav(path: Path, duration_sec: float) -> None:
    """Write a subtle pink-noise room tone WAV via ffmpeg."""
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"anoisesrc=d={duration_sec}:c=pink:r={SAMPLE_RATE}",
        "-af",
        "highpass=f=120,lowpass=f=3500,volume=-38dB",
        str(path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def _write_clap_bed_wav(path: Path, duration_sec: float, bpm: int = 128) -> None:
    """Synthesize party hand-clap hits on beats 1 and 3 every two bars."""
    beat_sec = 60.0 / bpm
    bar_sec = beat_sec * 4
    sample_count = int(duration_sec * SAMPLE_RATE)
    audio = np.zeros(sample_count, dtype=np.float64)
    clap_len = int(0.045 * SAMPLE_RATE)

    offset = 0.0
    while offset < duration_sec:
        for beat_idx in (0, 2):
            start = int((offset + beat_idx * beat_sec) * SAMPLE_RATE)
            end = min(start + clap_len, sample_count)
            if start >= sample_count:
                continue
            length = end - start
            envelope = np.exp(-np.linspace(0, 10, length))
            burst = np.random.default_rng(start).normal(0, 1, length) * envelope
            audio[start:end] += burst * 0.35
        offset += bar_sec * 2

    peak = float(np.max(np.abs(audio))) or 1.0
    audio = (audio / peak) * 0.55
    wavfile.write(path, SAMPLE_RATE, (audio * 32767).astype(np.int16))


def _probe_duration_sec(path: Path) -> float:
    """Return audio duration using ffprobe."""
    import json

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(path),
    ]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return float(json.loads(result.stdout)["format"]["duration"])


def _natural_master_af() -> str:
    """Clean human master: micro pitch drift + de-harsh EQ, no echo/reverb/claps."""
    return (
        "asetrate=48000*0.982,aresample=48000,atempo=1.0183,"
        "equalizer=f=2800:t=q:w=1.2:g=-1.2,"
        "equalizer=f=6200:t=h:w=0.8:g=-2.0,"
        "loudnorm=I=-14:TP=-1.0:LRA=10"
    )


def _distribute_master_af() -> str:
    """Distributor-hardened: breaks decoder fingerprints + synthetic stereo cues."""
    return (
        "asetrate=48000*0.982,aresample=48000,atempo=1.0183,"
        "equalizer=f=2800:t=q:w=1.2:g=-1.2,"
        "equalizer=f=6200:t=h:w=0.8:g=-2.0,"
        "asoftclip=type=tanh:threshold=0.92:output=1,"
        "extrastereo=m=1.015,"
        "loudnorm=I=-14:TP=-1.0:LRA=11"
    )


def _party_master_af() -> str:
    """Warmer party master with light ambience (legacy style)."""
    return (
        "aecho=0.6:0.72:40:0.25,"
        "compand=attacks=0.4:decays=0.7:points=-80/-80|-18/-12|-6/-4|0/-2,"
        "loudnorm=I=-14:TP=-1.2:LRA=13"
    )


def _run_ffmpeg_filter(
    src: Path,
    dst: Path,
    *,
    filter_complex: str,
    inputs: list[str] | None = None,
) -> None:
    """Execute ffmpeg with a filter graph ending in ``[out]``."""
    cmd = [
        "ffmpeg",
        "-y",
        *(inputs or ["-i", str(src)]),
        "-filter_complex",
        filter_complex,
        "-map",
        "[out]",
        "-ar",
        str(SAMPLE_RATE),
        "-c:a",
        "libmp3lame",
        "-b:a",
        "192k",
        str(dst),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def humanize_mp3(
    src: Path,
    dst: Path,
    *,
    duration_sec: float | None = None,
    bpm: int = 128,
    vocal_overlay: Path | None = None,
    style: str = "distribute",
    variation: MasterVariation | None = None,
) -> Path:
    """Master a batch MP3 for a more human, less synthetic listen.

    Args:
        src: Source MP3 (typically mastered batch output).
        dst: Output humanized MP3 path.
        duration_sec: Track length; probed from *src* when omitted.
        bpm: Tempo for clap placement (``party`` style only).
        vocal_overlay: Optional WAV/MP3 of live vocals to blend on top.
        style: ``distribute`` (default), ``natural``, or ``party``.
        variation: Optional per-name mastering fingerprint (``distribute`` only).

    Returns:
        Path to the written humanized MP3.
    """
    if style not in HUMANIZE_STYLES:
        raise ValueError(f"Unknown humanize style: {style}")

    src = src.resolve()
    dst = dst.resolve()
    dst.parent.mkdir(parents=True, exist_ok=True)
    duration = duration_sec if duration_sec is not None else _probe_duration_sec(src)

    if style in ("natural", "distribute"):
        if style == "natural":
            master_af = _natural_master_af()
        elif variation is not None:
            master_af = build_distribute_filter(variation)
        else:
            master_af = _distribute_master_af()
        merge_label = "[0:a]"
        filter_parts: list[str] = []
        inputs = ["-i", str(src)]

        if vocal_overlay is not None and vocal_overlay.exists():
            inputs.extend(["-i", str(vocal_overlay.resolve())])
            filter_parts.append("[1:a]volume=0.42,highpass=f=90[vox]")
            filter_parts.append("[0:a][vox]amix=inputs=2:duration=first[voxmix]")
            merge_label = "[voxmix]"

        filter_parts.append(f"{merge_label}{master_af}[out]")
        _run_ffmpeg_filter(src, dst, filter_complex=";".join(filter_parts), inputs=inputs)
        return dst

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        room_wav = tmp / "room.wav"
        clap_wav = tmp / "claps.wav"
        _write_room_bed_wav(room_wav, duration)
        _write_clap_bed_wav(clap_wav, duration, bpm=bpm)

        inputs = ["-i", str(src), "-i", str(room_wav), "-i", str(clap_wav)]
        filter_parts = [
            "[1:a]volume=0.55[room]",
            "[2:a]volume=0.45[clap]",
            "[0:a][room][clap]amix=inputs=3:duration=first:dropout_transition=0[mix]",
        ]
        merge_label = "[mix]"

        if vocal_overlay is not None and vocal_overlay.exists():
            inputs.extend(["-i", str(vocal_overlay.resolve())])
            filter_parts.append("[3:a]volume=0.42,highpass=f=90[vox]")
            filter_parts.append(f"{merge_label}[vox]amix=inputs=2:duration=first[voxmix]")
            merge_label = "[voxmix]"

        filter_parts.append(f"{merge_label}{_party_master_af()}[out]")
        _run_ffmpeg_filter(src, dst, filter_complex=";".join(filter_parts), inputs=inputs)

    return dst


def main() -> None:
    """CLI entry for one-off humanization."""
    import argparse

    parser = argparse.ArgumentParser(description="Humanize a batch_birthday MP3")
    parser.add_argument("mp3", type=Path, help="Source MP3")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output path (default: <name>_human.mp3)",
    )
    parser.add_argument("--bpm", type=int, default=128)
    parser.add_argument(
        "--style",
        choices=HUMANIZE_STYLES,
        default="distribute",
        help="distribute = hardened for DSP upload (default); natural = light; party = legacy",
    )
    parser.add_argument(
        "--vocal-overlay",
        type=Path,
        default=None,
        help="Optional live vocal recording to blend",
    )
    args = parser.parse_args()
    out = args.output or args.mp3.with_name(f"{args.mp3.stem}_human.mp3")
    humanize_mp3(
        args.mp3,
        out,
        bpm=args.bpm,
        vocal_overlay=args.vocal_overlay,
        style=args.style,
    )
    print(f"HUMANIZED ({args.style}): {out}")


if __name__ == "__main__":
    main()
