from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING, Any

from agentflow_studio.model_gateway.errors import ModelProviderError
from agentflow_studio.production.posterflow.provider_common import ensure_remote_image_calls_allowed, input_hash
from agentflow_studio.production.posterflow.schemas import (
    PosterCandidate,
    PosterCandidatesManifest,
    PosterModelInvocation,
    PosterModelInvocations,
    PosterPromptPack,
)

if TYPE_CHECKING:
    from agentflow_studio.production.posterflow.minimax_provider import MiniMaxImageProvider


IMAGE_PROVIDER_ENV = "AFS_IMAGE_PROVIDER"
MINIMAX_PROVIDER = "minimax"
OPENAI_COMPATIBLE_PROVIDER = "openai_compatible"


class OpenAICompatibleImageProvider:
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        api_key_env: str | None = None,
        timeout_sec: float = 120.0,
    ) -> None:
        if not base_url:
            raise ModelProviderError("OpenAI-compatible image provider requires base_url")
        if not model:
            raise ModelProviderError("OpenAI-compatible image provider requires model")
        if api_key == "" and not api_key_env:
            raise ModelProviderError("OpenAI-compatible image provider requires an API key")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.api_key_env = api_key_env
        self.timeout_sec = timeout_sec

    @classmethod
    def from_env(cls) -> "OpenAICompatibleImageProvider":
        return cls(
            base_url=os.environ.get("AFS_IMAGE_BASE_URL", ""),
            api_key=os.environ.get("AFS_IMAGE_API_KEY"),
            api_key_env="AFS_IMAGE_API_KEY",
            model=os.environ.get("AFS_IMAGE_MODEL", ""),
        )

    def generate(
        self,
        prompt_pack: PosterPromptPack,
        output_dir: str | Path,
        *,
        candidate_count: int,
    ) -> tuple[PosterCandidatesManifest, PosterModelInvocations]:
        self._ensure_remote_calls_allowed()
        api_key = self._resolve_api_key()
        started = time.perf_counter()
        payload = self._request_payload(prompt_pack, candidate_count)
        response = self._send_request(payload, api_key)
        candidates = self._write_candidates(response, prompt_pack, Path(output_dir), candidate_count)
        latency_ms = int((time.perf_counter() - started) * 1000)
        invocation = PosterModelInvocation(
            invocation_id=f"{prompt_pack.run_id}_image_generation",
            provider="openai_compatible_image",
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
        raise ModelProviderError("OpenAI-compatible image provider requires an API key")

    def _ensure_remote_calls_allowed(self) -> None:
        ensure_remote_image_calls_allowed()

    def _request_payload(self, prompt_pack: PosterPromptPack, candidate_count: int) -> dict[str, Any]:
        size = str(prompt_pack.model_params.get("size") or "1024x1536")
        prompt = f"{prompt_pack.positive_prompt}\n\nAvoid: {prompt_pack.negative_prompt}".strip()
        return {
            "model": self.model,
            "prompt": prompt,
            "n": candidate_count,
            "size": size,
            "response_format": "b64_json",
        }

    def _send_request(self, payload: dict[str, Any], api_key: str) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{self.base_url}/images/generations",
            data=json.dumps(payload).encode("utf-8"),
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
            raise ModelProviderError(f"OpenAI-compatible image HTTP error {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise ModelProviderError(f"OpenAI-compatible image request failed: {exc.reason}") from exc
        try:
            decoded = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ModelProviderError("OpenAI-compatible image response is not valid JSON") from exc
        if not isinstance(decoded, dict):
            raise ModelProviderError("OpenAI-compatible image response JSON must be an object")
        return decoded

    def _write_candidates(
        self,
        response: dict[str, Any],
        prompt_pack: PosterPromptPack,
        output_dir: Path,
        candidate_count: int,
    ) -> list[PosterCandidate]:
        data = response.get("data")
        if not isinstance(data, list) or len(data) < candidate_count:
            raise ModelProviderError("OpenAI-compatible image response missing data entries")
        image_dir = output_dir / "image_candidates"
        image_dir.mkdir(parents=True, exist_ok=True)
        candidates: list[PosterCandidate] = []
        for index, item in enumerate(data[:candidate_count], start=1):
            if not isinstance(item, dict):
                raise ModelProviderError("OpenAI-compatible image response data entry must be an object")
            candidate_id = f"candidate_{index:03d}"
            relative_path = f"image_candidates/{candidate_id}.png"
            image_bytes, response_source = self._image_bytes(item)
            (output_dir / relative_path).write_bytes(image_bytes)
            candidates.append(
                PosterCandidate(
                    candidate_id=candidate_id,
                    image_path=relative_path,
                    prompt_id=prompt_pack.prompt_id,
                    provider="openai_compatible_image",
                    metadata={
                        "response_source": response_source,
                        "revised_prompt_present": bool(item.get("revised_prompt")),
                    },
                )
            )
        return candidates

    def _image_bytes(self, item: dict[str, Any]) -> tuple[bytes, str]:
        if isinstance(item.get("b64_json"), str) and item["b64_json"]:
            try:
                return base64.b64decode(item["b64_json"]), "b64_json"
            except ValueError as exc:
                raise ModelProviderError("OpenAI-compatible image b64_json is invalid") from exc
        if isinstance(item.get("url"), str) and item["url"]:
            return self._download_image(item["url"]), "url"
        raise ModelProviderError("OpenAI-compatible image response entry missing b64_json or url")

    def _download_image(self, url: str) -> bytes:
        try:
            with urllib.request.urlopen(url, timeout=self.timeout_sec) as response:
                return response.read()
        except urllib.error.URLError as exc:
            raise ModelProviderError(f"OpenAI-compatible image URL download failed: {exc.reason}") from exc


def _safe_params(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "n": payload.get("n"),
        "size": payload.get("size"),
        "response_format": payload.get("response_format"),
    }


def create_image_provider_from_env() -> OpenAICompatibleImageProvider | MiniMaxImageProvider:
    provider_name = os.environ.get(IMAGE_PROVIDER_ENV, OPENAI_COMPATIBLE_PROVIDER).strip().lower()
    if provider_name in {"", OPENAI_COMPATIBLE_PROVIDER}:
        return OpenAICompatibleImageProvider.from_env()
    if provider_name == MINIMAX_PROVIDER:
        from agentflow_studio.production.posterflow.minimax_provider import MiniMaxImageProvider

        return MiniMaxImageProvider.from_env()
    raise ModelProviderError(
        f"Unsupported image provider '{provider_name}'; expected {OPENAI_COMPATIBLE_PROVIDER} or {MINIMAX_PROVIDER}"
    )
