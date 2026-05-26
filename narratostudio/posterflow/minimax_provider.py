from __future__ import annotations

import base64
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from narratocut.model_gateway.errors import ModelProviderError
from narratostudio.posterflow.provider_common import ensure_remote_image_calls_allowed, input_hash
from narratostudio.posterflow.schemas import (
    PosterCandidate,
    PosterCandidatesManifest,
    PosterModelInvocation,
    PosterModelInvocations,
    PosterPromptPack,
)


DEFAULT_MINIMAX_BASE_URL = "https://api.minimax.io"
DEFAULT_MINIMAX_IMAGE_MODEL = "image-01"
MINIMAX_MIN_IMAGE_COUNT = 1
MINIMAX_MAX_IMAGE_COUNT = 9


class MiniMaxImageProvider:
    def __init__(
        self,
        *,
        base_url: str = DEFAULT_MINIMAX_BASE_URL,
        model: str = DEFAULT_MINIMAX_IMAGE_MODEL,
        api_key: str | None = None,
        api_key_env: str | None = None,
        timeout_sec: float = 120.0,
    ) -> None:
        if not base_url:
            raise ModelProviderError("MiniMax image provider requires base_url")
        if not model:
            raise ModelProviderError("MiniMax image provider requires model")
        if api_key == "" and not api_key_env:
            raise ModelProviderError("MiniMax image provider requires an API key")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.api_key_env = api_key_env
        self.timeout_sec = timeout_sec

    @classmethod
    def from_env(cls) -> "MiniMaxImageProvider":
        return cls(
            base_url=os.environ.get("NARRATOCUT_IMAGE_BASE_URL") or DEFAULT_MINIMAX_BASE_URL,
            api_key=os.environ.get("NARRATOCUT_IMAGE_API_KEY"),
            api_key_env="NARRATOCUT_IMAGE_API_KEY",
            model=os.environ.get("NARRATOCUT_IMAGE_MODEL") or DEFAULT_MINIMAX_IMAGE_MODEL,
        )

    def generate(
        self,
        prompt_pack: PosterPromptPack,
        output_dir: str | Path,
        *,
        candidate_count: int,
    ) -> tuple[PosterCandidatesManifest, PosterModelInvocations]:
        ensure_remote_image_calls_allowed()
        _ensure_candidate_count(candidate_count)
        api_key = self._resolve_api_key()
        started = time.perf_counter()
        payload = self._request_payload(prompt_pack, candidate_count)
        response = self._send_request(payload, api_key)
        _ensure_success_response(response)
        candidates = self._write_candidates(response, prompt_pack, Path(output_dir), candidate_count)
        latency_ms = int((time.perf_counter() - started) * 1000)
        invocation = PosterModelInvocation(
            invocation_id=f"{prompt_pack.run_id}_image_generation",
            provider="minimax_image",
            model=self.model,
            prompt_id=prompt_pack.prompt_id,
            input_hash=input_hash(payload),
            params=_safe_params(payload),
            output_files=[candidate.image_path for candidate in candidates],
            latency_ms=latency_ms,
            status="succeeded",
        )
        manifest = PosterCandidatesManifest(
            project_id=prompt_pack.project_id,
            run_id=prompt_pack.run_id,
            prompt_id=prompt_pack.prompt_id,
            candidates=candidates,
            source_refs={"poster_prompt_pack": "poster_prompt_pack.json"},
        )
        invocations = PosterModelInvocations(
            project_id=prompt_pack.project_id,
            run_id=prompt_pack.run_id,
            invocations=[invocation],
        )
        return manifest, invocations

    def _resolve_api_key(self) -> str:
        if self.api_key:
            return self.api_key
        if self.api_key_env:
            value = os.environ.get(self.api_key_env)
            if value:
                return value
        raise ModelProviderError("MiniMax image provider requires an API key")

    def _request_payload(self, prompt_pack: PosterPromptPack, candidate_count: int) -> dict[str, Any]:
        return {
            "model": self.model,
            "prompt": _combined_prompt(prompt_pack),
            "aspect_ratio": _aspect_ratio(prompt_pack),
            "response_format": "base64",
            "n": candidate_count,
            "prompt_optimizer": bool(prompt_pack.model_params.get("prompt_optimizer", False)),
        }

    def _send_request(self, payload: dict[str, Any], api_key: str) -> dict[str, Any]:
        request = urllib.request.Request(
            _image_generation_url(self.base_url),
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_sec) as response:
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

    def _write_candidates(
        self,
        response: dict[str, Any],
        prompt_pack: PosterPromptPack,
        output_dir: Path,
        candidate_count: int,
    ) -> list[PosterCandidate]:
        images = _base64_images(response)
        if len(images) < candidate_count:
            raise ModelProviderError("MiniMax image response missing image_base64 entries")
        image_dir = output_dir / "image_candidates"
        image_dir.mkdir(parents=True, exist_ok=True)
        candidates: list[PosterCandidate] = []
        response_id = str(response.get("id") or "")
        for index, encoded in enumerate(images[:candidate_count], start=1):
            candidate_id = f"candidate_{index:03d}"
            relative_path = f"image_candidates/{candidate_id}.png"
            try:
                image_bytes = base64.b64decode(encoded)
            except ValueError as exc:
                raise ModelProviderError("MiniMax image_base64 entry is invalid") from exc
            (output_dir / relative_path).write_bytes(image_bytes)
            candidates.append(
                PosterCandidate(
                    candidate_id=candidate_id,
                    image_path=relative_path,
                    prompt_id=prompt_pack.prompt_id,
                    provider="minimax_image",
                    metadata={
                        "response_source": "image_base64",
                        "response_id_hash": _hash_value(response_id) if response_id else "",
                    },
                )
            )
        return candidates


def _combined_prompt(prompt_pack: PosterPromptPack) -> str:
    prompt = prompt_pack.positive_prompt.strip()
    negative = prompt_pack.negative_prompt.strip()
    if negative:
        return f"{prompt}\n\nAvoid: {negative}"
    return prompt


def _aspect_ratio(prompt_pack: PosterPromptPack) -> str:
    raw = prompt_pack.model_params.get("aspect_ratio")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return "3:4"


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
    raise ModelProviderError(f"MiniMax image response status_code {status_code}")


def _ensure_candidate_count(candidate_count: int) -> None:
    if MINIMAX_MIN_IMAGE_COUNT <= candidate_count <= MINIMAX_MAX_IMAGE_COUNT:
        return
    raise ModelProviderError(
        f"MiniMax candidate_count must be between {MINIMAX_MIN_IMAGE_COUNT} and {MINIMAX_MAX_IMAGE_COUNT}"
    )


def _image_generation_url(base_url: str) -> str:
    if base_url.endswith("/v1"):
        return f"{base_url}/image_generation"
    return f"{base_url}/v1/image_generation"


def _safe_params(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "n": payload.get("n"),
        "aspect_ratio": payload.get("aspect_ratio"),
        "response_format": payload.get("response_format"),
        "prompt_optimizer": payload.get("prompt_optimizer"),
    }


def _hash_value(value: str) -> str:
    encoded = value.encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"
