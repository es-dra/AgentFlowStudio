from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from agentflow_studio.model_gateway.company_secrets import (
    SERVER_CODEX_SERVICE_ID,
    CompanyProviderSecrets,
)
from agentflow_studio.model_gateway.codex_runtime_env import codex_subprocess_env, prune_codex_home
from agentflow_studio.model_gateway.errors import ModelConfigError, ModelGatewayError
from agentflow_studio.model_gateway.provider_account_pool import ProviderAccountSelection
from agentflow_studio.model_gateway.provider_adapter import (
    ProviderDescriptor,
    ProviderDispatchRequest,
    structured_output_schema_digest,
)


TRUE_VALUES = {"1", "true", "yes", "on"}
REFERENCE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
CODEX_CLI_ALLOWED_REASONING_EFFORTS = {"low", "medium", "high", "xhigh"}
CODEX_CLI_KNOWN_MODEL_ALLOWLIST = {
    "codex-auto-review",
    "gpt-5.3-codex-spark",
    "gpt-5.4",
    "gpt-5.4-mini",
    "gpt-5.5",
    "gpt-5.6-luna",
    "gpt-5.6-sol",
    "gpt-5.6-terra",
}


class CodexLocalAdapter:
    """Synchronous local Codex execution for text and visual understanding tasks."""

    def __init__(self, store: CompanyProviderSecrets, service_id: str, descriptor: ProviderDescriptor) -> None:
        self.store = store
        self.service_id = service_id
        self.descriptor = descriptor

    def validate(self, request: ProviderDispatchRequest) -> None:
        _require_gate(self.descriptor.required_gate)
        if len(request.prompt) > self.descriptor.prompt_char_limit:
            raise ModelConfigError(f"prompt_char_limit exceeded for {self.service_id}")
        if self.descriptor.modality == "image" and request.aspect_ratio not in self.descriptor.supported_aspect_ratios:
            raise ModelConfigError(f"unsupported aspect ratio for {self.service_id}: {request.aspect_ratio}")
        if len(request.reference_image_paths) > self.descriptor.reference_image_slots:
            raise ModelConfigError(f"reference_image_slots exceeded for {self.service_id}")
        if self.descriptor.modality not in {"llm", "vision"}:
            raise ModelConfigError(f"Codex local adapter does not support capability: {self.descriptor.modality}")
        structured_requested = (
            request.structured_output_contract_id is not None
            or request.structured_output_schema is not None
            or request.structured_output_schema_digest is not None
        )
        if structured_requested:
            if self.service_id != SERVER_CODEX_SERVICE_ID or self.descriptor.modality != "llm":
                raise ModelConfigError("structured output is only supported by server_codex llm")
            if (
                not request.structured_output_contract_id
                or not isinstance(request.structured_output_schema, dict)
                or not request.structured_output_schema_digest
            ):
                raise ModelConfigError("structured output contract id, schema, and schema digest are required")
            if (
                request.structured_output_schema.get("type") != "object"
                or request.structured_output_schema.get("additionalProperties") is not False
            ):
                raise ModelConfigError("structured output root schema must be a closed object")
            actual_digest = structured_output_schema_digest(request.structured_output_schema)
            if actual_digest != request.structured_output_schema_digest:
                raise ModelConfigError("structured output schema digest mismatch")

    def translate(
        self,
        request: ProviderDispatchRequest,
        account_selection: ProviderAccountSelection,
    ) -> dict[str, Any]:
        service = self.store.service(self.service_id)
        account = account_selection.account
        return {
            "service_id": self.service_id,
            "capability": self.descriptor.modality,
            "prompt": request.prompt,
            "task_type": request.task_type,
            "structured_output_contract_id": request.structured_output_contract_id,
            "structured_output_schema": request.structured_output_schema,
            "structured_output_schema_digest": request.structured_output_schema_digest,
            "reference_image_paths": tuple(request.reference_image_paths),
            "cli_command": _codex_cli_command(
                self.service_id,
                str(service.get("cli_command") or account.get("cli_command") or "codex"),
            ),
            "cli_model": _validated_cli_model(
                request.model_name_override
                or str(service.get("cli_model") or account.get("cli_model") or "").strip()
            ),
            "cli_reasoning_effort": _validated_cli_reasoning_effort(
                str(service.get("cli_reasoning_effort") or account.get("cli_reasoning_effort") or "").strip()
            ),
            "timeout_sec": float(service.get("timeout_sec") or account.get("timeout_sec") or request.timeout_sec),
            "account": account_selection.public_summary(),
        }

    def submit(self, plan: dict[str, Any]) -> dict[str, Any]:
        raw = _run_codex(plan)
        return {"status": "already_complete", "raw": raw}

    def poll(self, task: dict[str, Any]) -> dict[str, Any]:
        return task["raw"]

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        if self.descriptor.modality == "llm":
            normalized = {"text": _extract_text(raw), "provider_calls_started": True}
            if isinstance(raw.get("structured_output"), dict):
                normalized["structured_output"] = raw["structured_output"]
            return normalized
        if self.descriptor.modality == "vision":
            return _normalize_vision(raw)
        return raw

    def safe_error(self, error: Exception) -> dict[str, str]:
        return {"error": type(error).__name__, "reason": _safe_error(str(error)), "required_gate": self.descriptor.required_gate}


def _codex_cli_command(service_id: str, configured: str) -> str:
    command = configured.strip() or "codex"
    if service_id != SERVER_CODEX_SERVICE_ID:
        return command
    candidates = [
        os.environ.get("AFS_CODEX_CLI", "").strip(),
        str(Path.home() / ".codex" / "packages" / "standalone" / "current" / "bin" / "codex"),
        str(Path.home() / ".local" / "bin" / "codex"),
        shutil.which(command) or "",
    ]
    for raw in candidates:
        if not raw:
            continue
        candidate = Path(raw).expanduser()
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return command


def _validated_cli_model(value: str | None) -> str:
    model = str(value or "").strip()
    if not model:
        return ""
    if not re.fullmatch(r"[A-Za-z0-9._:-]{1,80}", model):
        raise ModelConfigError("codex_local cli_model is not a safe model slug")
    if model not in _codex_cli_allowed_models():
        raise ModelConfigError("codex_local cli_model is not in the local Codex model allowlist")
    return model


def _validated_cli_reasoning_effort(value: str | None) -> str:
    effort = str(value or "").strip().lower()
    if not effort:
        return ""
    if effort not in CODEX_CLI_ALLOWED_REASONING_EFFORTS:
        raise ModelConfigError("codex_local cli_reasoning_effort is not allowed")
    return effort


def _codex_cli_allowed_models() -> set[str]:
    allowed = set(CODEX_CLI_KNOWN_MODEL_ALLOWLIST)
    for path in _codex_model_cache_paths():
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        models = payload.get("models") if isinstance(payload, dict) else None
        if isinstance(models, list):
            for item in models:
                if isinstance(item, dict) and isinstance(item.get("slug"), str):
                    allowed.add(str(item["slug"]))
    return allowed


def _codex_model_cache_paths() -> tuple[Path, ...]:
    configured_home = str(os.environ.get("CODEX_HOME") or os.environ.get("AFS_CODEX_HOME") or "").strip()
    paths = []
    if configured_home:
        paths.append(Path(configured_home).expanduser() / "models_cache.json")
    paths.append(Path.home() / ".codex" / "models_cache.json")
    return tuple(paths)


def _run_codex(plan: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="afs_codex_local_") as tmp:
        work_dir = Path(tmp)
        references = _copy_reference_images(work_dir, plan.get("reference_image_paths") or [])
        contract_id = str(plan.get("structured_output_contract_id") or "")
        schema = plan.get("structured_output_schema")
        schema_digest = str(plan.get("structured_output_schema_digest") or "")
        request_payload = {
            "schema_version": "afs_codex_local_request.v0.2",
            "service_id": str(plan["service_id"]),
            "capability": str(plan["capability"]),
            "task_type": plan.get("task_type"),
            "structured_output_contract_id": contract_id or None,
            "structured_output_schema_digest": schema_digest or None,
            "prompt": str(plan["prompt"]),
            "reference_images": references,
            "provider_raw_response_stored": False,
            "signed_urls_persisted": False,
            "media_bytes_returned_by_api": False,
        }
        (work_dir / "request.json").write_text(json.dumps(request_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        (work_dir / "prompt.md").write_text(_codex_prompt(request_payload), encoding="utf-8")
        schema_path = work_dir / "output.schema.json"
        final_message_path = work_dir / "final-message.json"
        if isinstance(schema, dict):
            schema_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        command = [
            str(plan.get("cli_command") or "codex"),
            "exec",
            "-c",
            'approval_policy="never"',
            "--sandbox",
            "workspace-write",
            "--skip-git-repo-check",
        ]
        if plan.get("cli_model"):
            command.extend(["--model", str(plan["cli_model"])])
        if plan.get("cli_reasoning_effort"):
            command.extend(["-c", f'model_reasoning_effort="{plan["cli_reasoning_effort"]}"'])
        if isinstance(schema, dict):
            command.extend(
                [
                    "--ephemeral",
                    "--output-schema",
                    str(schema_path),
                    "--output-last-message",
                    str(final_message_path),
                ]
            )
        command.extend(
            [
                "--cd",
                str(work_dir),
                "-",
            ]
        )
        codex_env = codex_subprocess_env()
        try:
            completed = subprocess.run(
                command,
                cwd=str(work_dir),
                capture_output=True,
                input=_codex_prompt(request_payload),
                text=True,
                encoding="utf-8",
                errors="replace",
                env=codex_env,
                timeout=float(plan.get("timeout_sec") or 120.0),
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ModelGatewayError("Codex local provider timed out before returning structured output") from exc
        except OSError as exc:
            raise ModelGatewayError("Codex local provider command is not available") from exc
        finally:
            prune_codex_home(codex_env)
        if completed.returncode != 0:
            raise ModelGatewayError(_safe_error(completed.stderr or completed.stdout))
        if isinstance(schema, dict):
            payload, output = _read_structured_final(final_message_path, schema)
            return {
                "text": output,
                "structured_output": payload,
                "provider_calls_started": True,
                "provider_raw_response_stored": False,
                "safe_evidence": {
                    "reference_image_count": len(references),
                    "structured_output_contract_id": contract_id,
                    "structured_output_schema_digest": schema_digest,
                    "stdout_ignored": True,
                },
            }
        output = (completed.stdout or "").strip()
        if not output:
            raise ModelGatewayError("Codex local provider returned empty output")
        if str(plan["capability"]) == "vision":
            return _vision_raw(output, references)
        return {
            "text": output,
            "provider_calls_started": True,
            "provider_raw_response_stored": False,
            "safe_evidence": {"reference_image_count": len(references)},
        }


def _read_structured_final(path: Path, schema: dict[str, Any]) -> tuple[dict[str, Any], str]:
    if not path.is_file():
        raise ModelGatewayError("Codex structured final response is missing")
    output = path.read_text(encoding="utf-8").strip()
    if not output:
        raise ModelGatewayError("Codex structured final response is empty")
    try:
        payload = json.loads(output)
    except json.JSONDecodeError as exc:
        raise ModelGatewayError("Codex structured final response is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ModelGatewayError("Codex structured final response must be an object")
    try:
        _validate_controlled_schema(payload, schema)
    except (TypeError, ValueError) as exc:
        raise ModelGatewayError("Codex structured final response does not match schema") from exc
    return payload, json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _validate_controlled_schema(value: Any, schema: dict[str, Any]) -> None:
    expected = schema.get("type")
    if expected == "object":
        if not isinstance(value, dict):
            raise TypeError("object required")
        properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
        required = schema.get("required") if isinstance(schema.get("required"), list) else []
        if any(key not in value for key in required):
            raise ValueError("required property missing")
        if schema.get("additionalProperties") is False and any(key not in properties for key in value):
            raise ValueError("additional property is not allowed")
        for key, item in value.items():
            child = properties.get(key)
            if isinstance(child, dict):
                _validate_controlled_schema(item, child)
        return
    if expected == "array":
        if not isinstance(value, list):
            raise TypeError("array required")
        if "minItems" in schema and len(value) < int(schema["minItems"]):
            raise ValueError("array is too short")
        if "maxItems" in schema and len(value) > int(schema["maxItems"]):
            raise ValueError("array is too long")
        child = schema.get("items")
        if isinstance(child, dict):
            for item in value:
                _validate_controlled_schema(item, child)
        return
    if expected == "string":
        if not isinstance(value, str):
            raise TypeError("string required")
        if "minLength" in schema and len(value) < int(schema["minLength"]):
            raise ValueError("string is too short")
        allowed = schema.get("enum")
        if isinstance(allowed, list) and value not in allowed:
            raise ValueError("string is not in enum")
        return
    if expected == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
        raise TypeError("integer required")
    if expected == "number" and (not isinstance(value, (int, float)) or isinstance(value, bool)):
        raise TypeError("number required")
    if expected == "boolean" and not isinstance(value, bool):
        raise TypeError("boolean required")

def _codex_prompt(request: dict[str, Any]) -> str:
    request_json = json.dumps(request, ensure_ascii=False, sort_keys=True)
    if request.get("structured_output_contract_id"):
        return (
            "You are the local Codex structured script worker for AFS.\n"
            "Return exactly one final JSON object that conforms to output.schema.json.\n"
            "Do not include markdown fences, prefaces, suffixes, explanations, credentials, paths, or raw metadata.\n"
            "Use only this safe request payload:\n"
            f"<request_json>{request_json}</request_json>"
        )

    if request["capability"] == "vision":
        refs = "\n".join(f"- {item['path']}" for item in request.get("reference_images") or [])
        return (
            "You are the local Codex visual understanding worker for AFS.\n"
            "Inspect only the copied reference images listed below and the user prompt in request.json.\n"
            "Return strict JSON only, with this shape:\n"
            '{"observation":{"description":"...","summary":"...","labels":["..."],"feature_card":{},"segments":[]}}\n'
            "Do not include local absolute paths, signed URLs, credentials, raw provider payloads, or media bytes.\n"
            f"Reference image files:\n{refs or '- none'}\n"
            f"Safe request payload:\n<request_json>{request_json}</request_json>"
        )
    return (
        "You are the local Codex prompt optimization worker for AFS.\n"
        "Produce only the optimized prompt text requested by the safe request payload.\n"
        "Do not include explanations, markdown fences, credentials, paths, or raw provider metadata.\n"
        f"<request_json>{request_json}</request_json>"
    )


def _copy_reference_images(work_dir: Path, reference_paths: Any) -> list[dict[str, Any]]:
    copied: list[dict[str, Any]] = []
    ref_dir = work_dir / "references"
    for index, raw_path in enumerate(list(reference_paths or [])[:8], start=1):
        source = Path(raw_path).resolve()
        if not source.is_file() or source.suffix.lower() not in REFERENCE_SUFFIXES:
            continue
        target_name = f"reference_{index:03d}{source.suffix.lower()}"
        target = ref_dir / target_name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        copied.append({"ref_id": f"reference_{index:03d}", "path": f"references/{target_name}"})
    return copied


def _vision_raw(output: str, references: list[dict[str, Any]]) -> dict[str, Any]:
    payload = _json_object_from_text(output)
    observation = payload.get("observation") if isinstance(payload.get("observation"), dict) else payload
    return {
        "status": str(payload.get("status") or "succeeded"),
        "provider_calls_started": True,
        "provider_raw_response_stored": False,
        "observation": observation,
        "safe_evidence": {"reference_image_count": len(references)},
    }


def _normalize_vision(raw: dict[str, Any]) -> dict[str, Any]:
    observation = raw.get("observation") if isinstance(raw.get("observation"), dict) else {}
    labels = observation.get("labels") if isinstance(observation.get("labels"), list) else []
    return {
        "status": str(raw.get("status") or "succeeded"),
        "provider_calls_started": True,
        "provider_raw_response_stored": False,
        "provider_observation": {
            "description": str(observation.get("description") or observation.get("summary") or ""),
            "summary": str(observation.get("summary") or observation.get("description") or ""),
            "labels": [str(item) for item in labels[:16]],
            "feature_card": observation.get("feature_card") if isinstance(observation.get("feature_card"), dict) else {},
            "segments": observation.get("segments") if isinstance(observation.get("segments"), list) else [],
        },
        "safe_manifest": {
            "provider_raw_response_stored": False,
            "media_bytes_returned_by_api": False,
            "signed_urls_returned_by_api": False,
            "local_paths_returned_by_api": False,
        },
        "safe_evidence": raw.get("safe_evidence") if isinstance(raw.get("safe_evidence"), dict) else {},
    }


def _json_object_from_text(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            return {"observation": {"description": text.strip(), "summary": text.strip(), "labels": []}}
        payload = json.loads(text[start : end + 1])
    if not isinstance(payload, dict):
        raise ModelGatewayError("Codex local vision response JSON must be an object")
    return payload


def _extract_text(raw: dict[str, Any]) -> str:
    text = str(raw.get("text") or "").strip()
    if not text:
        raise ModelGatewayError("Codex local LLM response missing text")
    return text


def _require_gate(required_gate: str) -> None:
    if os.environ.get(required_gate, "").strip().lower() not in TRUE_VALUES:
        raise ModelGatewayError(f"Remote provider gate is closed: {required_gate}")


def _safe_error(value: str) -> str:
    lowered = value.lower()
    if any(term in lowered for term in ("api", "key", "secret", "token", "authorization", "cookie")):
        return "Codex local provider configuration is not ready."
    if any(term in lowered for term in ("request.json", "prompt.md", "references/")):
        return "Codex local provider failed."
    return " ".join(value.split())[:160] or "Codex local provider failed."


__all__ = ("CodexLocalAdapter",)
