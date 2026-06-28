"""FFmpeg helpers to stitch generated song segments."""

from __future__ import annotations

from batch_birthday.audio_merge import crossfade_merge as stitch_crossfade

__all__ = ["stitch_crossfade"]
