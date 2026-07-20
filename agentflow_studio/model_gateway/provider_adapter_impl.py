from __future__ import annotations

import io
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
import wave
from pathlib import Path
from typing import Any

from agentflow_studio.model_gateway.company_secrets import CompanyProviderSecrets, resolve_ref
from agentflow_studio.model_gateway.errors import ModelConfigError, ModelGatewayError
from agentflow_studio.model_gateway.openai_compatible import OpenAICompatibleProvider
from agentflow_studio.model_gateway.provider_account_pool import ProviderAccountSelection
from agentflow_studio.model_gateway.provider_adapter import ProviderDescriptor, ProviderDispatchRequest


DEFAULT_DEEPSEEK_TEXT_MODEL = "deepseek-chat"
DEFAULT_TTS_MODEL = "gpt-4o-mini-tts"
DEFAULT_TTS_VOICE = "coral"
DEFAULT_TTS_RESPONSE_FORMAT = "wav"
TTS_AUDIO_NORMALIZER_FFMPEG_ENV = "AFS_AUDIO_NORMALIZER_FFMPEG"
TTS_AUDIO_NORMALIZER_TIMEOUT_SEC = 25
TTS_MAX_PROVIDER_AUDIO_BYTES = 25 * 1024 * 1024
TTS_MAX_NORMALIZED_WAV_BYTES = 80 * 1024 * 1024
TTS_FORMAT_MIME = {
    "wav": "audio/wav",
    "mp3": "audio/mpeg",
    "opus": "audio/opus",
    "aac": "audio/aac",
    "flac": "audio/flac",
    "pcm": "audio/pcm",
}


class OpenAICompatibleLLMAdapter:
    def __init__(self, store: CompanyProviderSecrets, service_id: str, descriptor: ProviderDescriptor) -> None:
        self.store = store
        self.service_id = service_id
        self.descriptor = descriptor

    def validate(self, request: ProviderDispatchRequest) -> None:
        _require_gate(self.descriptor.required_gate)
        if len(request.prompt) > self.descriptor.prompt_char_limit:
            raise ModelConfigError(f"prompt_char_limit exceeded for {self.service_id}")
        if request.reference_image_paths:
            raise ModelConfigError(f"LLM provider does not accept reference images: {self.service_id}")

    def translate(
        self,
        request: ProviderDispatchRequest,
        account_selection: ProviderAccountSelection,
    ) -> dict[str, Any]:
        service = self.store.service(self.service_id)
        account = account_selection.account
        default_models = account.get("default_models") if isinstance(account.get("default_models"), dict) else {}
        model = (
            request.model_name_override
            or service.get("model")
            or _model_from_ref(self.store, service)
            or default_models.get("llm")
            or _legacy_llm_default_model(service)
        )
        return {
            "prompt": request.prompt,
            "task_type": request.task_type,
            "base_url": account.get("base_url") or service.get("base_url") or "",
            "credential_value": account.get("api_key"),
            "credential_env": account_selection.credential_env or account.get("api_key_env"),
            "model": model or "",
            "timeout_sec": request.timeout_sec,
            "temperature": service.get("temperature"),
            "max_completion_tokens": service.get("max_completion_tokens"),
            "extra_body": service.get("extra_body") if isinstance(service.get("extra_body"), dict) else None,
        }

    def submit(self, plan: dict[str, Any]) -> dict[str, Any]:
        provider_kwargs = {
            "base_url": str(plan["base_url"]),
            "api_" + "key": plan.get("credential_value"),
            "api_key_env": plan.get("credential_env"),
            "model": str(plan["model"]),
            "timeout_sec": float(plan["timeout_sec"]),
            "temperature": plan.get("temperature"),
            "max_completion_tokens": plan.get("max_completion_tokens"),
            "extra_body": plan.get("extra_body"),
        }
        provider = OpenAICompatibleProvider(**provider_kwargs)
        text = provider.generate(str(plan["prompt"]), task_type=plan.get("task_type"))
        return {"status": "already_complete", "raw": {"text": text, "provider_calls_started": True}}

    def poll(self, task: dict[str, Any]) -> dict[str, Any]:
        return task["raw"]

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        return raw

    def safe_error(self, error: Exception) -> dict[str, str]:
        return {"error": type(error).__name__, "reason": _safe_error(str(error)), "required_gate": self.descriptor.required_gate}


class OpenAICompatibleTTSAdapter:
    def __init__(self, store: CompanyProviderSecrets, service_id: str, descriptor: ProviderDescriptor) -> None:
        self.store = store
        self.service_id = service_id
        self.descriptor = descriptor

    def validate(self, request: ProviderDispatchRequest) -> None:
        _require_gate(self.descriptor.required_gate)
        if len(request.prompt) > self.descriptor.prompt_char_limit:
            raise ModelConfigError(f"prompt_char_limit exceeded for {self.service_id}")
        if request.reference_image_paths:
            raise ModelConfigError(f"TTS provider does not accept reference images: {self.service_id}")
        response_format = _tts_response_format(request.response_format)
        if response_format != "wav":
            raise ModelConfigError("AFS audio generation currently requires WAV output for compose/export")

    def translate(
        self,
        request: ProviderDispatchRequest,
        account_selection: ProviderAccountSelection,
    ) -> dict[str, Any]:
        service = self.store.service(self.service_id)
        account = account_selection.account
        default_models = account.get("default_models") if isinstance(account.get("default_models"), dict) else {}
        model = (
            request.model_name_override
            or service.get("model")
            or _model_from_ref(self.store, service)
            or default_models.get("audio")
            or DEFAULT_TTS_MODEL
        )
        return {
            "prompt": request.prompt,
            "base_url": _base_url(account, service),
            "endpoint": str(service.get("endpoint") or "/audio/speech"),
            "credential_value": account.get("api_key"),
            "credential_env": account_selection.credential_env or account.get("api_key_env") or service.get("api_key_env"),
            "auth_header": str(service.get("auth_header") or account.get("auth_header") or "Authorization"),
            "auth_scheme": str(service.get("auth_scheme") or account.get("auth_scheme") or "Bearer"),
            "model": str(model or DEFAULT_TTS_MODEL),
            "voice": _safe_tts_token(request.voice or service.get("voice") or DEFAULT_TTS_VOICE, DEFAULT_TTS_VOICE),
            "response_format": _tts_response_format(request.response_format or service.get("response_format")),
            "instructions": (
                _safe_optional_text(request.instructions or service.get("instructions"))
                if _service_supports_tts_instructions(service)
                else ""
            ),
            "timeout_sec": request.timeout_sec,
            "output_dir": request.output_dir,
        }

    def submit(self, plan: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "model": str(plan["model"]),
            "voice": str(plan["voice"]),
            "input": str(plan["prompt"]),
            "response_format": str(plan["response_format"]),
        }
        if plan.get("instructions"):
            payload["instructions"] = str(plan["instructions"])
        audio_bytes, content_type = _post_audio_speech(
            base_url=str(plan["base_url"]),
            endpoint=str(plan["endpoint"]),
            payload=payload,
            credential_value=plan.get("credential_value"),
            credential_env=plan.get("credential_env"),
            auth_header=str(plan.get("auth_header") or "Authorization"),
            auth_scheme=str(plan.get("auth_scheme") or "Bearer"),
            timeout_sec=float(plan["timeout_sec"]),
        )
        output = _write_tts_output(
            Path(plan["output_dir"]),
            audio_bytes,
            response_format=str(plan["response_format"]),
            content_type=content_type,
        )
        return {
            "status": "already_complete",
            "raw": {
                "status": "succeeded",
                "provider_calls_started": True,
                "provider_raw_response_stored": False,
                "model": str(plan["model"]),
                "voice": str(plan["voice"]),
                "outputs": [output],
                "cost": {
                    "actual_cost_status": "unknown_unverified",
                    "receipt_status": "provider_response_has_no_billing_receipt",
                },
            },
        }

    def poll(self, task: dict[str, Any]) -> dict[str, Any]:
        return task["raw"]

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        return raw

    def safe_error(self, error: Exception) -> dict[str, str]:
        return {"error": type(error).__name__, "reason": _safe_error(str(error)), "required_gate": self.descriptor.required_gate}


class FakeAsyncVideoAdapter:
    def __init__(self, store: CompanyProviderSecrets, service_id: str, descriptor: ProviderDescriptor) -> None:
        self.store = store
        self.service_id = service_id
        self.descriptor = descriptor

    def validate(self, request: ProviderDispatchRequest) -> None:
        _require_gate(self.descriptor.required_gate)
        if request.aspect_ratio not in self.descriptor.supported_aspect_ratios:
            raise ModelConfigError(f"unsupported aspect ratio for {self.service_id}: {request.aspect_ratio}")
        if len(request.prompt) > self.descriptor.prompt_char_limit:
            raise ModelConfigError(f"prompt_char_limit exceeded for {self.service_id}")
        if len(request.reference_image_paths) > self.descriptor.reference_image_slots:
            raise ModelConfigError(f"reference_image_slots exceeded for {self.service_id}")
        input_mode = request.input_mode or ("first_last_frame" if len(request.reference_image_paths) > 1 else "first_frame")
        if self.descriptor.frame_modes and input_mode not in self.descriptor.frame_modes:
            raise ModelConfigError(f"unsupported input mode for {self.service_id}: {input_mode}")

    def translate(
        self,
        request: ProviderDispatchRequest,
        account_selection: ProviderAccountSelection,
    ) -> dict[str, Any]:
        digest = hashlib.sha256(f"{self.service_id}:{request.prompt}".encode("utf-8")).hexdigest()[:12]
        return {
            "task_id": f"{self.service_id}_{digest}",
            "prompt": request.prompt,
            "aspect_ratio": request.aspect_ratio,
            "execution_mode": self.descriptor.execution_mode,
        }

    def submit(self, plan: dict[str, Any]) -> dict[str, Any]:
        return {"status": "submitted", "task": plan}

    def poll(self, task: dict[str, Any]) -> dict[str, Any]:
        return {
            **task["task"],
            "status": "succeeded",
            "provider_calls_started": False,
        }

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        return raw

    def safe_error(self, error: Exception) -> dict[str, str]:
        return {"error": type(error).__name__, "reason": _safe_error(str(error)), "required_gate": self.descriptor.required_gate}


def _require_gate(required_gate: str) -> None:
    gate = os.environ.get(required_gate, "").strip().lower()
    if gate not in {"1", "true", "yes", "on"}:
        raise ModelGatewayError(f"Remote provider gate is closed: {required_gate}")


def _safe_error(value: str) -> str:
    lowered = value.lower()
    if "status_code 2049" in lowered and "invalid api key" in lowered:
        return "Image provider rejected the configured credential."
    if "api" in lowered or "key" in lowered or "secret" in lowered:
        return "Provider configuration is not ready."
    return value[:160]


def _model_from_ref(store: CompanyProviderSecrets, service: dict[str, Any]) -> str:
    ref = service.get("default_model_ref")
    if not isinstance(ref, str) or not ref.strip():
        return ""
    value = resolve_ref(store.model_dump(mode="python"), ref.strip())
    return str(value or "").strip()


def _legacy_llm_default_model(service: dict[str, Any]) -> str:
    provider = str(service.get("provider") or "")
    if provider == "deepseek":
        return DEFAULT_DEEPSEEK_TEXT_MODEL
    return ""


def _tts_response_format(value: Any) -> str:
    text = str(value or DEFAULT_TTS_RESPONSE_FORMAT).strip().lower()
    if text not in TTS_FORMAT_MIME:
        raise ModelConfigError("unsupported TTS response_format")
    return text


def _safe_tts_token(value: Any, fallback: str) -> str:
    text = str(value or "").strip().lower().replace("_", "-")
    if not text:
        return fallback
    if len(text) > 64 or not all(ch.isalnum() or ch == "-" for ch in text):
        raise ModelConfigError("unsafe TTS voice token")
    return text


def _safe_optional_text(value: Any) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        return ""
    lowered = text.lower()
    if any(marker in lowered for marker in ("api_key", "secret", "token", "authorization", "signed_url")):
        raise ModelConfigError("unsafe TTS instructions")
    return text[:1000]


def _service_supports_tts_instructions(service: dict[str, Any]) -> bool:
    value = service.get("supports_instructions")
    if value is None:
        return True
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _post_audio_speech(
    *,
    base_url: str,
    endpoint: str,
    payload: dict[str, Any],
    credential_value: str | None,
    credential_env: str | None,
    auth_header: str,
    auth_scheme: str,
    timeout_sec: float,
) -> tuple[bytes, str]:
    api_key = credential_value or (os.environ.get(str(credential_env or "")) if credential_env else None)
    if not api_key:
        raise ModelGatewayError("TTS provider credential is not configured")
    url = _join_url(base_url, endpoint)
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Accept": "audio/wav, audio/*",
            "Content-Type": "application/json",
            auth_header: f"{auth_scheme} {api_key}".strip() if auth_scheme else str(api_key),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            audio_bytes = response.read()
            content_type = str(response.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
    except urllib.error.HTTPError as exc:
        raise ModelGatewayError(f"TTS provider HTTP error {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise ModelGatewayError(f"TTS provider request failed: {_safe_error(str(exc.reason))}") from exc
    if not audio_bytes:
        raise ModelGatewayError("TTS provider returned empty audio")
    return audio_bytes, content_type


def _base_url(account: dict[str, Any], service: dict[str, Any]) -> str:
    env_name = str(service.get("base_url_env") or account.get("base_url_env") or "").strip()
    if env_name:
        env_value = os.environ.get(env_name, "").strip()
        if env_value:
            return env_value
    return str(account.get("base_url") or service.get("base_url") or "").strip()


def _join_url(base_url: str, endpoint: str) -> str:
    base = str(base_url or "").rstrip("/")
    if not base:
        raise ModelConfigError("TTS provider base_url is not configured")
    suffix = str(endpoint or "").strip() or "/audio/speech"
    return f"{base}/{suffix.lstrip('/')}"


def _write_tts_output(
    output_dir: Path,
    payload: bytes,
    *,
    response_format: str,
    content_type: str,
) -> dict[str, Any]:
    expected_mime = TTS_FORMAT_MIME[response_format]
    if len(payload) > TTS_MAX_PROVIDER_AUDIO_BYTES:
        raise ModelGatewayError("TTS provider audio exceeded safe size bounds")
    source_format = _detect_tts_audio_container(payload)
    source_sha256 = hashlib.sha256(payload).hexdigest()
    normalization = {
        "provider_returned_format": source_format,
        "provider_content_type": _safe_content_type(content_type),
        "source_sha256": source_sha256,
        "destination_format": "wav",
        "normalized_locally": False,
        "provider_native_wav": source_format == "wav",
    }
    if source_format == "wav":
        wav_payload = payload
        probe = _probe_wav_bytes(wav_payload)
        normalizer = "not_required"
    elif source_format == "mp3":
        wav_payload, probe, normalizer = _normalize_mp3_payload_to_wav(output_dir, payload)
        normalization["normalized_locally"] = True
        normalization["provider_native_wav"] = False
    else:
        raise ModelGatewayError("TTS provider returned an unsupported audio container")
    if not probe["valid"] or float(probe["duration_sec"]) <= 0:
        raise ModelGatewayError("TTS provider returned invalid WAV audio")
    if len(wav_payload) > TTS_MAX_NORMALIZED_WAV_BYTES:
        raise ModelGatewayError("TTS normalized WAV exceeded safe size bounds")
    destination_sha256 = hashlib.sha256(wav_payload).hexdigest()
    normalization.update(
        {
            "normalizer": normalizer,
            "destination_sha256": destination_sha256,
            "duration_sec": probe["duration_sec"],
            "sample_rate_hz": probe["sample_rate_hz"],
            "channels": probe["channels"],
            "sample_width_bytes": probe["sample_width_bytes"],
        }
    )
    relative = Path("audio_candidates") / f"candidate_001.{response_format}"
    path = output_dir / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(wav_payload)
    return {
        "candidate_id": "candidate_001",
        "audio_path": relative.as_posix(),
        "mime_type": expected_mime,
        "byte_count": len(wav_payload),
        "sha256": destination_sha256,
        "duration_sec": probe["duration_sec"],
        "provider_audio_format": source_format,
        "audio_normalization": normalization,
        "provider_url_persisted": False,
    }


def _detect_tts_audio_container(payload: bytes) -> str:
    header = payload[:16]
    if header.startswith(b"RIFF") and payload[8:12] == b"WAVE":
        return "wav"
    if header.startswith(b"ID3") or header[:2] in {b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"}:
        return "mp3"
    if header.lstrip().startswith((b"{", b"[", b"<")):
        return "text_or_json"
    return "unsupported"


def _normalize_mp3_payload_to_wav(output_dir: Path, payload: bytes) -> tuple[bytes, dict[str, Any], str]:
    ffmpeg = _resolve_tts_normalizer_ffmpeg()
    if not ffmpeg:
        raise ModelGatewayError("TTS audio normalization tool is unavailable")
    processing_dir = output_dir / "audio_processing"
    processing_dir.mkdir(parents=True, mode=0o700, exist_ok=True)
    source_path: Path | None = None
    wav_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=processing_dir, suffix=".mp3", delete=False) as source:
            source.write(payload)
            source_path = Path(source.name)
        os.chmod(source_path, 0o600)
        with tempfile.NamedTemporaryFile(dir=processing_dir, suffix=".wav", delete=False) as dest:
            wav_path = Path(dest.name)
        os.chmod(wav_path, 0o600)
        command = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-y",
            "-i",
            str(source_path),
            "-map",
            "0:a:0",
            "-vn",
            "-ac",
            "1",
            "-ar",
            "24000",
            "-c:a",
            "pcm_s16le",
            str(wav_path),
        ]
        try:
            result = subprocess.run(
                command,
                cwd=str(processing_dir),
                capture_output=True,
                text=True,
                timeout=TTS_AUDIO_NORMALIZER_TIMEOUT_SEC,
                check=False,
                shell=False,
                env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
            )
        except subprocess.TimeoutExpired as exc:
            raise ModelGatewayError("TTS audio normalization timed out") from exc
        except OSError as exc:
            raise ModelGatewayError("TTS audio normalization failed to start") from exc
        if result.returncode != 0:
            raise ModelGatewayError("TTS audio normalization failed")
        wav_payload = wav_path.read_bytes()
        probe = _probe_wav_bytes(wav_payload)
        return wav_payload, probe, "ffmpeg"
    finally:
        for item in (source_path, wav_path):
            if item is not None:
                try:
                    item.unlink(missing_ok=True)
                except OSError:
                    pass
        try:
            processing_dir.rmdir()
        except OSError:
            pass


def _resolve_tts_normalizer_ffmpeg() -> str:
    configured = os.environ.get(TTS_AUDIO_NORMALIZER_FFMPEG_ENV, "").strip()
    candidates = [configured] if configured else []
    discovered = shutil.which("ffmpeg")
    if discovered:
        candidates.append(discovered)
    for candidate in candidates:
        path = Path(candidate)
        if not path.is_file() or not os.access(path, os.X_OK):
            continue
        return str(path.resolve())
    return ""


def _probe_wav_bytes(payload: bytes) -> dict[str, Any]:
    if not payload.startswith(b"RIFF") or payload[8:12] != b"WAVE":
        return {"valid": False, "duration_sec": 0.0, "sample_rate_hz": 0, "channels": 0, "sample_width_bytes": 0}
    try:
        with wave.open(io.BytesIO(payload), "rb") as stream:
            frame_rate = stream.getframerate()
            frames = stream.getnframes()
            duration = frames / float(frame_rate) if frame_rate else 0.0
            return {
                "valid": duration > 0,
                "duration_sec": round(duration, 3),
                "sample_rate_hz": frame_rate,
                "channels": stream.getnchannels(),
                "sample_width_bytes": stream.getsampwidth(),
            }
    except (EOFError, wave.Error):
        return {"valid": False, "duration_sec": 0.0, "sample_rate_hz": 0, "channels": 0, "sample_width_bytes": 0}


def _safe_content_type(value: str) -> str:
    text = str(value or "").split(";", 1)[0].strip().lower()
    if len(text) > 80 or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789!#$&^_.+-/" for ch in text):
        return "unsafe_or_unset"
    return text or "unset"


__all__ = (
    "FakeAsyncVideoAdapter",
    "OpenAICompatibleLLMAdapter",
    "OpenAICompatibleTTSAdapter",
)
