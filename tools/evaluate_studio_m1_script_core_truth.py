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
COMMAND_SCHEMA = "afs.core_asset_command.v0.1"


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only evaluator for Studio M1 ScriptRevision/Core Asset truth.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    report = evaluate(args.root.resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["verdict"] == "PASS" else 1


def evaluate(root: Path) -> dict[str, Any]:
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("afs.runtime.request").setLevel(logging.ERROR)
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
        "schema_version": "afs.studio_m1_script_core_truth.evaluator.v0.1",
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
            "not_provider_script_understanding",
            "not_media_generation",
            "not_complete_automated_production_chain",
            "not_creative_quality_assurance",
            "not_owner_acceptance",
            "not_business_validation",
        ],
    }


def _check_static_contract(root: Path, findings: list[dict[str, str]]) -> None:
    files = {
        "runtime": root / "apps/api/runtime_script_core_truth.py",
        "service": root / "apps/api/runtime_service.py",
        "lifecycle": root / "apps/studio/src/agent-chat-lifecycle.js",
        "panel": root / "apps/studio/src/agent-chat-panel.js",
        "projection": root / "apps/studio/src/script-core-truth-projection.js",
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
            "ScriptRevisionCreateRequest",
            "StructuredAnalysisCandidateRequest",
            "CoreAssetCommandRequest",
            "ANALYSIS_CANDIDATE_SCHEMA_VERSION",
            "CORE_ASSET_COMMAND_SCHEMA_VERSION",
            "source_digest_mismatch",
            "schema_version_mismatch",
            "project_identity_mismatch",
            "evidence_span_mismatch",
            '"auto_props": 0',
            '"style_assets": 0',
            '"action_event_assets": 0',
        ],
        "service": ["register_runtime_script_core_truth_routes(app, store, auth)"],
        "lifecycle": [
            "create_script_revision",
            "refresh_script_truth",
            "create_manual_prop",
            "merge_alias",
            "retire_asset",
            "restore_asset",
            "executePendingAgentCommandWithRuntime",
            "undoAgentReceiptWithRuntime",
            "storyboard_read_only",
        ],
        "projection": ["applyScriptCoreTruthProjection", "runtime_script_core_truth", "script_core_truth"],
        "client": [
            "createScriptRevision",
            "loadScriptTruth",
            "submitStructuredAnalysisCandidate",
            "previewCoreAssetCommand",
            "confirmCoreAssetCommand",
            "undoCoreAssetCommand",
        ],
        "main": ["refreshScriptCoreTruth"],
        "shell": ["runtime: options.getRuntime?.()"],
    }
    for key, markers in required.items():
        for marker in markers:
            if marker not in text.get(key, ""):
                findings.append({"severity": "P0", "scope": key, "issue": f"missing marker: {marker}"})

    combined_production = "\n".join(text.values())
    for marker in ("KNOWN_", "_HINTS", "FALLBACK_SCENES", "巷口", "雨巷", "老宅", "4x15", "4×15"):
        if marker in combined_production:
            findings.append({"severity": "P1", "scope": "pollution", "issue": f"forbidden production marker present: {marker}"})
    if "storyboard_write: true" in text["lifecycle"]:
        findings.append({"severity": "P0", "scope": "storyboard", "issue": "Agent command can write storyboard truth"})


def _api_probe(root: Path, findings: list[dict[str, str]]) -> dict[str, Any]:
    sys.path.insert(0, str(root))
    try:
        from apps.api.runtime_service import create_runtime_app
    except Exception as exc:  # pragma: no cover - reported as evaluator finding
        findings.append({"severity": "P0", "scope": "api", "issue": f"import failed: {exc}"})
        return {}

    with tempfile.TemporaryDirectory(prefix="afs-script-core-eval-") as temp_dir:
        client = TestClient(create_runtime_app(runtime_root=Path(temp_dir)))
        project_id = "script-core-eval"
        created = client.post("/projects", json={"project_id": project_id, "goal": "Script core eval"})
        if created.status_code != 200:
            findings.append({"severity": "P0", "scope": "api", "issue": f"project create failed: {created.status_code}"})
            return {}
        text = "Eva finds the key in the Library. Mo watches the street."
        revision = _create_revision(client, project_id, text, findings)
        if not revision:
            return {}
        failed = client.post(
            f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates",
            json={
                "project_id": project_id,
                "revision_id": revision["revision_id"],
                "source_digest": "0" * 64,
                "schema_version": ANALYSIS_SCHEMA,
                "named_characters": [],
                "main_scenes": [],
                "provider_dispatch_count": 0,
                "remote_dispatch_count": 0,
            },
        )
        if failed.status_code != 409:
            findings.append({"severity": "P0", "scope": "api", "issue": "digest mismatch did not fail closed"})
        accepted = client.post(
            f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates",
            json=_candidate(project_id, revision, text),
        )
        if accepted.status_code != 200:
            findings.append({"severity": "P0", "scope": "api", "issue": f"candidate submit failed: {accepted.status_code} {accepted.text}"})
            return {}
        projection = accepted.json()["projection"]
        if projection["asset_counts"]["auto_props"] != 0 or projection["asset_counts"]["style_assets"] != 0:
            findings.append({"severity": "P0", "scope": "api", "issue": "non-core fields leaked into assets"})
        character = next((item for item in projection["assets"] if item["asset_type"] == "character"), None)
        if not character:
            findings.append({"severity": "P0", "scope": "api", "issue": "character asset was not projected"})
            return projection
        command = _command(project_id, revision, "merge_alias", target_asset_id=character["asset_id"], patch={"alias": "E"})
        preview = client.post(f"/projects/{project_id}/core-assets/commands/preview", json=command)
        confirmed = client.post(f"/projects/{project_id}/core-assets/commands/confirm", json=command)
        if preview.status_code != 200 or confirmed.status_code != 200:
            findings.append({"severity": "P0", "scope": "api", "issue": "core asset preview/confirm failed"})
            return projection
        undo = client.post(
            f"/projects/{project_id}/core-assets/commands/undo",
            json={
                "project_id": project_id,
                "receipt_id": confirmed.json()["receipt"]["receipt_id"],
                "revision_id": revision["revision_id"],
                "source_digest": revision["source_digest"],
                "schema_version": COMMAND_SCHEMA,
            },
        )
        if undo.status_code != 200:
            findings.append({"severity": "P0", "scope": "api", "issue": "core asset undo failed"})
        final = client.get(f"/projects/{project_id}/script-truth").json()
        return {
            "analysis_state": final["projection"]["analysis_state"],
            "asset_counts": final["projection"]["asset_counts"],
            "revision_history_count": len(final["projection"]["revision_history"]),
            "provider_dispatch_count": final.get("provider_dispatch_count", 0),
            "remote_dispatch_count": final.get("remote_dispatch_count", 0),
            "digest_mismatch_status": failed.status_code,
            "core_asset_receipt_status": confirmed.json().get("receipt", {}).get("status", ""),
            "undo_status": undo.status_code,
        }


def _agent_chat_probe(root: Path, findings: list[dict[str, str]]) -> dict[str, Any]:
    script = r'''
import {
  agentChatContextKey,
  agentChatContextSnapshot,
  createAgentChatContextStore,
  executePendingAgentCommandWithRuntime,
  submitAgentChatMessage,
} from "./apps/studio/src/agent-chat-lifecycle.js";
const projection = {
  schema_version: "afs.script_core_truth.v0.1",
  project_id: "p1",
  current_revision_id: "scrrev_eval",
  current_revision: { revision_id: "scrrev_eval", source_kind: "script", source_digest: "b".repeat(64), source_length: 3, analysis_state: "analysis_required" },
  revision_history: [],
  assets: [],
  asset_counts: { characters: 0, main_scenes: 0, manual_props: 0, auto_props: 0, style_assets: 0, action_event_assets: 0 },
  analysis_state: "analysis_required",
};
const state = {
  meta: { projectId: "p1", projectName: "Eval", canvasName: "Canvas", seq: 1 },
  viewport: { x: 0, y: 0, scale: 1 },
  nodes: {},
  edges: {},
  groups: {},
  order: [],
  assets: [],
  production: {},
  selection: { nodeIds: [], edgeId: null },
  ui: {},
};
const store = { get: () => state, set: (mutator) => mutator(state) };
const runtime = {
  createScriptRevision: async () => ({ project_id: "p1", revision: projection.current_revision, projection, analysis_state: "analysis_required" }),
};
const context = agentChatContextSnapshot({ project: { project_id: "p1", name: "Eval" }, studioState: state, section: "canvas" });
const session = createAgentChatContextStore().get(agentChatContextKey(context));
const preview = submitAgentChatMessage(session, "/script-revision Eva enters.", context);
const receipt = await executePendingAgentCommandWithRuntime(session, store, runtime);
const storyboard = agentChatContextSnapshot({ project: { project_id: "p1", name: "Eval" }, studioState: state, section: "storyboard" });
const blocked = submitAgentChatMessage(session, "/manual-prop Blocked", storyboard);
process.stdout.write(JSON.stringify({
  previewStatus: preview.status,
  commandType: preview.command.command_type,
  receiptStatus: receipt.status,
  undoAvailable: receipt.undo_available,
  revisionNodeCount: state.order.filter((id) => id.startsWith("script_truth_revision_")).length,
  analysisState: state.production.script_core_truth_projection.analysis_state,
  storyboardBlocked: blocked.status,
  providerDispatchCount: receipt.provider_dispatch_count,
  remoteDispatchCount: receipt.remote_dispatch_count,
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
    except (subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        findings.append({"severity": "P0", "scope": "agent_chat", "issue": f"runtime lifecycle probe failed: {exc}"})
        return {}
    expected = {
        "previewStatus": "preview",
        "commandType": "create_script_revision",
        "receiptStatus": "executed",
        "undoAvailable": False,
        "revisionNodeCount": 1,
        "analysisState": "analysis_required",
        "storyboardBlocked": "blocked",
        "providerDispatchCount": 0,
        "remoteDispatchCount": 0,
    }
    for key, value in expected.items():
        if probe.get(key) != value:
            findings.append({"severity": "P0", "scope": "agent_chat", "issue": f"probe mismatch: {key}"})
    return probe


def _create_revision(client: TestClient, project_id: str, text: str, findings: list[dict[str, str]]) -> dict[str, Any]:
    response = client.post(f"/projects/{project_id}/script-revisions", json={"source_kind": "script", "source_text": text})
    if response.status_code != 200:
        findings.append({"severity": "P0", "scope": "api", "issue": f"revision create failed: {response.status_code} {response.text}"})
        return {}
    payload = response.json()
    if payload["analysis_state"] != "analysis_required":
        findings.append({"severity": "P0", "scope": "api", "issue": "revision without candidate was not analysis_required"})
    return payload["revision"]


def _candidate(project_id: str, revision: dict[str, Any], text: str) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "revision_id": revision["revision_id"],
        "source_digest": revision["source_digest"],
        "schema_version": ANALYSIS_SCHEMA,
        "named_characters": [
            {"display_name": "Eva", "aliases": [], "pronoun_links": [], "evidence_spans": [_span(text, "Eva")], "confidence": 0.94, "status": "candidate"},
            {"display_name": "Mo", "aliases": [], "pronoun_links": [], "evidence_spans": [_span(text, "Mo")], "confidence": 0.73, "status": "candidate"},
        ],
        "main_scenes": [
            {"name": "Library", "evidence_spans": [_span(text, "Library")], "confidence": 0.9, "status": "candidate"},
        ],
        "style": "observational",
        "genre": "short drama",
        "tone": "contained",
        "actions": ["finds the key"],
        "events": ["watch begins"],
        "beats": [{"summary": "discovery"}],
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }


def _span(text: str, quote: str) -> dict[str, Any]:
    start = text.index(quote)
    return {"start": start, "end": start + len(quote), "quote": quote}


def _command(
    project_id: str,
    revision: dict[str, Any],
    command_type: str,
    *,
    target_asset_id: str,
    patch: dict[str, Any],
) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "revision_id": revision["revision_id"],
        "source_digest": revision["source_digest"],
        "schema_version": COMMAND_SCHEMA,
        "command_type": command_type,
        "target_asset_id": target_asset_id,
        "patch": patch,
        "provider_dispatch_count": 0,
        "remote_dispatch_count": 0,
    }


if __name__ == "__main__":
    raise SystemExit(main())
