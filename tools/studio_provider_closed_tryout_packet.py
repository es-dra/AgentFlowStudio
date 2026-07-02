from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_VERDICT = "internal_provider_closed_tryout_ready"
EVIDENCE_STATE = "provider_closed_internal_tryout_packet_structure_verified"
ACCEPTED_GENERATION_PLAN_CHECK_ID = "accepted_generation_plan_default_blocked_preview"
REQUIRED_SOURCE_REMAINING_GATES = {
    "provider_smoke_requires_explicit_authorization",
    "generated_media_quality_requires_provider_run_and_review",
    "product_readiness_not_claimed",
    "human_creative_acceptance_not_claimed",
    "business_validation_not_claimed",
    "public_legal_patent_claim_not_made",
    "deploy_server_sync_runtime_health_not_claimed",
    "cos_active_rule_promotion_not_made",
}
EVIDENCE_CHECKS = {
    "storyboard_content_quality": "storyboard_content_quality",
    "asset_candidate_fixed_asset_path": "asset_candidate_fixed_asset_path",
    "production_graph_fixed_asset_reuse": "production_graph_fixed_asset_reuse",
    "keyframe_request_preflight_blocked_bridge": "keyframe_preflight_blocked_bridge",
    "feedback_overlay_context": "feedback_overlay_human_gate_non_claim",
    "provider_closed_browser_runtime": "provider_closed_browser_runtime",
    "accepted_generation_plan_bridge": ACCEPTED_GENERATION_PLAN_CHECK_ID,
}
NON_CLAIM_GATES = [
    ("provider_smoke", "provider_smoke_requires_explicit_authorization"),
    ("generated_media_quality", "generated_media_quality_requires_provider_run_and_review"),
    ("product_readiness", "product_readiness_not_claimed"),
    ("human_creative_acceptance", "human_creative_acceptance_not_claimed"),
    ("business_validation", "business_validation_not_claimed"),
    ("public_legal_patent", "public_legal_patent_claim_not_made"),
    ("deploy_runtime_health", "deploy_server_sync_runtime_health_not_claimed"),
    ("cos_active_rule_promotion", "cos_active_rule_promotion_not_made"),
]


class PacketError(ValueError):
    """Raised when a readiness report cannot produce a safe tryout packet."""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report_path = Path(args.readiness_report)
        report = _load_json(report_path)
        packet = build_tryout_packet(report, readiness_report_path=report_path)
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
        if args.markdown:
            markdown_path = Path(args.markdown)
            markdown_path.parent.mkdir(parents=True, exist_ok=True)
            markdown_path.write_text(render_tryout_markdown(packet), encoding="utf-8")
        print(json.dumps({"status": "passed", "output": str(output_path), "provider_calls_started": False}, ensure_ascii=False))
        return 0
    except PacketError as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a provider-closed internal tryout packet from the T50 readiness report.")
    parser.add_argument("--readiness-report", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--markdown", default="")
    return parser.parse_args(argv)


def build_tryout_packet(report: dict[str, Any], *, readiness_report_path: Path | str = "") -> dict[str, Any]:
    readiness = _validated_readiness(report)
    checks = {str(item.get("check_id", "")): item for item in readiness.get("checks", []) if isinstance(item, dict)}
    missing_checks = sorted(set(EVIDENCE_CHECKS.values()) - set(checks))
    if missing_checks:
        raise PacketError(f"readiness report missing checks: {', '.join(missing_checks)}")
    accepted_generation_plan_bridge = _validated_accepted_generation_plan_bridge(checks)

    packet = {
        "artifact_type": "afs_provider_closed_internal_tryout_packet",
        "schema_version": "0.1.0",
        "status": "review_pending_internal_operator",
        "evidence_state": EVIDENCE_STATE,
        "source_report": {
            "path": _display_path(readiness_report_path),
            "artifact_type": report.get("artifact_type", ""),
            "schema_version": report.get("schema_version", ""),
            "status": report.get("status", ""),
        },
        "source_verdict": SOURCE_VERDICT,
        "tryout_verdict": SOURCE_VERDICT,
        "product_readiness": readiness.get("product_readiness", ""),
        "quality_evidence": readiness.get("quality_evidence", ""),
        "governance_evidence": readiness.get("governance_evidence", ""),
        "case_id": report.get("case_id", ""),
        "project_id": report.get("project_id", ""),
        "provider_calls_started": False,
        "provider_smoke_claimed": False,
        "live_provider_call_claimed": False,
        "generated_media_claimed": False,
        "human_creative_acceptance_claimed": False,
        "business_validation_claimed": False,
        "public_legal_patent_claimed": False,
        "deploy_runtime_health_claimed": False,
        "cos_active_rule_promotion_claimed": False,
        "source_artifacts": _source_artifacts(report),
        "source_evidence_summary": _source_evidence_summary(checks),
        "accepted_generation_plan_bridge": accepted_generation_plan_bridge,
        "readiness_checks": [_safe_check(item) for item in readiness.get("checks", [])],
        "remaining_gate_non_claims": _remaining_gate_non_claims(readiness),
        "operator_review_packet": _operator_review_packet(),
        "cleanup_boundary": {
            "generated_runs_artifacts_staging": "do_not_stage_unless_explicitly_intended",
            "demo_docs_boundary": "docs/demo-docs-20260629 remains do-not-touch",
            "provider_config_boundary": "unchanged",
        },
    }
    _assert_packet_safe(packet)
    return packet


def render_tryout_markdown(packet: dict[str, Any]) -> str:
    lines = [
        "# AFS Provider-Closed Internal Tryout Packet",
        "",
        f"Status: `{_safe_inline(packet.get('status'))}`",
        f"Source verdict: `{_safe_inline(packet.get('source_verdict'))}`",
        f"Evidence state: `{_safe_inline(packet.get('evidence_state'))}`",
        f"Provider calls started: `{str(packet.get('provider_calls_started')).lower()}`",
        "",
        "## Evidence Summary",
        "",
    ]
    for item in packet.get("source_evidence_summary", []):
        lines.append(f"- `{_safe_inline(item.get('summary_id'))}`: `{_safe_inline(item.get('status'))}`")
    lines.extend(["", "## Remaining Gates", ""])
    for gate in packet.get("remaining_gate_non_claims", []):
        lines.append(f"- `{_safe_inline(gate.get('gate_id'))}`: claimed=`{str(gate.get('claimed')).lower()}`")
    lines.extend([
        "",
        "## Operator Decision",
        "",
        "Decision: `continue_to_provider_smoke_authorization_review` / `request_fix_before_provider_smoke` / `defer_or_split_before_provider_smoke`",
        "",
        "Notes:",
        "",
        "```text",
        "",
        "```",
        "",
    ])
    return "\n".join(lines)


def _validated_readiness(report: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(report, dict):
        raise PacketError("readiness report must be a JSON object")
    readiness = report.get("delivery_readiness")
    if not isinstance(readiness, dict):
        raise PacketError("readiness report is missing delivery_readiness")
    if readiness.get("verdict") != SOURCE_VERDICT:
        raise PacketError(f"source verdict must be {SOURCE_VERDICT}")
    if report.get("provider_calls_started") is not False or _provider_calls_started(report):
        raise PacketError("readiness report must preserve provider_calls_started=false")
    if report.get("status") != "passed":
        raise PacketError("readiness report status must be passed")
    failed = [str(item.get("check_id", "")) for item in readiness.get("checks", []) if item.get("status") != "passed"]
    if failed:
        raise PacketError(f"readiness checks are not all passed: {', '.join(failed)}")
    source_gates = set(readiness.get("remaining_gates") or [])
    missing_gates = sorted(REQUIRED_SOURCE_REMAINING_GATES - source_gates)
    if missing_gates:
        raise PacketError(f"readiness report missing remaining-gate non-claims: {', '.join(missing_gates)}")
    return readiness


def _source_artifacts(report: dict[str, Any]) -> dict[str, Any]:
    accepted_plan = report.get("accepted_generation_plan_modal")
    accepted_plan = accepted_plan if isinstance(accepted_plan, dict) else {}
    return {
        "screenshot": _display_path(report.get("screenshot", "")),
        "fixed_asset_id": report.get("fixed_asset_id", ""),
        "production_graph_artifact_id": report.get("production_graph_artifact_id", ""),
        "feedback_overlay_id": report.get("overlay_id", ""),
        "first_bridge_artifact_id": report.get("first_bridge_artifact_id", ""),
        "second_bridge_artifact_id": report.get("second_bridge_artifact_id", ""),
        "second_request_plan_artifact_id": report.get("second_request_plan_artifact_id", ""),
        "accepted_generation_plan_preview_artifact_id": accepted_plan.get("artifact_id", ""),
        "accepted_generation_plan_preview_job_id": accepted_plan.get("job_id", ""),
    }


def _source_evidence_summary(checks: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "summary_id": summary_id,
            "source_check_id": check_id,
            "status": checks[check_id].get("status", ""),
            "evidence": checks[check_id].get("evidence", {}),
        }
        for summary_id, check_id in EVIDENCE_CHECKS.items()
    ]


def _remaining_gate_non_claims(readiness: dict[str, Any]) -> list[dict[str, Any]]:
    source_gates = set(readiness.get("remaining_gates") or [])
    return [
        {
            "gate_id": gate_id,
            "source_remaining_gate": source_gate if source_gate in source_gates else "",
            "claimed": False,
        }
        for gate_id, source_gate in NON_CLAIM_GATES
    ]


def _validated_accepted_generation_plan_bridge(checks: dict[str, dict[str, Any]]) -> dict[str, Any]:
    item = checks.get(ACCEPTED_GENERATION_PLAN_CHECK_ID)
    evidence = item.get("evidence") if isinstance(item, dict) else None
    if not isinstance(evidence, dict):
        raise PacketError("accepted generation plan bridge evidence is missing")
    required_non_claims = {
        "not_provider_smoke",
        "not_generated_media_qa",
        "not_product_readiness",
        "not_human_creative_acceptance",
        "not_business_validation",
        "not_deploy_runtime_health",
        "fixture_demo_not_acceptance",
    }
    explicit_non_claims = set(evidence.get("explicit_non_claims") or [])
    expected = {
        "modal_opened": True,
        "default_fixture_mode": "default_unconfirmed",
        "preview_status": "blocked",
        "job_status": "blocked",
        "accepted": False,
        "source_mode": "fixture_demo",
        "fixture_demo_non_acceptance": True,
        "provider_calls_started": False,
        "provider_gate": "closed",
        "provider_smoke_claimed": False,
        "generated_media_quality_claimed": False,
        "product_readiness_claimed": False,
        "human_creative_acceptance_claimed": False,
        "business_validation_claimed": False,
        "deploy_runtime_health_claimed": False,
        "cos_active_rule_promotion_claimed": False,
        "rendered_blocked_status": True,
        "rendered_provider_not_started": True,
        "rendered_product_readiness_not_claimed": True,
    }
    wrong = [key for key, value in expected.items() if evidence.get(key) != value]
    if wrong:
        raise PacketError(f"accepted generation plan bridge evidence failed non-claim checks: {', '.join(wrong)}")
    if not required_non_claims.issubset(explicit_non_claims):
        missing = sorted(required_non_claims - explicit_non_claims)
        raise PacketError(f"accepted generation plan bridge missing non-claims: {', '.join(missing)}")
    if not evidence.get("artifact_id") or not evidence.get("job_id"):
        raise PacketError("accepted generation plan bridge is missing preview artifact/job evidence")
    return {
        "check_id": ACCEPTED_GENERATION_PLAN_CHECK_ID,
        "preview_status": evidence["preview_status"],
        "job_status": evidence["job_status"],
        "packet_state": evidence.get("packet_state", ""),
        "accepted": False,
        "source_mode": evidence["source_mode"],
        "fixture_demo_non_acceptance": True,
        "provider_calls_started": False,
        "provider_gate": "closed",
        "artifact_id": evidence.get("artifact_id", ""),
        "job_id": evidence.get("job_id", ""),
        "explicit_non_claims": sorted(required_non_claims),
    }


def _operator_review_packet() -> dict[str, Any]:
    return {
        "reviewer_role": "internal_provider_closed_tryout_operator",
        "review_status": "pending_operator_review",
        "decision_options": [
            "continue_to_provider_smoke_authorization_review",
            "request_fix_before_provider_smoke",
            "defer_or_split_before_provider_smoke",
        ],
        "forbidden_claims": [
            "provider smoke",
            "generated media quality acceptance",
            "human creative acceptance",
            "business validation",
            "public legal patent approval",
            "deploy Runtime health",
            "COS active rule promotion",
        ],
    }


def _safe_check(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "check_id": item.get("check_id", ""),
        "status": item.get("status", ""),
        "evidence": item.get("evidence", {}),
    }


def _provider_calls_started(value: Any) -> bool:
    if isinstance(value, dict):
        if value.get("provider_calls_started") is True:
            return True
        return any(_provider_calls_started(item) for item in value.values())
    if isinstance(value, list):
        return any(_provider_calls_started(item) for item in value)
    return False


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise PacketError(f"cannot read readiness report: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise PacketError(f"readiness report is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise PacketError("readiness report must be a JSON object")
    return data


def _display_path(value: Any) -> str:
    if not value:
        return ""
    path = Path(str(value))
    try:
        resolved = path.resolve()
        if _is_relative_to(resolved, REPO_ROOT):
            return resolved.relative_to(REPO_ROOT).as_posix()
    except OSError:
        pass
    return path.as_posix() if not path.is_absolute() else path.name


def _assert_packet_safe(packet: dict[str, Any]) -> None:
    text = json.dumps(packet, ensure_ascii=False).lower()
    unsafe_markers = ('"provider_raw"', '"signed_url"', "data_base64", "bearer ", "api_key")
    if any(marker in text for marker in unsafe_markers):
        raise PacketError("packet contains an unsafe marker")


def _safe_inline(value: Any) -> str:
    return str(value or "").replace("`", "'")


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


if __name__ == "__main__":
    raise SystemExit(main())
