from __future__ import annotations

import base64
import hashlib
import urllib.error
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from agentflow_studio.model_gateway.errors import ModelConfigError, ModelGatewayError
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
MAX_EDIT_IMAGE_COUNT = 4
MAX_EDIT_IMAGE_BYTES = 8 * 1024 * 1024
MAX_EDIT_TOTAL_BYTES = 24 * 1024 * 1024


def openai_images_payload(*, service: dict[str, Any], model: str, request: ProviderDispatchRequest) -> dict[str, Any]:
    if request.image_operation == "edit" or request.edit_source_image_path is not None:
        return _openai_images_edit_payload(service=service, model=model, request=request)
    if request.reference_image_paths or request.subject_reference_image_path is not None:
        raise ModelGatewayError("Image relay generation route does not accept reference images")
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
        _merge_extra_body(payload, extra_body)
    return payload


def _openai_images_edit_payload(*, service: dict[str, Any], model: str, request: ProviderDispatchRequest) -> dict[str, Any]:
    image_paths = _edit_image_paths(request)
    if not image_paths:
        raise ModelGatewayError("Image relay edit requires a source image")
    fields: dict[str, Any] = {
        "model": model,
        "prompt": request.prompt,
        "n": request.candidate_count,
        "size": str(service.get("size") or ASPECT_RATIO_SIZES.get(request.aspect_ratio) or "1024x1024"),
        "quality": str(service.get("quality") or "low"),
        "output_format": str(service.get("output_format") or "png"),
    }
    descriptor = service.get("descriptor") if isinstance(service.get("descriptor"), dict) else {}
    edit_capabilities = (
        descriptor.get("image_edit_capabilities")
        if isinstance(descriptor.get("image_edit_capabilities"), dict)
        else {}
    )
    supported_fidelity = {
        str(item) for item in edit_capabilities.get("input_fidelity_modes", []) if str(item)
    }
    configured_fidelity = str(service.get("input_fidelity") or request.image_input_fidelity or "").strip()
    if configured_fidelity and configured_fidelity not in supported_fidelity:
        raise ModelGatewayError("Image relay input fidelity is not declared by the provider descriptor")
    if configured_fidelity:
        fields["input_fidelity"] = configured_fidelity
    extra_body = service.get("extra_body")
    if isinstance(extra_body, dict):
        _merge_extra_body(fields, extra_body)
    field_name = str(service.get("edit_image_field_name") or "image")
    return {
        "__transport": "multipart",
        "__endpoint": _edit_endpoint(service),
        "fields": fields,
        "files": [_image_file_part(field_name, path, index) for index, path in enumerate(image_paths, start=1)],
    }


def _merge_extra_body(payload: dict[str, Any], extra_body: dict[str, Any]) -> None:
    for raw_key, value in extra_body.items():
        if value in (None, "", []):
            continue
        key = str(raw_key)
        if key in payload:
            if value != payload[key]:
                raise ModelConfigError(f"Image relay extra_body cannot override request field: {key}")
            continue
        payload[key] = value


def _edit_endpoint(service: dict[str, Any]) -> str:
    configured = str(service.get("edit_endpoint") or "").strip()
    if configured:
        return configured
    endpoint = str(service.get("endpoint") or "").strip()
    if endpoint.endswith("/generations"):
        return f"{endpoint.removesuffix('/generations')}/edits"
    return "/images/edits"


def _edit_image_paths(request: ProviderDispatchRequest) -> list[Path | str]:
    values: list[Path | str] = []
    if request.edit_source_image_path is not None:
        values.append(request.edit_source_image_path)
    values.extend(request.edit_reference_image_paths or request.reference_image_paths)
    seen: set[str] = set()
    result: list[Path | str] = []
    for value in values:
        key = str(Path(value))
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(value)
    if len(result) > MAX_EDIT_IMAGE_COUNT:
        raise ModelGatewayError(f"Image relay edit accepts at most {MAX_EDIT_IMAGE_COUNT} reference images")
    total_bytes = 0
    for value in result:
        image_path = Path(value)
        if not image_path.is_file():
            raise ModelGatewayError("Image relay edit source image is missing")
        byte_count = image_path.stat().st_size
        if byte_count > MAX_EDIT_IMAGE_BYTES:
            raise ModelGatewayError("Image relay edit reference exceeds the per-file byte limit")
        total_bytes += byte_count
    if total_bytes > MAX_EDIT_TOTAL_BYTES:
        raise ModelGatewayError("Image relay edit references exceed the total byte limit")
    return result


def _image_file_part(field_name: str, path: Path | str, index: int) -> dict[str, Any]:
    image_path = Path(path)
    if not image_path.is_file():
        raise ModelGatewayError("Image relay edit source image is missing")
    image_bytes = image_path.read_bytes()
    if len(image_bytes) > MAX_EDIT_IMAGE_BYTES:
        raise ModelGatewayError("Image relay edit reference exceeds the per-file byte limit")
    mime_type = _mime_type_for_bytes(image_bytes)
    if not mime_type:
        raise ModelGatewayError("Image relay edit source image must be PNG or JPEG")
    safe_suffix = ".png" if mime_type == "image/png" else ".jpg"
    return {
        "field_name": field_name,
        "filename": f"reference_{index:03d}{safe_suffix}",
        "mime_type": mime_type,
        "byte_count": len(image_bytes),
        "sha256": hashlib.sha256(image_bytes).hexdigest(),
        "data": image_bytes,
    }


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
                "status": "succeeded",
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
    if parsed.scheme not in {"https", "http"} or not host:
        raise ModelGatewayError("API relay image URL must use HTTP(S)")
    if not allowed_url_hosts or not _host_allowed(host, allowed_url_hosts):
        raise ModelGatewayError(f"API relay image URL host is not allowed: {host}")
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "image/png,image/jpeg,image/webp,*/*",
            "User-Agent": "AgentFlowStudio/1.0 media-artifact-fetcher",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            image_bytes = response.read(MAX_IMAGE_DOWNLOAD_BYTES + 1)
    except TimeoutError as exc:
        raise ModelGatewayError("API relay image URL download timed out") from exc
    except urllib.error.HTTPError as exc:
        raise ModelGatewayError(f"API relay image URL download HTTP error {exc.code} from host: {host}") from exc
    except urllib.error.URLError as exc:
        if _looks_like_timeout(str(exc.reason)):
            raise ModelGatewayError("API relay image URL download timed out") from exc
        raise ModelGatewayError(f"API relay image URL download failed from host: {host}") from exc
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


def _mime_type_for_bytes(image_bytes: bytes) -> str:
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image_bytes.startswith(b"\xff\xd8"):
        return "image/jpeg"
    return ""


def _looks_like_timeout(value: str) -> bool:
    lowered = value.lower()
    return "timed out" in lowered or "timeout" in lowered


__all__ = ("openai_images_payload", "write_image_outputs")
