from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from agentflow_studio.model_gateway.company_secrets import CompanyProviderSecrets
from agentflow_studio.model_gateway.codex_runtime_env import codex_subprocess_env, prune_codex_home
from agentflow_studio.model_gateway.errors import ModelConfigError, ModelGatewayError
from agentflow_studio.model_gateway.provider_account_pool import ProviderAccountSelection
from agentflow_studio.model_gateway.provider_adapter import ProviderDescriptor, ProviderDispatchRequest


TRUE_VALUES = {"1", "true", "yes", "on"}
REFERENCE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


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
            "reference_image_paths": tuple(request.reference_image_paths),
            "cli_command": str(service.get("cli_command") or account.get("cli_command") or "codex"),
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
            return {"text": _extract_text(raw), "provider_calls_started": True}
        if self.descriptor.modality == "vision":
            return _normalize_vision(raw)
        return raw

    def safe_error(self, error: Exception) -> dict[str, str]:
        return {"error": type(error).__name__, "reason": _safe_error(str(error)), "required_gate": self.descriptor.required_gate}


def _run_codex(plan: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="afs_codex_local_") as tmp:
        work_dir = Path(tmp)
        references = _copy_reference_images(work_dir, plan.get("reference_image_paths") or [])
        request_payload = {
            "schema_version": "afs_codex_local_request.v0.1",
            "service_id": str(plan["service_id"]),
            "capability": str(plan["capability"]),
            "task_type": plan.get("task_type"),
            "prompt": str(plan["prompt"]),
            "reference_images": references,
            "provider_raw_response_stored": False,
            "signed_urls_persisted": False,
            "media_bytes_returned_by_api": False,
        }
        (work_dir / "request.json").write_text(json.dumps(request_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        (work_dir / "prompt.md").write_text(_codex_prompt(request_payload), encoding="utf-8")
        codex_env = codex_subprocess_env()
        try:
            completed = subprocess.run(
                [
                    str(plan.get("cli_command") or "codex"),
                    "exec",
                    "-c",
                    'approval_policy="never"',
                    "--sandbox",
                    "workspace-write",
                    "--skip-git-repo-check",
                    "--cd",
                    str(work_dir),
                    "Read request.json and prompt.md in the current directory, then return only the requested answer.",
                ],
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=codex_env,
                timeout=float(plan.get("timeout_sec") or 120.0),
                check=False,
            )
        finally:
            prune_codex_home(codex_env)
        if completed.returncode != 0:
            raise ModelGatewayError(_safe_error(completed.stderr or completed.stdout))
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


def _codex_prompt(request: dict[str, Any]) -> str:
    if request["capability"] == "vision":
        refs = "\n".join(f"- {item['path']}" for item in request.get("reference_images") or [])
        return (
            "You are the local Codex visual understanding worker for AFS.\n"
            "Inspect only the copied reference images listed below and the user prompt in request.json.\n"
            "Return strict JSON only, with this shape:\n"
            '{"observation":{"description":"...","summary":"...","labels":["..."],"feature_card":{},"segments":[]}}\n'
            "Do not include local absolute paths, signed URLs, credentials, raw provider payloads, or media bytes.\n"
            f"Reference image files:\n{refs or '- none'}\n"
        )
    return (
        "You are the local Codex prompt optimization worker for AFS.\n"
        "Read request.json and produce only the optimized prompt text requested by the user prompt.\n"
        "Do not include explanations, markdown fences, credentials, paths, or raw provider metadata.\n"
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
