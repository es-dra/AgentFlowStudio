from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = REPO_ROOT / "tools"
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from tools import studio_quality_feedback_context_overlay_browser_qa as feedback_qa
from tools.studio_asset_context_browser_qa_support import runtime_test_client


def test_quality_feedback_browser_qa_screenshot_defaults_next_to_report(tmp_path) -> None:
    report = tmp_path / "evidence" / "quality_feedback_report.json"

    screenshot = feedback_qa.resolve_screenshot_path(report, "")

    assert screenshot == report.with_suffix(".png")


def test_quality_feedback_browser_qa_screenshot_can_be_overridden(tmp_path) -> None:
    report = tmp_path / "quality_feedback_report.json"
    explicit = tmp_path / "screens" / "quality-feedback.png"

    screenshot = feedback_qa.resolve_screenshot_path(report, str(explicit))

    assert screenshot == explicit.resolve()


def test_prepare_project_seeds_quality_feedback_node_contract(tmp_path) -> None:
    project_id = "studio-quality-feedback-seed-test"

    seed = feedback_qa.prepare_project(tmp_path, project_id=project_id)

    client = runtime_test_client(tmp_path)
    state = client.get(f"/projects/{project_id}/studio-state").json()["state"]
    node = state["nodes"][feedback_qa.NODE_ID]
    serialized = json.dumps(state, ensure_ascii=False).lower()

    assert seed == {"project_id": project_id, "node_id": feedback_qa.NODE_ID}
    assert state["order"] == [feedback_qa.NODE_ID]
    assert node["type"] == "image"
    assert node["status"] == "complete"
    assert node["result"]
    assert node["params"]["model"] == "local-image-fixture"
    assert "lastSafeManifest" not in node["params"]
    assert "data_base64" not in serialized
    assert "signed_url" not in serialized
    assert "provider_raw" not in serialized


def test_quality_feedback_artifact_assertion_accepts_runtime_overlay_chain(tmp_path) -> None:
    project_id = "studio-quality-feedback-artifacts-test"
    feedback_qa.prepare_project(tmp_path, project_id=project_id)
    client = runtime_test_client(tmp_path)
    feedback = client.post(
        "/feedback",
        json={
            "project_id": project_id,
            "generated_at": "2026-06-30T23:00:00+08:00",
            "feedback": {
                "kind": "studio_quality_feedback",
                "node_id": feedback_qa.NODE_ID,
                "node_type": "image",
                "artifact_ref": "artifact-keyframe-summary-browser-qa",
                "ratings": {"identity_similarity": 4, "scene_continuity": 3},
                "drift_notes": "Safe local feedback evidence for next context.",
            },
        },
    ).json()
    candidate = feedback["feedback_event"]["feedback_candidate"]
    promotion = client.post(
        f"/projects/{project_id}/feedback-candidate-promotions",
        json={
            "feedback_artifact_id": feedback["artifact"]["artifact_id"],
            "candidate_id": candidate["candidate_id"],
            "decision": "promote_to_context_overlay",
            "rationale": "Safe for next local context.",
            "reviewed_at": "2026-06-30T23:01:00+08:00",
        },
    ).json()
    overlay = client.post(
        f"/projects/{project_id}/feedback-candidate-context-overlays",
        json={
            "promotion_decision_artifact_id": promotion["artifact"]["artifact_id"],
            "overlay_intent": "Carry reviewed feedback into the next local context pass.",
            "generated_at": "2026-06-30T23:02:00+08:00",
        },
    ).json()
    summary = {
        "candidate_id": candidate["candidate_id"],
        "context_overlay_id": overlay["feedback_candidate_context_overlay"]["overlay_id"],
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }

    artifacts = feedback_qa.feedback_artifacts(tmp_path, project_id)

    feedback_qa.assert_feedback_artifacts(artifacts, summary, dict(summary))


def test_quality_feedback_browser_qa_tool_stays_provider_closed() -> None:
    source = (REPO_ROOT / "tools" / "studio_quality_feedback_context_overlay_browser_qa.py").read_text(encoding="utf-8")

    assert "allow_live_llm" not in source
    assert "AFS_ALLOW_REMOTE" not in source
    assert '"provider_calls_started": False' in source
    assert '"writes_long_term_memory": False' in source
    assert '"writes_company_kb": False' in source
