from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path
from typing import Any

from narratocut.model_gateway.errors import ModelProviderError
from narratostudio.posterflow.schemas import PosterPromptPack


def runtime_subject_reference(image_path: str | Path | None) -> dict[str, Any] | None:
    if image_path is None:
        return None
    path = Path(image_path)
    if not path.is_file():
        raise ModelProviderError(f"MiniMax subject reference image not found: {path}")
    image_bytes = path.read_bytes()
    return {
        "path": path,
        "image_ref": path.name,
        "byte_count": len(image_bytes),
        "sha256": f"sha256:{hashlib.sha256(image_bytes).hexdigest()}",
        "mime_type": image_mime_type(path),
    }


def image_mime_type(image_path: Path) -> str:
    suffix = image_path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".png":
        return "image/png"
    guessed = mimetypes.guess_type(str(image_path))[0]
    if guessed in {"image/jpeg", "image/png"}:
        return guessed
    raise ModelProviderError("MiniMax subject reference image must be JPG, JPEG, or PNG")


def prompt_pack(*, prompt: str, aspect_ratio: str, model: str) -> PosterPromptPack:
    return PosterPromptPack(
        project_id="agentflow_memory_advantage_demo",
        run_id="minimax_image_smoke",
        prompt_id="minimax_image_smoke_prompt",
        target_model_family="minimax_image",
        prompt_language="en",
        positive_prompt=prompt,
        negative_prompt="",
        prompt_sections={"source": "cli_prompt"},
        model_params={"aspect_ratio": aspect_ratio, "model": model},
        context_usage={"company_provider_config_used": True},
        source_refs={"provider_config": "local_company_secret_file"},
    )


def output_summaries(output_root: Path, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    for candidate in candidates:
        image_ref = str(candidate.get("image_path") or "")
        image_path = output_root / image_ref
        image_bytes = image_path.read_bytes()
        outputs.append(
            {
                "candidate_id": candidate.get("candidate_id"),
                "image_path": image_ref,
                "byte_count": len(image_bytes),
                "sha256": hashlib.sha256(image_bytes).hexdigest(),
                "provider_url_persisted": False,
            }
        )
    return outputs
