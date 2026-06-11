from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import struct
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from agentflow_studio.model_gateway.errors import ModelProviderError


MINIMAX_MIN_IMAGE_COUNT = 1
MINIMAX_MAX_IMAGE_COUNT = 9
MINIMAX_MAX_PROMPT_CHARS = 1500


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


def generate_minimax_image_outputs(
    *,
    base_url: str,
    api_key: str,
    model: str,
    prompt: str,
    output_root: Path,
    candidate_count: int,
    aspect_ratio: str,
    timeout_sec: float,
    subject_reference_image_path: str | Path | None = None,
    seed: int | None = None,
) -> list[dict[str, Any]]:
    _ensure_candidate_count(candidate_count)
    _ensure_prompt_length(prompt)
    payload = {
        "model": model,
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "response_format": "base64",
        "n": candidate_count,
        "prompt_optimizer": False,
    }
    if seed is not None:
        payload["seed"] = seed
    if subject_reference_image_path is not None:
        payload["subject_reference"] = [
            {
                "type": "character",
                "image_file": _subject_reference_data_url(Path(subject_reference_image_path)),
            }
        ]
    response = _send_minimax_image_request(
        base_url=base_url,
        api_key=api_key,
        payload=payload,
        timeout_sec=timeout_sec,
    )
    _ensure_success_response(response)
    return _write_output_summaries(output_root, _base64_images(response), candidate_count)


def _send_minimax_image_request(
    *,
    base_url: str,
    api_key: str,
    payload: dict[str, Any],
    timeout_sec: float,
) -> dict[str, Any]:
    request = urllib.request.Request(
        _image_generation_url(base_url),
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        raise ModelProviderError(f"MiniMax image HTTP error {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise ModelProviderError(f"MiniMax image request failed: {exc.reason}") from exc
    try:
        decoded = json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ModelProviderError("MiniMax image response is not valid JSON") from exc
    if not isinstance(decoded, dict):
        raise ModelProviderError("MiniMax image response JSON must be an object")
    return decoded


def _write_output_summaries(
    output_root: Path,
    encoded_images: list[str],
    candidate_count: int,
) -> list[dict[str, Any]]:
    if len(encoded_images) < candidate_count:
        raise ModelProviderError("MiniMax image response missing image_base64 entries")
    image_dir = output_root / "image_candidates"
    image_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[dict[str, Any]] = []
    for index, encoded in enumerate(encoded_images[:candidate_count], start=1):
        candidate_id = f"candidate_{index:03d}"
        try:
            image_bytes = base64.b64decode(encoded)
        except ValueError as exc:
            raise ModelProviderError("MiniMax image_base64 entry is invalid") from exc
        image_ref = f"image_candidates/{candidate_id}{_image_extension(image_bytes)}"
        (output_root / image_ref).write_bytes(image_bytes)
        dimensions = image_dimensions(image_bytes)
        outputs.append(
            {
                "candidate_id": candidate_id,
                "image_path": image_ref,
                "byte_count": len(image_bytes),
                "sha256": hashlib.sha256(image_bytes).hexdigest(),
                **dimensions,
                "provider_url_persisted": False,
            }
        )
    return outputs


def image_dimensions(image_bytes: bytes) -> dict[str, Any]:
    size = _png_dimensions(image_bytes) or _jpeg_dimensions(image_bytes)
    if size is None:
        return {}
    width, height = size
    if width <= 0 or height <= 0:
        return {}
    return {
        "width": width,
        "height": height,
        "aspect_ratio": f"{width}:{height}",
    }


def _png_dimensions(image_bytes: bytes) -> tuple[int, int] | None:
    if not image_bytes.startswith(b"\x89PNG\r\n\x1a\n") or len(image_bytes) < 24:
        return None
    return struct.unpack(">II", image_bytes[16:24])


def _jpeg_dimensions(image_bytes: bytes) -> tuple[int, int] | None:
    if not image_bytes.startswith(b"\xff\xd8"):
        return None
    index = 2
    length = len(image_bytes)
    while index + 9 < length:
        while index < length and image_bytes[index] == 0xFF:
            index += 1
        if index >= length:
            return None
        marker = image_bytes[index]
        index += 1
        if marker in {0xD8, 0xD9}:
            continue
        if index + 2 > length:
            return None
        segment_length = int.from_bytes(image_bytes[index : index + 2], "big")
        if segment_length < 2 or index + segment_length > length:
            return None
        if marker in {
            0xC0,
            0xC1,
            0xC2,
            0xC3,
            0xC5,
            0xC6,
            0xC7,
            0xC9,
            0xCA,
            0xCB,
            0xCD,
            0xCE,
            0xCF,
        }:
            if segment_length < 7:
                return None
            height = int.from_bytes(image_bytes[index + 3 : index + 5], "big")
            width = int.from_bytes(image_bytes[index + 5 : index + 7], "big")
            return width, height
        index += segment_length
    return None


def _base64_images(response: dict[str, Any]) -> list[str]:
    data = response.get("data")
    if not isinstance(data, dict):
        raise ModelProviderError("MiniMax image response missing data object")
    images = data.get("image_base64")
    if not isinstance(images, list):
        raise ModelProviderError("MiniMax image response missing image_base64 entries")
    return [item for item in images if isinstance(item, str) and item]


def _ensure_success_response(response: dict[str, Any]) -> None:
    base_resp = response.get("base_resp")
    if not isinstance(base_resp, dict):
        return
    status_code = base_resp.get("status_code")
    if status_code in {None, 0}:
        return
    message = f"MiniMax image response status_code {status_code}"
    status_msg = base_resp.get("status_msg")
    if isinstance(status_msg, str) and status_msg.strip():
        message = f"{message}: {_safe_status_msg(status_msg)}"
    raise ModelProviderError(message)


def _ensure_candidate_count(candidate_count: int) -> None:
    if MINIMAX_MIN_IMAGE_COUNT <= candidate_count <= MINIMAX_MAX_IMAGE_COUNT:
        return
    raise ModelProviderError(
        f"MiniMax candidate_count must be between {MINIMAX_MIN_IMAGE_COUNT} and {MINIMAX_MAX_IMAGE_COUNT}"
    )


def _ensure_prompt_length(prompt: str) -> None:
    if len(prompt) <= MINIMAX_MAX_PROMPT_CHARS:
        return
    raise ModelProviderError(f"MiniMax image prompt must be at most {MINIMAX_MAX_PROMPT_CHARS} characters")


def _safe_status_msg(value: str) -> str:
    clean = " ".join(value.split())
    return clean.replace("\x00", "")[:120]


def _image_generation_url(base_url: str) -> str:
    clean_base_url = base_url.rstrip("/")
    if clean_base_url.endswith("/v1"):
        return f"{clean_base_url}/image_generation"
    return f"{clean_base_url}/v1/image_generation"


def _image_extension(image_bytes: bytes) -> str:
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if image_bytes.startswith(b"\xff\xd8"):
        return ".jpg"
    raise ModelProviderError("MiniMax image_base64 entry is not a PNG or JPEG image")


def _subject_reference_data_url(image_path: Path) -> str:
    if not image_path.is_file():
        raise ModelProviderError(f"MiniMax subject reference image not found: {image_path}")
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{image_mime_type(image_path)};base64,{encoded}"
