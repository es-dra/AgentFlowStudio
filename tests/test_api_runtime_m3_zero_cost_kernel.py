from __future__ import annotations

import hashlib

from fastapi.testclient import TestClient

from apps.api.runtime_m3_zero_cost_kernel import (
    EVALUATION_REPORT_SCHEMA_VERSION,
    FEEDBACK_CANDIDATE_SCHEMA_VERSION,
    M3_CONTEXT_COMMAND_SCHEMA_VERSION,
    PROMOTION_DECISION_SCHEMA_VERSION,
)
from apps.api.runtime_script_core_truth import ANALYSIS_CANDIDATE_SCHEMA_VERSION
from apps.api.runtime_service import create_runtime_app


def _client(tmp_path) -> TestClient:
    return TestClient(create_runtime_app(runtime_root=tmp_path))


def _auth_headers(session_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {session_token}"}


def _register(client: TestClient, *, invite_code: str, email: str) -> dict:
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "strong-password-123",
            "display_name": email.split("@", 1)[0],
            "invite_code": invite_code,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _create_project(client: TestClient, project_id: str, headers: dict[str, str] | None = None) -> None:
    response = client.post("/projects", json={"project_id": project_id, "goal": f"{project_id} M3 audit"}, headers=headers or {})
    assert response.status_code == 200, response.text


def _create_revision(client: TestClient, project_id: str, text: str, headers: dict[str, str] | None = None) -> dict:
    response = client.post(
        f"/projects/{project_id}/script-revisions",
        json={"source_kind": "script", "source_text": text, "provenance": {"test": "m3_zero_cost"}},
        headers=headers or {},
    )
    assert response.status_code == 200, response.text
    return response.json()["revision"]


def _span(text: str, quote: str) -> dict:
    start = text.index(quote)
    return {"start": start, "end": start + len(quote), "quote": quote}


def _submit_analysis(client: TestClient, project_id: str, revision: dict, text: str, headers: dict[str, str] | None = None) -> dict:
    response = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates",
        json={
            "project_id": project_id,
            "revision_id": revision["revision_id"],
            "source_digest": revision["source_digest"],
            "schema_version": ANALYSIS_CANDIDATE_SCHEMA_VERSION,
            "named_characters": [
                {
                    "display_name": "Nia",
                    "aliases": ["she"],
                    "pronoun_links": [],
                    "evidence_spans": [_span(text, "Nia")],
                    "confidence": 0.93,
                    "status": "candidate",
                },
                {
                    "display_name": "Oren",
                    "aliases": [],
                    "pronoun_links": [],
                    "evidence_spans": [_span(text, "Oren")],
                    "confidence": 0.9,
                    "status": "candidate",
                },
            ],
            "main_scenes": [
                {
                    "name": "Night Workshop",
                    "evidence_spans": [_span(text, "night workshop")],
                    "confidence": 0.91,
                    "status": "candidate",
                }
            ],
            "style": "restrained suspense",
            "genre": "short drama",
            "tone": "tense",
            "actions": ["Nia hides a receipt"],
            "events": ["Oren notices the locked drawer"],
            "beats": [{"summary": "receipt becomes a motive"}],
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        },
        headers=headers or {},
    )
    assert response.status_code == 200, response.text
    return response.json()["projection"]


def _context_payload(project_id: str, revision: dict, **overrides) -> dict:
    payload = {
        "project_id": project_id,
        "script_revision_id": revision["revision_id"],
        "source_digest": revision["source_digest"],
        "schema_version": M3_CONTEXT_COMMAND_SCHEMA_VERSION,
        "instruction": "Zero-cost professional audit before any paid provider call.",
        "selected_node_id": "script_truth_revision_node",
        "selected_node_type": "script",
        "requested_domains": ["story_plan", "asset_bible", "context", "safety", "evaluation"],
        "constraints": {"draft_is_not_truth": True, "provider_disabled": True},
        "preferences": {"tone": "restrained"},
        "upstream_refs": [revision["revision_id"]],
        "downstream_refs": ["story_plan_candidate"],
        "exclusions": ["full_chat_history", "private_user_data"],
        "token_budget": 760,
        "provider_gates": {
            "llm": False,
            "image": False,
            "video": False,
            "audio": False,
            "asr": False,
            "vision": False,
            "external_download": False,
        },
        "tool_gates": {"model_call": False, "external_download": False, "media_generation": False},
        "trace_id": "trace_m3_api_test",
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }
    payload.update(overrides)
    return payload


def test_m3_zero_cost_auth_scope_and_context_fail_closed(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AFS_INVITE_CODES", "alpha-m3-invite,beta-m3-invite")
    client = _client(tmp_path)
    alpha = _register(client, invite_code="alpha-m3-invite", email="alpha-m3@example.com")
    beta = _register(client, invite_code="beta-m3-invite", email="beta-m3@example.com")
    alpha_headers = _auth_headers(alpha["session_token"])
    beta_headers = _auth_headers(beta["session_token"])
    _create_project(client, "alpha-m3-project", alpha_headers)
    text = "Nia waits in the night workshop while Oren studies the locked drawer."
    revision = _create_revision(client, "alpha-m3-project", text, alpha_headers)

    assert client.get("/projects/alpha-m3-project/m3-zero-cost/audit-truth").status_code == 401
    assert client.get("/projects/alpha-m3-project/m3-zero-cost/audit-truth", headers=beta_headers).status_code == 403
    assert client.get("/projects/alpha-m3-project/m3-zero-cost/audit-truth", headers=alpha_headers).status_code == 200
    assert client.post(
        "/projects/alpha-m3-project/m3-zero-cost/context-packs/preview",
        json=_context_payload("alpha-m3-project", revision, source_digest="0" * 64),
        headers=alpha_headers,
    ).status_code == 409
    assert client.post(
        "/projects/alpha-m3-project/m3-zero-cost/context-packs/preview",
        json=_context_payload("alpha-m3-project", revision),
        headers=beta_headers,
    ).status_code == 403


def test_context_pack_preview_confirm_undo_is_scoped_and_provider_closed(tmp_path) -> None:
    client = _client(tmp_path)
    project_id = "m3-context-pack-lifecycle"
    _create_project(client, project_id)
    text = "Nia waits in the night workshop while Oren studies the locked drawer."
    revision = _create_revision(client, project_id, text)
    _submit_analysis(client, project_id, revision, text)

    preview = client.post(f"/projects/{project_id}/m3-zero-cost/context-packs/preview", json=_context_payload(project_id, revision))
    assert preview.status_code == 200, preview.text
    context_pack = preview.json()["context_pack"]
    knowledge_pack = client.get(f"/projects/{project_id}/m3-zero-cost/knowledge-pack").json()["knowledge_pack"]
    assert 0 < len(context_pack["relevant_knowledge_refs"]) < knowledge_pack["entry_count"]
    assert context_pack["estimated_context_tokens"] <= context_pack["token_budget"]
    assert all(value is False for value in context_pack["provider_gates"].values())
    assert context_pack["draft_is_not_truth"] is True
    assert context_pack["feedback_is_not_memory"] is True

    confirmed = client.post(f"/projects/{project_id}/m3-zero-cost/context-packs/confirm", json=_context_payload(project_id, revision))
    assert confirmed.status_code == 200, confirmed.text
    receipt = confirmed.json()["receipt"]
    assert receipt["undo_available"] is True
    projection = confirmed.json()["projection"]
    assert projection["context_pack_count"] == 1
    assert projection["pending_feedback_not_memory"] is True

    undo = client.post(
        f"/projects/{project_id}/m3-zero-cost/context-packs/undo",
        json={
            "project_id": project_id,
            "context_pack_id": confirmed.json()["context_pack"]["context_pack_id"],
            "receipt_id": receipt["receipt_id"],
            "script_revision_id": revision["revision_id"],
            "source_digest": revision["source_digest"],
            "schema_version": M3_CONTEXT_COMMAND_SCHEMA_VERSION,
        },
    )
    assert undo.status_code == 200, undo.text
    assert undo.json()["receipt"]["status"] == "undone"
    assert undo.json()["projection"]["current_context_pack_id"] == ""


def test_feedback_promotion_and_evaluation_reports_enforce_memory_privacy_and_role_gates(tmp_path) -> None:
    client = _client(tmp_path)
    project_id = "m3-feedback-promotion"
    _create_project(client, project_id)
    output_digest = hashlib.sha256(b"zero-cost-output").hexdigest()

    rejected_memory = client.post(
        f"/projects/{project_id}/m3-zero-cost/feedback-candidates",
        json={
            "project_id": project_id,
            "schema_version": FEEDBACK_CANDIDATE_SCHEMA_VERSION,
            "source_kind": "user_edit",
            "output_ref": "script_revision:one",
            "output_digest": output_digest,
            "reason": "User shortened the dialogue.",
            "memory_write_requested": True,
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        },
    )
    assert rejected_memory.status_code == 422

    created = client.post(
        f"/projects/{project_id}/m3-zero-cost/feedback-candidates",
        json={
            "project_id": project_id,
            "schema_version": FEEDBACK_CANDIDATE_SCHEMA_VERSION,
            "source_kind": "user_edit",
            "output_ref": "script_revision:one",
            "output_digest": output_digest,
            "reason": "User shortened the dialogue and kept the subtext.",
            "privacy_scope": "private_project",
            "rights": {"allow_project_reuse": True, "allow_global_reuse": False},
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        },
    )
    assert created.status_code == 200, created.text
    feedback_id = created.json()["feedback_candidate"]["feedback_candidate_id"]
    assert created.json()["feedback_candidate"]["memory_status"] == "not_memory"

    blocked_global = client.post(
        f"/projects/{project_id}/m3-zero-cost/promotion-decisions",
        json={
            "project_id": project_id,
            "schema_version": PROMOTION_DECISION_SCHEMA_VERSION,
            "feedback_candidate_id": feedback_id,
            "target_scope": "global",
            "decision": "promoted",
            "reviewer": "m3-zero-cost-evaluator",
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        },
    )
    assert blocked_global.status_code == 422

    promoted = client.post(
        f"/projects/{project_id}/m3-zero-cost/promotion-decisions",
        json={
            "project_id": project_id,
            "schema_version": PROMOTION_DECISION_SCHEMA_VERSION,
            "feedback_candidate_id": feedback_id,
            "target_scope": "global",
            "decision": "promoted",
            "reviewer": "m3-zero-cost-evaluator",
            "evidence_refs": [{"type": "evaluation_report", "ref": "eval-safe"}],
            "conflict_review": {"status": "clear"},
            "privacy_review": {"allowed_cross_user_reuse": True, "private_data_removed": True},
            "rights_review": {"allow_global_reuse": True, "third_party_text": False},
            "rollback": {"supported": True, "strategy": "revoke promotion decision"},
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        },
    )
    assert promoted.status_code == 200, promoted.text

    for role in [
        "story_editor",
        "director_cinematographer_editor",
        "asset_production_continuity",
        "agent_context_safety_product",
    ]:
        report = client.post(
            f"/projects/{project_id}/m3-zero-cost/evaluation-reports",
            json={
                "project_id": project_id,
                "schema_version": EVALUATION_REPORT_SCHEMA_VERSION,
                "role": role,
                "target_ref": "m3-case:dialogue-a",
                "target_digest": output_digest,
                "independence": {"separate_pass": True, "implementation_author": False},
                "rubric_refs": ["m3_zero_cost_professional_kernel_rubric"],
                "dimensions": [{"name": "contract", "score": 0.9, "evidence": ["provider gates closed"]}],
                "critical_failures": [],
                "provider_dispatch_count": 0,
                "remote_dispatch_count": 0,
            },
        )
        assert report.status_code == 200, report.text

    projection = client.get(f"/projects/{project_id}/m3-zero-cost/audit-truth").json()["projection"]
    assert projection["evaluator_roles_covered"] == [
        "agent_context_safety_product",
        "asset_production_continuity",
        "director_cinematographer_editor",
        "story_editor",
    ]
    assert projection["pending_feedback_not_memory"] is True
    assert projection["promoted_global_count"] == 1
    assert projection["provider_dispatch_count"] == 0
