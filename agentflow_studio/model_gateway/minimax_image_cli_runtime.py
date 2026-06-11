from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path
from typing import Any

from agentflow_studio.model_gateway.errors import ModelProviderError
from agentflow_studio.model_gateway.minimax_image_runtime import (
    MINIMAX_MAX_IMAGE_COUNT,
    MINIMAX_MAX_PROMPT_CHARS,
    MINIMAX_MIN_IMAGE_COUNT,
    image_dimensions,
)


def generate_minimax_image_outputs_with_mmx_cli(
    *,
    prompt: str,
    output_root: Path,
    candidate_count: int,
    aspect_ratio: str,
    timeout_sec: float,
    seed: int | None = None,
    region: str | None = None,
    subject_reference_image_path: str | Path | None = None,
    cli_command: str = "mmx",
) -> list[dict[str, Any]]:
    _ensure_mmx_cli_inputs(prompt, candidate_count)
    image_dir = output_root / "image_candidates"
    image_dir.mkdir(parents=True, exist_ok=True)
    command = [
        cli_command,
        "image",
        "generate",
        "--prompt",
        prompt,
        "--aspect-ratio",
        aspect_ratio,
        "--n",
        str(candidate_count),
        "--out-dir",
        str(image_dir),
        "--out-prefix",
        "candidate",
        "--non-interactive",
        "--no-color",
    ]
    if seed is not None:
        command.extend(["--seed", str(seed)])
    if region:
        command.extend(["--region", region])
    if subject_reference_image_path is not None:
        reference_path = Path(subject_reference_image_path)
        if not reference_path.is_file():
            raise ModelProviderError("MiniMax subject reference image is not available")
        command.extend(["--subject-ref", f"type=character,image={reference_path}"])
    _run_mmx(command, timeout_sec)
    return _output_summaries(output_root, image_dir, candidate_count)


def _run_mmx(command: list[str], timeout_sec: float) -> None:
    executable = shutil.which(command[0])
    if executable is None:
        raise ModelProviderError("MiniMax mmx CLI is not installed or not on PATH")
    command = [executable, *command[1:]]
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired as exc:
        raise ModelProviderError("MiniMax mmx CLI request timed out") from exc
    if result.returncode != 0:
        raise ModelProviderError(_safe_cli_failure(result.stderr or result.stdout))


def _output_summaries(output_root: Path, image_dir: Path, candidate_count: int) -> list[dict[str, Any]]:
    paths = sorted(
        path
        for path in image_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    )
    if len(paths) < candidate_count:
        raise ModelProviderError("MiniMax mmx CLI did not save the requested image count")
    outputs: list[dict[str, Any]] = []
    for index, path in enumerate(paths[:candidate_count], start=1):
        target = image_dir / f"candidate_{index:03d}{_safe_suffix(path)}"
        if path != target:
            path.replace(target)
            path = target
        image_bytes = path.read_bytes()
        outputs.append(
            {
                "candidate_id": f"candidate_{index:03d}",
                "image_path": path.relative_to(output_root).as_posix(),
                "byte_count": len(image_bytes),
                "sha256": hashlib.sha256(image_bytes).hexdigest(),
                **image_dimensions(image_bytes),
                "provider_url_persisted": False,
            }
        )
    return outputs


def _ensure_mmx_cli_inputs(prompt: str, candidate_count: int) -> None:
    if not prompt.strip():
        raise ModelProviderError("MiniMax mmx CLI prompt is required")
    if len(prompt) > MINIMAX_MAX_PROMPT_CHARS:
        raise ModelProviderError(f"MiniMax image prompt must be at most {MINIMAX_MAX_PROMPT_CHARS} characters")
    if not MINIMAX_MIN_IMAGE_COUNT <= candidate_count <= MINIMAX_MAX_IMAGE_COUNT:
        raise ModelProviderError(
            f"MiniMax candidate_count must be between {MINIMAX_MIN_IMAGE_COUNT} and {MINIMAX_MAX_IMAGE_COUNT}"
        )


def _safe_suffix(path: Path) -> str:
    suffix = path.suffix.lower()
    return suffix if suffix in {".jpg", ".jpeg", ".png", ".webp"} else ".jpg"


def _safe_cli_failure(value: str) -> str:
    clean = " ".join(str(value or "").split())
    lowered = clean.lower()
    if "api" in lowered or "key" in lowered or "token" in lowered or "authorization" in lowered:
        return "MiniMax mmx CLI authentication or configuration is not ready"
    return clean[:160] or "MiniMax mmx CLI request failed"


__all__ = ("generate_minimax_image_outputs_with_mmx_cli",)
