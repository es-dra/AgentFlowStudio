from __future__ import annotations

import base64
import hashlib
import urllib.error
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from agentflow_studio.model_gateway.errors import ModelGatewayError
from agentflow_studio.model_gateway.image_utils import image_dimensions, image_extension

if TYPE_CHECKING:
    from agentflow_studio.model_gateway.provider_adapter import ProviderDispatchRequest


ASPECT_RATIO_SIZES = {
    "1:1": "1024x1024",
    "4:3": "1280x960",
    "3:4": "960x1280",
    "16:9": "1280x720",
    "9:16": "720x1280",
}
MAX_IMAGE_DOWNLOAD_BYTES = 32 * 1024 * 1024


def openai_images_payload(*, service: dict[str, Any], model: str, request: ProviderDispatchRequest) -> dict[str, Any]:
    if request.reference_image_paths or request.subject_reference_image_path is not None:
        raise ModelGatewayError("OpenAI Images relay generation does not accept reference images")
    payload: dict[str, Any] = {
        "model": model,
        "prompt": request.prompt,
        "n": request.candidate_count,
        "size": str(service.get("size") or ASPECT_RATIO_SIZES.get(request.aspect_ratio) or "1024x1024"),
        "quality": str(service.get("quality") or "low"),
        "output_format": str(service.get("output_format") or "png"),
    }
    extra_body = service.get("extra_body")
    if isinstance(extra_body, dict):
        for key, value in extra_body.items():
            if value not in (None, "", []):
                payload[str(key)] = value
    return payload


def write_image_outputs(
    output_root: Path,
    response: dict[str, Any],
    candidate_count: int,
    *,
    allowed_url_hosts: tuple[str, ...] = (),
    download_timeout_sec: float = 180.0,
) -> list[dict[str, Any]]:
    images = _response_images(response)
    if len(images) < candidate_count:
        raise ModelGatewayError("API relay image response missing image entries")
    image_dir = output_root / "image_candidates"
    image_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[dict[str, Any]] = []
    for index, item in enumerate(images[:candidate_count], start=1):
        image_bytes = _decode_image_item(
            item,
            allowed_url_hosts=allowed_url_hosts,
            download_timeout_sec=download_timeout_sec,
        )
        extension = image_extension(image_bytes)
        if not extension:
            raise ModelGatewayError("API relay image response must be PNG or JPEG")
        candidate_id = f"candidate_{index:03d}"
        image_ref = f"image_candidates/{candidate_id}{extension}"
        (output_root / image_ref).write_bytes(image_bytes)
        outputs.append(
            {
                "candidate_id": candidate_id,
                "image_path": image_ref,
                "byte_count": len(image_bytes),
                "sha256": hashlib.sha256(image_bytes).hexdigest(),
                **image_dimensions(image_bytes),
                "provider_url_persisted": False,
            }
        )
    return outputs


def _response_images(response: dict[str, Any]) -> list[Any]:
    for key in ("images", "outputs", "candidates"):
        value = response.get(key)
        if isinstance(value, list):
            return value
    data = response.get("data")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        value = data.get("images") or data.get("image_base64")
        if isinstance(value, list):
            return value
    if isinstance(response.get("image_base64"), str):
        return [response["image_base64"]]
    return []


def _decode_image_item(item: Any, *, allowed_url_hosts: tuple[str, ...], download_timeout_sec: float) -> bytes:
    if isinstance(item, str):
        encoded = item
    elif isinstance(item, dict):
        url = str(item.get("url") or "").strip()
        if url:
            return _download_image_url(url, allowed_url_hosts=allowed_url_hosts, timeout_sec=download_timeout_sec)
        encoded = str(item.get("data_base64") or item.get("image_base64") or item.get("base64") or item.get("b64_json") or "")
    else:
        encoded = ""
    try:
        return base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as exc:
        raise ModelGatewayError("API relay image response contains invalid base64") from exc


def _download_image_url(url: str, *, allowed_url_hosts: tuple[str, ...], timeout_sec: float) -> bytes:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host:
        raise ModelGatewayError("API relay image URL must use HTTPS")
    if not allowed_url_hosts or not _host_allowed(host, allowed_url_hosts):
        raise ModelGatewayError("API relay image URL host is not allowed")
    request = urllib.request.Request(url, headers={"Accept": "image/png,image/jpeg,image/webp,*/*"})
    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            image_bytes = response.read(MAX_IMAGE_DOWNLOAD_BYTES + 1)
    except urllib.error.URLError as exc:
        raise ModelGatewayError("API relay image URL download failed") from exc
    if len(image_bytes) > MAX_IMAGE_DOWNLOAD_BYTES:
        raise ModelGatewayError("API relay image URL download exceeded size limit")
    return image_bytes


def _host_allowed(host: str, allowed_url_hosts: tuple[str, ...]) -> bool:
    for allowed in allowed_url_hosts:
        item = allowed.lower().strip()
        if not item:
            continue
        if item.startswith(".") and (host == item[1:] or host.endswith(item)):
            return True
        if host == item:
            return True
    return False


__all__ = ("openai_images_payload", "write_image_outputs")
