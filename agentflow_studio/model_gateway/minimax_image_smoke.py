from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow_studio.model_gateway.company_secrets import CompanyProviderSecrets
from agentflow_studio.model_gateway.minimax_image_plan import (
    api_key,
    build_minimax_image_request_plan,
    resolve_image_base_url,
)
from agentflow_studio.model_gateway.minimax_image_runtime import (
    generate_minimax_image_outputs,
    runtime_subject_reference,
)
from agentflow_studio.utils import write_json


MANIFEST_NAME = "minimax_image_smoke_manifest.json"


def run_minimax_image_smoke(
    store: CompanyProviderSecrets,
    *,
    service_id: str,
    prompt: str,
    output_dir: str | Path,
    aspect_ratio: str = "9:16",
    candidate_count: int = 1,
    timeout_sec: float = 120.0,
    model_name_override: str | None = None,
    subject_reference_image_path: str | Path | None = None,
    seed: int | None = None,
) -> dict[str, Any]:
    subject_reference = runtime_subject_reference(subject_reference_image_path)
    plan = build_minimax_image_request_plan(
        store,
        service_id=service_id,
        prompt=prompt,
        aspect_ratio=aspect_ratio,
        candidate_count=candidate_count,
        model_name_override=model_name_override,
        subject_reference_image_ref=(
            subject_reference["image_ref"] if subject_reference is not None else None
        ),
        require_live_gate=True,
    )
    account = store.account(str(store.service(service_id).get("account_ref") or ""))
    output_root = Path(output_dir)
    outputs = generate_minimax_image_outputs(
        base_url=resolve_image_base_url(store, account, store.service(service_id)),
        api_key=api_key(account),
        model=str(plan["create_request"]["json"]["model"]),
        prompt=prompt,
        output_root=output_root,
        candidate_count=candidate_count,
        aspect_ratio=aspect_ratio,
        timeout_sec=timeout_sec,
        subject_reference_image_path=(
            subject_reference["path"] if subject_reference is not None else None
        ),
        seed=seed,
    )
    manifest: dict[str, Any] = {
        "schema_version": "minimax_image_smoke_manifest.v1",
        "status": "succeeded",
        "service_id": service_id,
        "provider": "minimax_image",
        "api_family": plan["api_family"],
        "capability": "image",
        "model": plan["create_request"]["json"]["model"],
        "required_gate": plan.get("required_gate"),
        "gate_status": plan.get("gate_status"),
        "candidate_count": candidate_count,
        "outputs": outputs,
        "artifact_policy": {
            "provider_urls_persisted": False,
            "authorization_header_persisted": False,
            "api_key_persisted": False,
            "response_body_persisted": False,
            "writes_long_term_memory": False,
        },
        "claim_boundary": "provider_smoke_only_not_creative_quality",
    }
    if subject_reference is not None:
        manifest["api_family"] = "i2i"
        manifest["input_image"] = {
            "path_persisted": False,
            "byte_count": subject_reference["byte_count"],
            "sha256": subject_reference["sha256"],
            "mime_type": subject_reference["mime_type"],
        }
    write_json(output_root / MANIFEST_NAME, manifest)
    return manifest
