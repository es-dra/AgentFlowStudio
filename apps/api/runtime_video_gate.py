from __future__ import annotations

import os

from apps.api.runtime_video_constants import REMOTE_TRUE_VALUES, REMOTE_VIDEO_ENV


def video_gate(required_gate: str) -> dict[str, str]:
    status = "ready_not_run" if os.environ.get(required_gate, "").strip().lower() in REMOTE_TRUE_VALUES else "blocked"
    return {"capability": "video", "env": required_gate, "status": status}


def gate_closed_block(required_gate: str) -> dict[str, str]:
    return {
        "block_id": "remote_video_gate_closed",
        "reason": f"Set {required_gate}=true only for an explicit video provider smoke.",
        "required_gate": required_gate,
    }


def provider_not_ready_block(reason: str) -> dict[str, str]:
    return {
        "block_id": "remote_video_provider_not_ready",
        "reason": safe_video_error(reason),
        "required_gate": REMOTE_VIDEO_ENV,
    }


def safe_video_error(value: str) -> str:
    lowered = value.lower()
    if "api" in lowered or "key" in lowered or "secret" in lowered or "token" in lowered:
        return "Video provider configuration is not ready."
    return value[:160]
