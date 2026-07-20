from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_SCHEMA = "afs.structured_analysis_candidate.v0.1"


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only evaluator for Studio M2 Dynamic Production Plan truth.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    report = evaluate(args.root.resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["verdict"] == "PASS" else 1


def evaluate(root: Path) -> dict[str, Any]:
    logging.disable(logging.CRITICAL)
    for logger_name in ("httpx", "afs.runtime.request", "afs.runtime.audit"):
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.CRITICAL)
        logger.propagate = False
    findings: list[dict[str, str]] = []
    evidence: dict[str, Any] = {}
    _check_static_contract(root, findings)
    evidence["api_probe"] = _api_probe(root, findings)
    evidence["agent_chat_probe"] = _agent_chat_probe(root, findings)
    provider_dispatch_count = int(evidence["api_probe"].get("provider_dispatch_count", 0)) + int(
        evidence["agent_chat_probe"].get("providerDispatchCount", 0)
    )
    if provider_dispatch_count != 0:
        findings.append({"severity": "P0", "scope": "provider_gate", "issue": "provider dispatch count was non-zero"})
    p0 = sum(1 for item in findings if item["severity"] == "P0")
    p1 = sum(1 for item in findings if item["severity"] == "P1")
    return {
        "schema_version": "afs.studio_m2_dynamic_plan.evaluator.v0.1",
        "verdict": "PASS" if p0 == 0 and p1 == 0 else "FAIL",
        "p0": p0,
        "p1": p1,
        "P0": p0,
        "P1": p1,
        "findings": findings,
        "provider_dispatch_count": provider_dispatch_count,
        "remote_dispatch_count": int(evidence["api_probe"].get("remote_dispatch_count", 0))
        + int(evidence["agent_chat_probe"].get("remoteDispatchCount", 0)),
        "evidence": evidence,
        "non_claims": [
            "not_provider_story_planning",
            "not_media_generation",
            "not_complete_automated_production_chain",
            "not_creative_quality_assurance",
            "not_owner_acceptance",
            "not_business_validation",
        ],
    }


def _check_static_contract(root: Path, findings: list[dict[str, str]]) -> None:
    files = {
        "runtime": root / "apps/api/runtime_dynamic_production_plan.py",
        "service": root / "apps/api/runtime_service.py",
        "lifecycle": root / "apps/studio/src/agent-chat-lifecycle.js",
        "panel": root / "apps/studio/src/agent-chat-panel.js",
        "projection": root / "apps/studio/src/production-plan-projection.js",
        "client": root / "apps/studio/src/runtime-client.js",
        "main": root / "apps/studio/src/main.js",
        "shell": root / "apps/studio/src/product-shell.js",
    }
    text: dict[str, str] = {}
    for key, path in files.items():
        if not path.exists():
            findings.append({"severity": "P0", "scope": key, "issue": f"missing file: {path.relative_to(root)}"})
            text[key] = ""
        else:
            text[key] = path.read_text(encoding="utf-8")

    required = {
        "runtime": [
            "StoryPlanCandidateRequest",
            "ProviderCapabilityContract",
            "ProductionPlanCommandRequest",
            "PRODUCTION_PLAN_SCHEMA_VERSION",
            "STORY_PLAN_CANDIDATE_SCHEMA_VERSION",
            "PROVIDER_CAPABILITY_SCHEMA_VERSION",
            "PRODUCTION_PLAN_COMMAND_SCHEMA_VERSION",
            "story_plan_candidate_digest",
            "schema_version_mismatch",
            "candidate_digest_mismatch",
            "script_revision_contract_mismatch",
            "character_reference_mismatch",
            "pending_capability",
            "pending_input",
            "retry_failed",
            "concat_plan",
            '"provider_dispatch_count": 0',
        ],
        "service": ["register_runtime_dynamic_production_plan_routes(app, store, auth)"],
        "lifecycle": [
            "submit_story_plan_candidate",
            "refresh_production_plan",
            "edit_shot_duration",
            "set_shot_strategy",
            "split_shot",
            "merge_shot_next",
            "replan_affected",
            "mark_failed",
            "retry_failed",
            "undoProductionPlanCommand",
            "runtime_dynamic_production_plan_truth",
            "storyboard_read_only",
        ],
        "projection": ["applyProductionPlanProjection", "runtime_dynamic_production_plan", "storyboard_shots", "productionPlanProjection"],
        "client": [
            "loadProductionPlanTruth",
            "submitStoryPlanCandidate",
            "confirmStoryPlanCandidate",
            "previewProductionPlanCommand",
            "confirmProductionPlanCommand",
            "undoProductionPlanCommand",
        ],
        "main": ["refreshProductionPlanTruth", "applyProductionPlanProjection"],
        "shell": ["dynamic_production_plan_projection", "storyboard_shots"],
    }
    for key, markers in required.items():
        for marker in markers:
            if marker not in text.get(key, ""):
                findings.append({"severity": "P0", "scope": key, "issue": f"missing marker: {marker}"})

    combined = "\n".join(text.values())
    for marker in ("KNOWN_", "_HINTS", "FALLBACK_SCENES", "巷口", "雨巷", "老宅", "4x15", "4×15", "fixed 4"):
        if marker in combined:
            findings.append({"severity": "P1", "scope": "pollution", "issue": f"forbidden production marker present: {marker}"})
    if "storyboard_write: true" in text["lifecycle"]:
        findings.append({"severity": "P0", "scope": "storyboard", "issue": "Agent command can write storyboard truth"})


def _api_probe(root: Path, findings: list[dict[str, str]]) -> dict[str, Any]:
    sys.path.insert(0, str(root))
    try:
        from apps.api.runtime_dynamic_production_plan import (
            PRODUCTION_PLAN_COMMAND_SCHEMA_VERSION,
            PROVIDER_CAPABILITY_SCHEMA_VERSION,
            STORY_PLAN_CANDIDATE_SCHEMA_VERSION,
            story_plan_candidate_digest,
        )
        from apps.api.runtime_service import create_runtime_app
    except Exception as exc:  # pragma: no cover - reported as evaluator finding
        findings.append({"severity": "P0", "scope": "api", "issue": f"import failed: {exc}"})
        return {}

    with tempfile.TemporaryDirectory(prefix="afs-dynamic-plan-eval-") as temp_dir:
        client = TestClient(create_runtime_app(runtime_root=Path(temp_dir)))
        project_id = "dynamic-plan-eval"
        created = client.post("/projects", json={"project_id": project_id, "goal": "Dynamic plan eval"})
        if created.status_code != 200:
            findings.append({"severity": "P0", "scope": "api", "issue": f"project create failed: {created.status_code}"})
            return {}
        text = "Mira calibrates the lens in the observatory. Tao opens the signal room as a distant signal arrives."
        revision = _create_revision(client, project_id, text, findings)
        if not revision:
            return {}
        analysis = client.post(
            f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates",
            json=_analysis(project_id, revision, text),
        )
        if analysis.status_code != 200:
            findings.append({"severity": "P0", "scope": "api", "issue": f"analysis candidate failed: {analysis.status_code} {analysis.text}"})
            return {}
        candidate = _candidate(
            project_id,
            revision,
            analysis.json()["projection"],
            capability_schema=PROVIDER_CAPABILITY_SCHEMA_VERSION,
            candidate_schema=STORY_PLAN_CANDIDATE_SCHEMA_VERSION,
            digest_fn=story_plan_candidate_digest,
        )
        bad = {**candidate, "candidate_digest": "f" * 64}
        failed = client.post(f"/projects/{project_id}/story-plan-candidates", json=bad)
        if failed.status_code != 409:
            findings.append({"severity": "P0", "scope": "api", "issue": "candidate digest mismatch did not fail closed"})
        submitted = client.post(f"/projects/{project_id}/story-plan-candidates", json=candidate)
        if submitted.status_code != 200:
            findings.append({"severity": "P0", "scope": "api", "issue": f"candidate submit failed: {submitted.status_code} {submitted.text}"})
            return {}
        confirmed = client.post(
            f"/projects/{project_id}/story-plan-candidates/{candidate['candidate_digest']}/confirm",
            json={
                "project_id": project_id,
                "script_revision_id": revision["revision_id"],
                "source_digest": revision["source_digest"],
                "candidate_digest": candidate["candidate_digest"],
                "schema_version": STORY_PLAN_CANDIDATE_SCHEMA_VERSION,
            },
        )
        if confirmed.status_code != 200:
            findings.append({"severity": "P0", "scope": "api", "issue": f"candidate confirm failed: {confirmed.status_code} {confirmed.text}"})
            return {}
        projection = confirmed.json()["projection"]
        if len(projection["shots"]) != 3 or [shot["duration_seconds"] for shot in projection["shots"]] != [2.5, 6.5, 3.0]:
            findings.append({"severity": "P0", "scope": "api", "issue": "dynamic shot order/duration did not survive projection"})
        if {shot["media_strategy"]["strategy"] for shot in projection["shots"]} != {"t2v", "i2v"}:
            findings.append({"severity": "P0", "scope": "api", "issue": "T2V/I2V strategy set was not preserved"})
        edit = _command(project_id, projection, PRODUCTION_PLAN_COMMAND_SCHEMA_VERSION, "edit_shot_duration", target_shot_id="shot_eval_2", patch={"duration_seconds": 7.25})
        preview = client.post(f"/projects/{project_id}/production-plan-commands/preview", json=edit)
        confirmed_edit = client.post(f"/projects/{project_id}/production-plan-commands/confirm", json=edit)
        if preview.status_code != 200 or confirmed_edit.status_code != 200:
            findings.append({"severity": "P0", "scope": "api", "issue": "production plan preview/confirm failed"})
            return projection
        retry = client.post(
            f"/projects/{project_id}/production-plan-commands/confirm",
            json=_command(project_id, confirmed_edit.json()["projection"], PRODUCTION_PLAN_COMMAND_SCHEMA_VERSION, "retry_failed"),
        )
        if retry.status_code != 200:
            findings.append({"severity": "P0", "scope": "api", "issue": "retry_failed command failed"})
        final = client.get(f"/projects/{project_id}/production-plan-truth").json()
        return {
            "planning_state": final["projection"]["planning_state"],
            "shot_count": len(final["projection"]["shots"]),
            "chunk_count": len(final["projection"]["chunks"]),
            "digest_mismatch_status": failed.status_code,
            "command_preview_status": preview.status_code,
            "command_receipt_status": confirmed_edit.json().get("receipt", {}).get("status", ""),
            "provider_dispatch_count": final.get("provider_dispatch_count", 0),
            "remote_dispatch_count": final.get("remote_dispatch_count", 0),
        }


def _agent_chat_probe(root: Path, findings: list[dict[str, str]]) -> dict[str, Any]:
    script = r'''
import {
  agentChatContextKey,
  agentChatContextSnapshot,
  createAgentChatContextStore,
  executePendingAgentCommandWithRuntime,
  submitAgentChatMessage,
  undoAgentReceiptWithRuntime,
} from "./apps/studio/src/agent-chat-lifecycle.js";
import { applyScriptCoreTruthProjection } from "./apps/studio/src/script-core-truth-projection.js";
const digest = "b".repeat(64);
const planDigest = "d".repeat(64);
const revision = { revision_id: "scrrev_eval", source_kind: "script", source_digest: digest, source_length: 8, analysis_state: "confirmed" };
const scriptProjection = {
  schema_version: "afs.script_core_truth.v0.1",
  project_id: "p1",
  current_revision_id: revision.revision_id,
  current_revision: revision,
  revision_history: [revision],
  assets: [{ asset_id: "char_eval", asset_type: "character", source_mode: "analysis_candidate", status: "confirmed", project_id: "p1", revision_id: revision.revision_id, source_digest: digest, display_name: "Mira", name: "Mira", aliases: [], pronoun_links: [], evidence_spans: [], confidence: 0.9, lineage: {} }],
  asset_counts: { characters: 1, main_scenes: 0, manual_props: 0, auto_props: 0, style_assets: 0, action_event_assets: 0 },
  analysis_state: "confirmed",
};
function projection(nextDigest = planDigest, duration = 2.5) {
  return {
    schema_version: "afs.dynamic_production_plan.v0.1",
    project_id: "p1",
    planning_state: "planned",
    current_plan: { plan_id: nextDigest === planDigest ? "plan_eval" : "plan_eval_v2", plan_digest: nextDigest, parent_plan_id: "", plan_version: 1, script_revision_id: revision.revision_id, source_digest: digest, candidate_digest: "c".repeat(64), provider_dispatch_count: 0, remote_dispatch_count: 0 },
    beats: [{ beat_id: "beat_eval", order: 1, summary: "setup", source_evidence_refs: [{ source_kind: "script_revision", source_id: revision.revision_id, quote: "Mira" }], narrative_purpose: "setup" }],
    shots: [{ shot_id: "shot_eval", beat_id: "beat_eval", order: 1, intent: "dynamic", duration_seconds: duration, character_refs: ["char_eval"], scene_refs: [], continuity_in: "", continuity_out: "", source_evidence_refs: [{ source_kind: "script_revision", source_id: revision.revision_id, quote: "Mira" }], media_strategy: { strategy: "t2v", strategy_reason: "text-only", input_requirements: ["text_prompt_contract"], reference_asset_refs: [], user_constraints: {} }, media_input_state: "ready", status: "planned", chunk_ids: ["chunk_shot_eval_1"], attempt_history: [] }],
    chunks: [{ chunk_id: "chunk_shot_eval_1", shot_id: "shot_eval", shot_order: 1, sequence: 1, target_duration_seconds: duration, continuity_anchor_in: "", continuity_anchor_out: "hold", depends_on: "", state: "ready", remainder_strategy: "", attempt_history: [], selected_artifact_version_ref: "" }],
    concat_plan: { concat_plan_id: "concat_eval", state: "planned_not_executed", shot_order: ["shot_eval"], selected_artifact_version_refs: [{ shot_id: "shot_eval", artifact_version_ref: "artifact_placeholder:shot_eval", state: "planned_placeholder" }], executes_media: false, provider_dispatch_count: 0, remote_dispatch_count: 0 },
    plan_history: [],
    storyboard_mode: "read_only_consumer",
    provider_dispatch_count: 0,
    remote_dispatch_count: 0,
  };
}
const candidate = { project_id: "p1", script_revision_id: revision.revision_id, source_digest: digest, schema_version: "afs.story_plan_candidate.v0.1", candidate_digest: "c".repeat(64), beats: [], shots: [], capability_contract: {}, provider_dispatch_count: 0, remote_dispatch_count: 0 };
const state = { meta: { projectId: "p1", projectName: "Eval", canvasName: "Canvas", seq: 1 }, viewport: { x: 0, y: 0, scale: 1 }, nodes: {}, edges: {}, groups: {}, order: [], assets: [], production: {}, selection: { nodeIds: [], edgeId: null }, ui: {} };
const store = { get: () => state, set: (mutator) => mutator(state) };
applyScriptCoreTruthProjection(state, scriptProjection);
const runtime = {
  submitStoryPlanCandidate: async () => ({ candidate: { candidate_digest: "c".repeat(64) }, projection: projection() }),
  confirmStoryPlanCandidate: async () => ({ receipt: { receipt_id: "r1", command_type: "confirm_story_plan_candidate", status: "executed", summary: "confirmed", script_revision_id: revision.revision_id, source_digest: digest, before_plan_id: "", after_plan_id: "plan_eval", before_plan_digest: "", after_plan_digest: planDigest, undo_available: true }, projection: projection() }),
  previewProductionPlanCommand: async (payload) => ({ command: { status: "preview", command_type: payload.command_type }, projection: projection() }),
  confirmProductionPlanCommand: async (payload) => ({ receipt: { receipt_id: "r2", command_type: payload.command_type, status: "executed", summary: "edited", script_revision_id: revision.revision_id, source_digest: digest, before_plan_id: "plan_eval", after_plan_id: "plan_eval_v2", before_plan_digest: planDigest, after_plan_digest: "e".repeat(64), undo_available: true }, projection: projection("e".repeat(64), payload.patch.duration_seconds) }),
  undoProductionPlanCommand: async () => ({ receipt: { receipt_id: "r3", command_type: "undo", status: "undone", summary: "undo", after_plan_digest: planDigest }, projection: projection() }),
};
const context = agentChatContextSnapshot({ project: { project_id: "p1", name: "Eval" }, studioState: state, section: "canvas" });
const session = createAgentChatContextStore().get(agentChatContextKey(context));
const createPreview = submitAgentChatMessage(session, `/submit-story-plan ${JSON.stringify(candidate)}`, context);
const createReceipt = await executePendingAgentCommandWithRuntime(session, store, runtime);
const shotNodeId = state.order.find((id) => id === "production_plan_shot_shot_eval");
state.selection = { nodeIds: [shotNodeId], edgeId: null };
const shotContext = agentChatContextSnapshot({ project: { project_id: "p1", name: "Eval" }, studioState: state, section: "canvas", selectedNode: state.nodes[shotNodeId] });
const editPreview = submitAgentChatMessage(session, "/edit-shot-duration 3.75", shotContext);
const editReceipt = await executePendingAgentCommandWithRuntime(session, store, runtime);
const undoReceipt = await undoAgentReceiptWithRuntime(session, editReceipt, store, runtime);
const storyboard = agentChatContextSnapshot({ project: { project_id: "p1", name: "Eval" }, studioState: state, section: "storyboard" });
const blocked = submitAgentChatMessage(session, "/edit-shot-duration 4", storyboard);
process.stdout.write(JSON.stringify({
  createStatus: createPreview.status,
  createReceiptDomain: createReceipt.runtime_domain,
  planNodes: state.order.filter((id) => id.startsWith("production_plan_")).length,
  editStatus: editPreview.status,
  editReceiptDigest: editReceipt.plan_digest,
  undoStatus: undoReceipt.status,
  storyboardBlocked: blocked.status,
  providerDispatchCount: createReceipt.provider_dispatch_count + editReceipt.provider_dispatch_count + undoReceipt.provider_dispatch_count,
  remoteDispatchCount: createReceipt.remote_dispatch_count + editReceipt.remote_dispatch_count + undoReceipt.remote_dispatch_count,
}));
'''
    try:
        completed = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        probe = json.loads(completed.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError) as error:
        findings.append({"severity": "P0", "scope": "agent_chat", "issue": f"dynamic plan lifecycle probe failed: {error}"})
        return {}

    expected = {
        "createStatus": "preview",
        "createReceiptDomain": "production_plan",
        "editStatus": "preview",
        "editReceiptDigest": "e" * 64,
        "undoStatus": "undone",
        "storyboardBlocked": "blocked",
        "providerDispatchCount": 0,
        "remoteDispatchCount": 0,
    }
    for key, value in expected.items():
        if probe.get(key) != value:
            findings.append({"severity": "P0", "scope": "agent_chat", "issue": f"dynamic plan lifecycle mismatch: {key}"})
    if int(probe.get("planNodes", 0)) < 4:
        findings.append({"severity": "P0", "scope": "projection", "issue": "production plan projection did not create enough nodes"})
    return probe


def _create_revision(client: TestClient, project_id: str, text: str, findings: list[dict[str, str]]) -> dict[str, Any]:
    created = client.post(
        f"/projects/{project_id}/script-revisions",
        json={"source_kind": "script", "source_text": text, "provenance": {"test": "dynamic_plan_evaluator"}},
    )
    if created.status_code != 200:
        findings.append({"severity": "P0", "scope": "api", "issue": f"revision create failed: {created.status_code} {created.text}"})
        return {}
    return created.json()["revision"]


def _analysis(project_id: str, revision: dict[str, Any], text: str) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "revision_id": revision["revision_id"],
        "source_digest": revision["source_digest"],
        "schema_version": ANALYSIS_SCHEMA,
        "named_characters": [
            {"display_name": "Mira", "aliases": [], "pronoun_links": [], "evidence_spans": [_span(text, "Mira")], "confidence": 0.94, "status": "candidate"},
            {"display_name": "Tao", "aliases": [], "pronoun_links": [], "evidence_spans": [_span(text, "Tao")], "confidence": 0.9, "status": "candidate"},
        ],
        "main_scenes": [
            {"name": "Observatory", "evidence_spans": [_span(text, "observatory")], "confidence": 0.92, "status": "candidate"},
            {"name": "Signal Room", "evidence_spans": [_span(text, "signal room")], "confidence": 0.91, "status": "candidate"},
        ],
        "style": "precise animation",
        "genre": "short drama",
        "tone": "focused",
        "actions": ["calibrates lens"],
        "events": ["signal arrives"],
        "beats": [{"summary": "setup"}],
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }


def _candidate(
    project_id: str,
    revision: dict[str, Any],
    projection: dict[str, Any],
    *,
    capability_schema: str,
    candidate_schema: str,
    digest_fn,
) -> dict[str, Any]:
    characters = [item["asset_id"] for item in projection["assets"] if item["asset_type"] == "character"]
    scenes = [item["asset_id"] for item in projection["assets"] if item["asset_type"] == "main_scene"]
    beats = [
        {"beat_id": "beat_eval_setup", "order": 1, "summary": "setup", "source_evidence_refs": [{"source_kind": "script_revision", "source_id": revision["revision_id"], "quote": "Mira calibrates"}], "narrative_purpose": "setup"},
        {"beat_id": "beat_eval_response", "order": 2, "summary": "response", "source_evidence_refs": [{"source_kind": "script_revision", "source_id": revision["revision_id"], "quote": "signal room"}], "narrative_purpose": "response"},
    ]
    payload = {
        "project_id": project_id,
        "script_revision_id": revision["revision_id"],
        "source_digest": revision["source_digest"],
        "schema_version": candidate_schema,
        "candidate_digest": "",
        "beats": beats,
        "shots": [
            _shot("shot_eval_1", beats[0]["beat_id"], 1, 2.5, characters[:1], scenes[:1], _t2v(), revision),
            _shot("shot_eval_2", beats[0]["beat_id"], 2, 6.5, characters[:1], scenes[:1], _i2v(project_id, revision, characters[0]), revision),
            _shot("shot_eval_3", beats[1]["beat_id"], 3, 3.0, characters[:2], scenes[-1:], _t2v(), revision),
        ],
        "capability_contract": {
            "schema_version": capability_schema,
            "provider_profile_id": "offline-contract-capability",
            "supports_t2v": True,
            "supports_i2v": True,
            "supported_clip_durations": [2.5, 3.0, 4.0],
            "max_duration_seconds": 4.0,
            "supports_start_frame": True,
            "supports_end_frame": True,
            "aspect_ratios": ["9:16"],
            "fps_values": [24],
        },
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }
    payload["candidate_digest"] = digest_fn(payload)
    return payload


def _shot(
    shot_id: str,
    beat_id: str,
    order: int,
    duration: float,
    characters: list[str],
    scenes: list[str],
    strategy: dict[str, Any],
    revision: dict[str, Any],
) -> dict[str, Any]:
    return {
        "shot_id": shot_id,
        "beat_id": beat_id,
        "order": order,
        "intent": f"Dynamic eval shot {order}",
        "duration_seconds": duration,
        "character_refs": characters,
        "scene_refs": scenes,
        "continuity_in": "in",
        "continuity_out": "out",
        "source_evidence_refs": [{"source_kind": "script_revision", "source_id": revision["revision_id"], "quote": "distant signal arrives"}],
        "media_strategy": strategy,
    }


def _t2v() -> dict[str, Any]:
    return {
        "strategy": "t2v",
        "strategy_reason": "explicit text-only shot intent",
        "input_requirements": ["text_prompt_contract"],
        "reference_asset_refs": [],
        "user_constraints": {"explicit_reference_available": False},
    }


def _i2v(project_id: str, revision: dict[str, Any], asset_id: str) -> dict[str, Any]:
    return {
        "strategy": "i2v",
        "strategy_reason": "locked keyframe lineage is available",
        "input_requirements": ["reference_artifact_or_locked_keyframe"],
        "reference_asset_refs": [
            {
                "ref_id": "ref_eval_keyframe",
                "source_kind": "locked_keyframe",
                "asset_id": asset_id,
                "artifact_id": "artifact-eval-keyframe",
                "lineage": {
                    "project_id": project_id,
                    "script_revision_id": revision["revision_id"],
                    "source_digest": revision["source_digest"],
                    "asset_id": asset_id,
                    "artifact_id": "artifact-eval-keyframe",
                    "locked_keyframe_id": "locked-keyframe-eval",
                },
            }
        ],
        "user_constraints": {"explicit_reference_available": True},
    }


def _command(project_id: str, projection: dict[str, Any], schema: str, command_type: str, **overrides) -> dict[str, Any]:
    plan = projection["current_plan"]
    return {
        "project_id": project_id,
        "script_revision_id": plan["script_revision_id"],
        "source_digest": plan["source_digest"],
        "plan_id": plan["plan_id"],
        "plan_digest": plan["plan_digest"],
        "schema_version": schema,
        "command_type": command_type,
        "target_shot_id": overrides.get("target_shot_id"),
        "target_chunk_id": overrides.get("target_chunk_id"),
        "patch": overrides.get("patch", {}),
        "reason": "evaluator",
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }


def _span(text: str, quote: str) -> dict[str, Any]:
    start = text.index(quote)
    return {"start": start, "end": start + len(quote), "quote": quote}


if __name__ == "__main__":
    raise SystemExit(main())
