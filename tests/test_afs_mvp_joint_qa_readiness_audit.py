from __future__ import annotations

import json
from pathlib import Path

from tools.afs_mvp_joint_qa_readiness_audit import build_readiness_audit


def test_joint_qa_readiness_audit_summarizes_open_provider_blockers(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "live_image_runtime" / "runs" / "project" / "job" / "B" / "keyframe_generation_safe_manifest.json",
        {
            "status": "blocked",
            "provider_calls_started": True,
            "retry_count": 1,
            "blocks": [{"block_id": "remote_image_provider_not_ready", "reason": "safe reason"}],
        },
    )
    _write_json(
        tmp_path / "live_kling_i2v_runtime" / "runs" / "project" / "job" / "video_generation_safe_manifest.json",
        {
            "status": "blocked",
            "provider_calls_started": False,
            "blocks": [{"block_id": "remote_video_provider_not_ready", "reason": "Provider service not found: kling_i2v"}],
        },
    )
    _write_json(
        tmp_path / "kling_provider_preflight_after_blocker_hardening.json",
        {
            "status": "blocked",
            "checks": {
                "block_id": "provider_service_missing",
                "service_present": False,
                "available_video_service_ids": [],
            },
            "secrets_printed": False,
        },
    )
    _write_json(tmp_path / "frontend_ui_reviewer_after_fix2_report.json", {"status": "passed", "issues": []})
    _write_json(tmp_path / "gate_closed_8790_ui_smoke_corrected_report.json", {"status": "passed"})

    audit = build_readiness_audit(tmp_path)

    blockers = {item["blocker_id"]: item for item in audit["provider_blockers"]}
    assert audit["status"] == "needs_fixes"
    assert audit["human_acceptance_claim"] == "not_claimed"
    assert blockers["P1-KLING-CONFIG-MISSING"]["root_cause_block_id"] == "provider_service_missing"
    assert blockers["P1-KLING-CONFIG-MISSING"]["provider_calls_started"] is False
    assert blockers["P1-IMAGE-B-PROVIDER-READINESS"]["root_cause_block_id"] == "remote_image_provider_not_ready"
    assert blockers["P1-IMAGE-B-PROVIDER-READINESS"]["retry_count"] == 1
    serialized = json.dumps(audit, ensure_ascii=False)
    assert str(tmp_path) not in serialized
    assert "safe reason" not in serialized


def test_joint_qa_readiness_audit_reads_powershell_utf16_evidence(tmp_path: Path) -> None:
    payload = {
        "status": "blocked",
        "checks": {"block_id": "provider_service_missing", "service_present": False},
        "secrets_printed": False,
    }
    path = tmp_path / "kling_provider_preflight_after_blocker_hardening.json"
    path.write_text(json.dumps(payload), encoding="utf-16")

    audit = build_readiness_audit(tmp_path)

    blockers = {item["blocker_id"]: item for item in audit["provider_blockers"]}
    assert blockers["P1-KLING-CONFIG-MISSING"]["root_cause_block_id"] == "provider_service_missing"


def test_joint_qa_readiness_audit_marks_missing_kling_evidence_as_missing(tmp_path: Path) -> None:
    audit = build_readiness_audit(tmp_path)

    blockers = {item["blocker_id"]: item for item in audit["provider_blockers"]}
    assert blockers["P1-KLING-CONFIG-MISSING"]["status"] == "missing_evidence"
    assert blockers["P1-KLING-CONFIG-MISSING"]["root_cause_block_id"] == "missing_evidence"


def test_joint_qa_readiness_audit_accepts_startup_config_kling_success_evidence(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "live_image_runtime" / "runs" / "project" / "job" / "B" / "keyframe_generation_safe_manifest.json",
        {"status": "succeeded", "provider_calls_started": True},
    )
    _write_json(
        tmp_path / "kling_provider_preflight_startup_secrets_config_gate_open.json",
        {"status": "ready", "checks": {"service_present": True}, "secrets_printed": False},
    )
    _write_json(
        tmp_path
        / "live_kling_i2v_startup_config_runtime"
        / "runs"
        / "project"
        / "job"
        / "video_generation_safe_manifest.json",
        {"status": "succeeded", "provider_calls_started": True, "outputs": [{"candidate_id": "candidate_001"}]},
    )
    _write_json(
        tmp_path / "live_kling_i2v_startup_config_recovery_poll_report.json",
        {"status": "succeeded", "preview_check": {"content_type": "video/mp4"}},
    )
    _write_json(
        tmp_path / "live_kling_i2v_video_inspection.json",
        {"format_duration_sec": 5.04, "video_stream": {"width": 1176, "height": 1764}},
    )

    audit = build_readiness_audit(tmp_path)

    blockers = {item["blocker_id"]: item for item in audit["provider_blockers"]}
    roles = {item["role_id"]: item for item in audit["role_checks"]}
    assert "P1-KLING-CONFIG-MISSING" not in blockers
    assert roles["video_qa"]["status"] == "passed"
    assert roles["video_qa"]["evidence_ref"] == "live_kling_i2v_startup_config_recovery_poll_report.json"


def test_joint_qa_readiness_audit_uses_image_ready_preflight_for_next_action(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "live_image_runtime" / "runs" / "project" / "job" / "B" / "keyframe_generation_safe_manifest.json",
        {
            "status": "blocked",
            "provider_calls_started": True,
            "retry_count": 1,
            "blocks": [{"block_id": "remote_image_provider_not_ready", "reason": "safe reason"}],
        },
    )
    preflight_path = tmp_path / "image_provider_preflight_startup_secrets_config_gate_open.json"
    preflight_path.write_text(
        json.dumps(
            {
                "status": "ready",
                "checks": {
                    "service_present": True,
                    "execution_backend": "rest_api",
                    "gate": {"env": "AFS_ALLOW_REMOTE_IMAGE", "enabled": True},
                },
                "secrets_printed": False,
            }
        ),
        encoding="utf-8-sig",
    )
    _write_json(
        tmp_path / "image_provider_preflight_startup_secrets_config.json",
        {
            "status": "gate_closed",
            "checks": {
                "service_present": True,
                "execution_backend": "rest_api",
                "gate": {"env": "AFS_ALLOW_REMOTE_IMAGE", "enabled": False},
            },
            "secrets_printed": False,
        },
    )
    _write_json(
        tmp_path / "live_kling_i2v_startup_config_runtime" / "runs" / "project" / "job" / "video_generation_safe_manifest.json",
        {"status": "succeeded", "provider_calls_started": True},
    )
    _write_json(
        tmp_path / "live_kling_i2v_startup_config_recovery_poll_report.json",
        {"status": "succeeded", "preview_check": {"content_type": "video/mp4"}},
    )

    audit = build_readiness_audit(tmp_path)

    blockers = {item["blocker_id"]: item for item in audit["provider_blockers"]}
    image_blocker = blockers["P1-IMAGE-B-PROVIDER-READINESS"]
    assert image_blocker["status"] == "blocked"
    assert image_blocker["preflight_status"] == "ready"
    assert "image_provider_preflight_startup_secrets_config_gate_open.json" in image_blocker["evidence_refs"]
    assert "image_provider_preflight_startup_secrets_config.json" not in image_blocker["evidence_refs"]
    assert audit["next_actions"] == [
        "Image provider preflight is ready; after explicit image retry approval, run one B-only live retry with candidate_count=1."
    ]


def test_joint_qa_readiness_audit_clears_image_blocker_after_b_only_retry_success(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "live_image_runtime" / "runs" / "project" / "job" / "B" / "keyframe_generation_safe_manifest.json",
        {
            "status": "blocked",
            "provider_calls_started": True,
            "retry_count": 1,
            "blocks": [{"block_id": "remote_image_provider_not_ready", "reason": "safe reason"}],
        },
    )
    _write_json(
        tmp_path / "image_b_only_live_retry_20260615.json",
        {
            "status": "succeeded",
            "provider_calls_started": True,
            "arm_id": "B",
            "include_fixed_assets": False,
            "provider_output_count": 1,
        },
    )
    _write_json(
        tmp_path / "live_kling_i2v_startup_config_runtime" / "runs" / "project" / "job" / "video_generation_safe_manifest.json",
        {"status": "succeeded", "provider_calls_started": True},
    )
    _write_json(
        tmp_path / "live_kling_i2v_startup_config_recovery_poll_report.json",
        {"status": "succeeded", "preview_check": {"content_type": "video/mp4"}},
    )

    audit = build_readiness_audit(tmp_path)

    blockers = {item["blocker_id"]: item for item in audit["provider_blockers"]}
    assert "P1-IMAGE-B-PROVIDER-READINESS" not in blockers
    assert audit["status"] == "recommended"
    assert audit["next_actions"] == []


def test_readiness_audit_accepts_browser_drill_manifests_and_preserves_role_gaps(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "browser_qa_summary.json",
        {
            "artifact_type": "afs_browser_acceptance_drill_summary",
            "role_checks": [
                {"role_id": "ordinary_internal_tester", "status": "passed", "evidence_ref": "browser_qa_summary.json"},
                {"role_id": "creative_director", "status": "passed", "evidence_ref": "browser_qa_summary.json"},
                {"role_id": "asset_manager", "status": "passed", "evidence_ref": "browser_qa_summary.json"},
                {"role_id": "video_qa", "status": "passed", "evidence_ref": "browser_qa_summary.json"},
                {"role_id": "safety_release_qa", "status": "passed", "evidence_ref": "browser_qa_summary.json"},
                {"role_id": "runbook_paths_1_6", "status": "needs_fixes", "evidence_ref": "browser_qa_summary.json"},
                {"role_id": "frontend_ui_reviewer", "status": "passed", "evidence_ref": "browser_qa_summary.json"},
            ],
            "next_actions": ["Run one extra authorized I2I live reference call."],
        },
    )
    _write_json(
        tmp_path / "runtime_service" / "runs" / "project" / "image_job" / "keyframe_generation_safe_manifest.json",
        {"status": "succeeded", "provider_calls_started": True, "output_count": 1},
    )
    _write_json(
        tmp_path / "runtime_service" / "runs" / "project" / "video_job" / "video_generation_safe_manifest.json",
        {"status": "succeeded", "provider_calls_started": True, "outputs": [{"candidate_id": "candidate_001"}]},
    )

    audit = build_readiness_audit(tmp_path)

    roles = {item["role_id"]: item for item in audit["role_checks"]}
    assert audit["provider_blockers"] == []
    assert audit["status"] == "needs_fixes"
    assert roles["runbook_paths_1_6"]["status"] == "needs_fixes"
    assert audit["next_actions"] == ["Run one extra authorized I2I live reference call."]


def test_readiness_audit_marks_browser_drill_missing_roles_as_needs_fixes(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "browser_qa_summary.json",
        {
            "artifact_type": "afs_browser_acceptance_drill_summary",
            "role_checks": [],
        },
    )
    _write_json(
        tmp_path / "runtime_service" / "runs" / "project" / "image_job" / "keyframe_generation_safe_manifest.json",
        {"status": "succeeded", "provider_calls_started": True, "output_count": 1},
    )
    _write_json(
        tmp_path / "runtime_service" / "runs" / "project" / "video_job" / "video_generation_safe_manifest.json",
        {"status": "succeeded", "provider_calls_started": True, "outputs": [{"candidate_id": "candidate_001"}]},
    )

    audit = build_readiness_audit(tmp_path)

    assert audit["provider_blockers"] == []
    assert audit["status"] == "needs_fixes"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
