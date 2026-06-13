"""HTTP client for ACE-Step release_task and query_result endpoints."""

from __future__ import annotations

import json
import time
from typing import Any

import requests

DEFAULT_POLL_INTERVAL_SEC = 15
DEFAULT_POLL_TIMEOUT_SEC = 60 * 60


def ensure_llm_ready(api_base: str, api_key: str = "") -> None:
    """Raise if the API LLM is not loaded (required for sung lyrics)."""
    response = requests.get(
        f"{api_base}/health",
        headers=api_headers(api_key),
        timeout=30,
    )
    response.raise_for_status()
    data = response.json().get("data", {})
    if not data.get("llm_initialized"):
        raise RuntimeError(
            "ACE-Step LLM is not loaded — songs will be instrumental only. "
            "Restart the API with ACESTEP_INIT_LLM=true and "
            "LM_MODEL_PATH=acestep-5Hz-lm-1.7B, or POST /v1/init with init_llm=true."
        )


def api_headers(api_key: str = "") -> dict[str, str]:
    """Build request headers with optional bearer token."""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def submit_task(
    api_base: str,
    payload: dict[str, Any],
    api_key: str = "",
) -> str:
    """Submit a generation job and return task_id."""
    response = requests.post(
        f"{api_base}/release_task",
        headers=api_headers(api_key),
        json=payload,
        timeout=120,
    )
    response.raise_for_status()
    body = response.json()
    return body["data"]["task_id"]


def poll_task(
    api_base: str,
    task_id: str,
    api_key: str = "",
    poll_interval_sec: int = DEFAULT_POLL_INTERVAL_SEC,
    poll_timeout_sec: int = DEFAULT_POLL_TIMEOUT_SEC,
) -> dict[str, Any]:
    """Poll until task succeeds (status 1) or fails (status 2)."""
    deadline = time.time() + poll_timeout_sec
    while time.time() < deadline:
        response = requests.post(
            f"{api_base}/query_result",
            headers=api_headers(api_key),
            json={"task_id_list": [task_id]},
            timeout=120,
        )
        response.raise_for_status()
        item = response.json()["data"][0]
        status = item["status"]
        if status == 1:
            return item
        if status == 2:
            raise RuntimeError(f"Generation failed for task {task_id}")
        time.sleep(poll_interval_sec)
    raise TimeoutError(f"Timed out after {poll_timeout_sec}s for task {task_id}")


def download_audio(
    api_base: str,
    audio_path: str,
    dest_path: str,
    api_key: str = "",
) -> None:
    """Download generated audio from /v1/audio path."""
    url = audio_path if audio_path.startswith("http") else f"{api_base}{audio_path}"
    response = requests.get(url, headers=api_headers(api_key), timeout=600)
    response.raise_for_status()
    with open(dest_path, "wb") as handle:
        handle.write(response.content)


def parse_track_result(result_item: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse the JSON string in query_result.result into track dicts."""
    raw = result_item.get("result", "[]")
    if isinstance(raw, str):
        return json.loads(raw)
    return raw
