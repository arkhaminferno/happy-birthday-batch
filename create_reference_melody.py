"""Synthesize a fast Happy Birthday reference WAV for ACE-Step cover mode."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from scipy.io import wavfile

SAMPLE_RATE = 48000
BPM = 132
BEAT_SEC = 60.0 / BPM

# Classic "Happy Birthday to You" melody in C major (MIDI note numbers).
_MELODY = [
    67, 67, 69, 67, 72, 71,
    67, 67, 69, 67, 74, 72,
    67, 67, 67, 76, 72, 71, 69,
    75, 75, 76, 72, 74, 72,
]

# Quarter-note rhythm for a lively 3/4 waltz feel (beats per note).
_NOTE_BEATS = [1, 1, 1, 1, 2, 2, 1, 1, 1, 1, 2, 2, 1, 1, 1, 1, 2, 1, 1, 2, 2, 1, 1, 2, 2]


def _midi_to_hz(note: int) -> float:
    return 440.0 * (2.0 ** ((note - 69) / 12.0))


def _tone(freq: float, duration_sec: float, volume: float = 0.35) -> np.ndarray:
    """Simple piano-like tone with a quick decay."""
    n = max(1, int(SAMPLE_RATE * duration_sec))
    t = np.linspace(0, duration_sec, n, endpoint=False)
    wave = np.sin(2 * np.pi * freq * t)
    wave += 0.35 * np.sin(2 * np.pi * freq * 2 * t)
    env = np.exp(-3.0 * t / max(duration_sec, 0.05))
    return (wave * env * volume).astype(np.float32)


def build_phrase() -> np.ndarray:
    """Build one pass of the Happy Birthday melody."""
    chunks: list[np.ndarray] = []
    for note, beats in zip(_MELODY, _NOTE_BEATS):
        dur = beats * BEAT_SEC
        if note <= 0:
            chunks.append(np.zeros(int(SAMPLE_RATE * dur), dtype=np.float32))
        else:
            chunks.append(_tone(_midi_to_hz(note), dur))
    return np.concatenate(chunks)


def build_reference(
    *,
    repeats: int | None = None,
    target_duration_sec: float | None = None,
    gap_sec: float = 0.35,
) -> np.ndarray:
    """Repeat the phrase; target_duration_sec loops until ~full song length."""
    phrase = build_phrase()
    gap = np.zeros(int(SAMPLE_RATE * gap_sec), dtype=np.float32)
    phrase_sec = len(phrase) / SAMPLE_RATE
    cycle_sec = phrase_sec + gap_sec

    if target_duration_sec is not None:
        repeats = max(1, int(np.ceil(target_duration_sec / cycle_sec)))
    elif repeats is None:
        repeats = 4

    parts: list[np.ndarray] = []
    for i in range(repeats):
        parts.append(phrase)
        if i < repeats - 1:
            parts.append(gap)
    stereo = np.stack([np.concatenate(parts)] * 2, axis=1)
    peak = np.max(np.abs(stereo))
    if peak > 0:
        stereo = stereo / peak * 0.9
    return stereo


def main() -> None:
    """Write the reference WAV used as cover source audio."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "templates" / "audio" / "happy_birthday_reference.wav",
    )
    parser.add_argument("--repeats", type=int, default=0, help="Fixed repeat count (0 = use --duration)")
    parser.add_argument(
        "--duration",
        type=float,
        default=240.0,
        help="Target reference length in seconds (default: 240 for full song cover)",
    )
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.repeats > 0:
        audio = build_reference(repeats=args.repeats)
    else:
        audio = build_reference(target_duration_sec=args.duration)
    wavfile.write(str(args.output), SAMPLE_RATE, (audio * 32767).astype(np.int16))
    duration = len(audio) / SAMPLE_RATE
    print(f"Wrote {args.output} ({duration:.1f}s, {BPM} BPM)")


if __name__ == "__main__":
    main()
