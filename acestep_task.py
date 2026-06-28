"""Shared ACE-Step task submit, poll, and download helper."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from batch_birthday.api_client import (
    download_audio,
    parse_track_result,
    poll_task,
    submit_task,
)


def generate_to_file(
    payload: dict[str, Any],
    *,
    api_base: str,
    api_key: str,
    out_path: Path,
    label: str = "task",
) -> dict[str, Any]:
    """Run one ACE-Step job and write the first audio track to out_path."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    task_id = submit_task(api_base, payload, api_key)
    print(f"POLL ({label}): {task_id}")
    result = poll_task(api_base, task_id, api_key)
    tracks = parse_track_result(result)
    if not tracks:
        raise RuntimeError(f"No audio tracks for {label} ({task_id})")
    download_audio(api_base, tracks[0]["file"], str(out_path), api_key)
    return {
        "task_id": task_id,
        "track": tracks[0],
        "payload": payload,
    }
