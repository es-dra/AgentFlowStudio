from __future__ import annotations

import base64
import json

from agentflow_studio.production.posterflow.schemas import PosterPromptPack


PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)
PNG_B64 = base64.b64encode(PNG_BYTES).decode("ascii")
JPEG_BYTES = b"\xff\xd8\xff\xd9"
JPEG_B64 = base64.b64encode(JPEG_BYTES).decode("ascii")


class FakeResponse:
    def __init__(self, payload: dict | bytes) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        return False

    def read(self) -> bytes:
        if isinstance(self.payload, bytes):
            return self.payload
        return json.dumps(self.payload).encode("utf-8")


def prompt_pack() -> PosterPromptPack:
    return PosterPromptPack(
        project_id="cyber_xianxia_001",
        run_id="run_001",
        prompt_id="poster_prompt_001",
        target_model_family="openai_compatible_image",
        prompt_language="en",
        positive_prompt="cinematic poster, low saturation, premium composition",
        negative_prompt="cheap mobile game ad, oversaturated neon",
        prompt_sections={"style": "cinematic", "composition": "centered"},
        model_params={"aspect_ratio": "3:4", "num_candidates": 3},
        context_usage={"project_prefix_used": False, "preference_profile_used": False},
        source_refs={"poster_plan": "poster_plan.json"},
    )
