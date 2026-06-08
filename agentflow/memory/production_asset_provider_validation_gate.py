from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow.memory.production_asset_profile_constants import PROVIDER_VALIDATION_RESULT_KIND
from agentflow.memory.production_asset_profile_provider import (
    ProviderValidationExecutor,
    build_provider_validation_plan,
    provider_validation_blockers,
    run_provider_validation as execute_provider_validation,
)
from agentflow.memory.production_asset_profiles import load_asset_profile_seed
from agentflow.memory.production_loop import SCHEMA_VERSION
from agentflow.harness.json_io import write_json

PROVIDER_SAFE_MANIFEST_KIND = "agentflow_provider_safe_manifest"


def run_provider_validation_gate(
    *,
    asset_profile_seed_path: Path,
    output_dir: Path,
    generated_at: str,
    request_provider_validation: bool = False,
    run_provider_validation: bool = False,
    provider_config_path: Path | None = None,
    project_materials_path: Path | None = None,
    character_reference_image_path: Path | None = None,
    image_service: str = "minimax_image",
    video_service: str = "kling_i2v",
    provider_validation_executor: ProviderValidationExecutor | None = None,
) -> dict[str, Any]:
    if not isinstance(generated_at, str) or not generated_at.strip():
        raise ValueError("generated_at is required")
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    seed = load_asset_profile_seed(Path(asset_profile_seed_path))
    should_validate = request_provider_validation or run_provider_validation
    plan = build_provider_validation_plan(
        seed,
        generated_at=generated_at,
        run_provider_validation=should_validate,
        provider_config_path=provider_config_path,
        project_materials_path=project_materials_path,
        character_reference_image_path=character_reference_image_path,
        image_service=image_service,
        video_service=video_service,
    )
    blockers = provider_validation_blockers(
        plan,
        provider_config_path=provider_config_path,
        character_reference_image_path=character_reference_image_path,
        image_service=image_service,
    )
    result = _blocked_or_ready_result(blockers)
    if run_provider_validation and not blockers:
        result = execute_provider_validation(
            seed,
            provider_config_path=provider_config_path,
            character_reference_image_path=character_reference_image_path,
            image_service=image_service,
            video_service=video_service,
            provider_validation_executor=provider_validation_executor,
        )
    effective_blockers = _effective_blockers(blockers, result)
    safe_manifest = build_provider_safe_manifest(plan=plan, result=result, blockers=effective_blockers)
    report = build_provider_validation_gate_report(
        plan=plan,
        result=result,
        safe_manifest=safe_manifest,
        blockers=effective_blockers,
    )

    write_json(output_root / "provider_validation_plan.json", plan)
    write_json(output_root / "provider_validation_result.json", result)
    write_json(output_root / "provider_safe_manifest.json", safe_manifest)
    (output_root / "provider_validation_report.md").write_text(render_provider_validation_report_markdown(report), encoding="utf-8")
    return report


def build_provider_safe_manifest(
    *,
    plan: dict[str, Any],
    result: dict[str, Any],
    blockers: list[dict[str, str]],
) -> dict[str, Any]:
    local_inputs = _dict(plan.get("local_inputs"))
    return {
        "kind": PROVIDER_SAFE_MANIFEST_KIND,
        "artifact_type": PROVIDER_SAFE_MANIFEST_KIND,
        "schema_version": SCHEMA_VERSION,
        "status": _status_from_result(result, blockers),
        "provider_capability": {
            "image_service": plan.get("image_service", "unknown"),
            "video_service": plan.get("video_service", "unknown"),
        },
        "request_summary": {
            "project_materials_provided": local_inputs.get("project_materials_provided") is True,
            "character_reference_image_provided": local_inputs.get("character_reference_image_provided") is True,
            "provider_config_provided": local_inputs.get("provider_config_provided") is True,
            "private_paths_persisted": False,
            "media_bytes_persisted": False,
            "signed_urls_persisted": False,
            "provider_response_persisted": False,
        },
        "artifact_refs": {
            "plan": "provider_validation_plan.json",
            "result": "provider_validation_result.json",
            "report": "provider_validation_report.md",
        },
        "blockers": blockers,
        "redacted_metadata": {
            "secret_values": "redacted_or_not_loaded",
            "private_paths": "not_persisted",
            "provider_response": "not_persisted",
        },
        "provider_calls_started": result.get("provider_calls_started") is True,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": _non_claims(),
    }


def build_provider_validation_gate_report(
    *,
    plan: dict[str, Any],
    result: dict[str, Any],
    safe_manifest: dict[str, Any],
    blockers: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "kind": "agentflow_provider_validation_gate_report",
        "artifact_type": "agentflow_provider_validation_gate_report",
        "schema_version": SCHEMA_VERSION,
        "status": safe_manifest.get("status", "unknown"),
        "plan_id": plan.get("plan_id", "unknown"),
        "provider_calls_started": result.get("provider_calls_started") is True,
        "blockers": blockers,
        "safe_manifest_ref": "provider_safe_manifest.json",
        "claim_boundaries": {
            "provider_smoke": "blocked" if blockers else "ready_or_completed",
            "runtime_verification": "reported",
            "human_acceptance": "not_claimed",
            "business_validation": "not_validated",
            "durable_memory": "not_written",
        },
        "non_claims": _non_claims(),
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }


def render_provider_validation_report_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Provider Validation Gate Report",
            "",
            f"Status: {report.get('status', 'unknown')}",
            f"Provider calls started: {str(report.get('provider_calls_started') is True).lower()}",
            "Human acceptance: not claimed",
            "Business validation: not claimed",
            "Writes long-term memory: false",
            "Writes Company KB: false",
            "",
            "## Blockers",
            "",
            _blocker_lines(report.get("blockers")),
            "",
            "## Non-Claim",
            "",
            "\n".join(f"- {item}" for item in _list(report.get("non_claims"))) or "- none",
            "",
        ]
    )


def _blocked_or_ready_result(blockers: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "kind": PROVIDER_VALIDATION_RESULT_KIND,
        "artifact_type": PROVIDER_VALIDATION_RESULT_KIND,
        "schema_version": SCHEMA_VERSION,
        "status": "blocked" if blockers else "ready_not_run",
        "provider_calls_started": False,
        "blockers": blockers,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }


def _status_from_result(result: dict[str, Any], blockers: list[dict[str, str]]) -> str:
    status = str(result.get("status", "ready_not_run"))
    if status == "failed":
        return "failed"
    if blockers:
        return "blocked"
    return status


def _effective_blockers(preflight_blockers: list[dict[str, str]], result: dict[str, Any]) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    for item in preflight_blockers + _list(result.get("blockers")):
        blocker = _dict(item)
        blocker_id = str(blocker.get("blocker_id", "")).strip()
        message = str(blocker.get("message", "")).strip()
        if not blocker_id:
            continue
        normalized = {"blocker_id": blocker_id, "message": message or "blocked"}
        if normalized not in blockers:
            blockers.append(normalized)
    return blockers


def _non_claims() -> list[str]:
    return [
        "not human acceptance",
        "not business validation",
        "not durable memory",
        "not Company KB promotion",
        "not provider success unless provider_validation_result.json says succeeded",
    ]


def _blocker_lines(value: Any) -> str:
    blockers = _list(value)
    if not blockers:
        return "- none"
    return "\n".join(f"- {_dict(item).get('blocker_id', 'unknown')}: {_dict(item).get('message', 'blocked')}" for item in blockers)


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


__all__ = (
    "PROVIDER_SAFE_MANIFEST_KIND",
    "build_provider_safe_manifest",
    "build_provider_validation_gate_report",
    "render_provider_validation_report_markdown",
    "run_provider_validation_gate",
)
