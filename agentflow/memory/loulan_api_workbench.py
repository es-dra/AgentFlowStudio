from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from narratocut.utils import write_json


SCHEMA_VERSION = "0.1.0"
PLAN_TYPE = "agentflow_loulan_api_workbench_plan"
LOULAN_PACKAGE_TYPE = "agentflow_loulan_memory_package"
DEFAULT_PROVIDER_ADAPTER = "openai_compatible_image"
IMAGE_GATE = "NARRATOCUT_ALLOW_REMOTE_IMAGE"
REUSABLE_STATUSES = frozenset({"approved", "promoted", "merged"})
UNSAFE_OUTPUT_FRAGMENTS = (
    "D:\\",
    "C:\\",
    "file://",
    "Bearer ",
    "signed_url",
    "token=",
    "api_key",
    "secret_key",
    ".mp4",
    ".mov",
)


def build_loulan_api_workbench_plan(
    package: dict[str, Any],
    *,
    created_at: str,
    provider_adapter_id: str = DEFAULT_PROVIDER_ADAPTER,
) -> dict[str, Any]:
    """Build a no-call Loulan image API workbench plan from a memory package."""
    _validate_package(package)
    references = _reference_pack_entries(package)
    request_ready = bool(references)
    request_id = f"{package['package_id']}_image_request_preview_001"
    plan = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": PLAN_TYPE,
        "created_at": created_at,
        "package_id": package["package_id"],
        "project_id": package.get("project", {}).get("project_id"),
        "dry_run_only": True,
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "provider_adapter": _provider_adapter(provider_adapter_id, package),
        "reference_pack": _reference_pack(package, references),
        "prompt_compiler": _prompt_compiler(package, references),
        "request_manifest": _request_manifest(package, references, request_id, provider_adapter_id),
        "response_ledger": _response_ledger(request_id, request_ready),
        "qa_gate": _qa_gate(request_ready),
        "promotion_gate": _promotion_gate(package, request_ready),
        "blocking_reasons": [] if request_ready else ["no_approved_reference_hashes"],
        "claim_boundaries": _claim_boundaries(),
    }
    _reject_unsafe_output(plan)
    return plan


def write_loulan_api_workbench_plan(plan: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    paths = [
        write_json(output_root / "loulan_api_workbench_plan.json", plan),
        write_json(output_root / "reference_pack.json", plan["reference_pack"]),
        write_json(output_root / "prompt_compiler_preview.json", plan["prompt_compiler"]),
        write_json(output_root / "request_manifest.json", plan["request_manifest"]),
        write_json(output_root / "response_ledger.json", plan["response_ledger"]),
        write_json(
            output_root / "qa_promotion_gates.json",
            {"qa_gate": plan["qa_gate"], "promotion_gate": plan["promotion_gate"]},
        ),
    ]
    report_path = output_root / "loulan_api_workbench_plan.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_loulan_api_workbench_plan_report(plan), encoding="utf-8")
    paths.append(report_path)
    return paths


def render_loulan_api_workbench_plan_report(plan: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Loulan API Workbench Plan",
            "",
            f"- Package: `{plan['package_id']}`",
            f"- Provider adapter: `{plan['provider_adapter']['adapter_id']}`",
            "- Provider calls: not started",
            "- Request mode: dry-run preview only",
            f"- Reference pack: `{plan['reference_pack']['status']}`",
            f"- Requests previewed: {len(plan['request_manifest']['requests'])}",
            f"- QA gate: `{plan['qa_gate']['status']}`",
            f"- Promotion gate: `{plan['promotion_gate']['status']}`",
            "- Durable Memory runtime: not implemented",
            "",
        ]
    )


def _validate_package(package: dict[str, Any]) -> None:
    if package.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Loulan package schema_version must be 0.1.0")
    if package.get("artifact_type") != LOULAN_PACKAGE_TYPE:
        raise ValueError(f"Loulan package artifact_type must be {LOULAN_PACKAGE_TYPE}")
    if package.get("provider_calls_started") is not False:
        raise ValueError("Loulan package must not have provider calls started")
    if package.get("writes_long_term_memory") is not False:
        raise ValueError("Loulan package must not write long-term memory")
    if not package.get("package_id"):
        raise ValueError("Loulan package missing package_id")


def _provider_adapter(provider_adapter_id: str, package: dict[str, Any]) -> dict[str, Any]:
    safety = package.get("provider_route_safety") or {}
    return {
        "adapter_id": provider_adapter_id,
        "capability": "image",
        "required_gate": IMAGE_GATE,
        "gate_status": "not_checked_for_dry_run",
        "live_call_authorized": False,
        "request_preview_only": True,
        "provider_config_required_for_live_call": True,
        "source_route_failure_detected": bool(safety.get("unsafe_builtin_image_route_detected")),
    }


def _reference_pack_entries(package: dict[str, Any]) -> list[dict[str, str]]:
    eligible = set(package.get("next_context_bundle_draft", {}).get("eligible_memory_refs") or [])
    entries = []
    for asset in package.get("asset_summary", {}).get("assets") or []:
        memory_ref = str(asset.get("memory_ref") or "")
        sha = str(asset.get("sha256") or "")
        if memory_ref in eligible and asset.get("status") in REUSABLE_STATUSES and sha:
            entries.append(
                {
                    "memory_ref": memory_ref,
                    "asset_id": str(asset.get("asset_id") or ""),
                    "label": str(asset.get("label") or asset.get("asset_id") or memory_ref),
                    "sha256": sha,
                    "source_status": str(asset.get("status") or ""),
                }
            )
    return entries


def _reference_pack(package: dict[str, Any], references: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "reference_pack_id": f"{package['package_id']}_reference_pack_v0",
        "status": "ready" if references else "blocked",
        "references": references,
        "runtime_image_loading": "deferred",
        "copies_source_media": False,
    }


def _prompt_compiler(package: dict[str, Any], references: list[dict[str, str]]) -> dict[str, Any]:
    project = package.get("project") or {}
    ref_lines = "; ".join(f"{ref['memory_ref']} sha256={ref['sha256']}" for ref in references)
    prompt = (
        f"Loulan project: {project.get('title')}. "
        f"Target format: {project.get('target_format')}. "
        f"Use approved memory refs only: {ref_lines or 'none'}."
    )
    return {
        "status": "ready" if references else "blocked",
        "compiler_mode": "preview_only",
        "compiled_prompt_preview": prompt,
        "includes_candidate_refs": False,
    }


def _request_manifest(
    package: dict[str, Any],
    references: list[dict[str, str]],
    request_id: str,
    provider_adapter_id: str,
) -> dict[str, Any]:
    if not references:
        return {"status": "blocked", "requests": []}
    return {
        "status": "ready",
        "requests": [
            {
                "request_id": request_id,
                "capability": "image",
                "provider_adapter_id": provider_adapter_id,
                "live_call_authorized": False,
                "source_package_id": package["package_id"],
                "body_preview": {
                    "model": "<runtime_model_from_provider_config>",
                    "prompt": "<compiled_prompt_preview>",
                    "reference_images": [
                        {
                            "memory_ref": ref["memory_ref"],
                            "sha256": ref["sha256"],
                            "runtime_image_loader": "deferred",
                        }
                        for ref in references
                    ],
                },
            }
        ],
    }


def _response_ledger(request_id: str, request_ready: bool) -> dict[str, Any]:
    entries = []
    if request_ready:
        entries.append(
            {
                "request_id": request_id,
                "status": "not_submitted",
                "provider_task_id_persisted": False,
                "provider_urls_persisted": False,
                "generated_artifact_persisted": False,
            }
        )
    return {"status": "not_submitted", "entries": entries}


def _qa_gate(request_ready: bool) -> dict[str, Any]:
    return {
        "status": "pending_response" if request_ready else "blocked",
        "requires_human_review": True,
        "automatic_promotion_allowed": False,
    }


def _promotion_gate(package: dict[str, Any], request_ready: bool) -> dict[str, Any]:
    blocked_refs = package.get("next_context_bundle_draft", {}).get("blocked_memory_refs") or []
    return {
        "status": "blocked_until_human_review" if request_ready else "blocked_until_reference_pack_ready",
        "blocked_memory_refs": blocked_refs,
        "writes_long_term_memory": False,
        "allowed_decisions": ["promote", "merge", "reject", "expire"],
    }


def _claim_boundaries() -> dict[str, str]:
    return {
        "structure_verification": "api_workbench_plan_only",
        "runtime_verification": "not_run",
        "provider_smoke": "not_run",
        "human_acceptance": "not_acceptance",
        "business_validation": "not_validated",
        "durable_memory_runtime": "not_implemented",
    }


def _reject_unsafe_output(plan: dict[str, Any]) -> None:
    serialized = json.dumps(plan, ensure_ascii=False)
    if any(fragment.lower() in serialized.lower() for fragment in UNSAFE_OUTPUT_FRAGMENTS):
        raise ValueError("Loulan API workbench plan contains unsafe path, media ref, provider secret, or signed URL")
