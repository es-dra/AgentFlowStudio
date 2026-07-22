from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = Path("tests/fixtures/m3_zero_cost_creative_chain_cases.json")
ZERO_PROVIDER_GATES = ("llm", "image", "video", "audio", "asr", "vision", "external_download")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate M3.0 zero-cost creative-chain knowledge/context contracts.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--corpus", type=Path, default=CORPUS_PATH)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()
    root = args.root.resolve()
    report = evaluate(root, args.corpus)
    report_path = args.report or Path(f"/tmp/afs-m3-zero-cost-evaluation-{report['evaluation_trace_id']}.json")
    report_path = report_path.resolve()
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    output = {
        "verdict": report["verdict"],
        "P0": report["P0"],
        "P1": report["P1"],
        "provider_dispatch_count": report["provider_dispatch_count"],
        "remote_dispatch_count": report["remote_dispatch_count"],
        "case_count": report["case_count"],
        "adversarial_variant_count": report["adversarial_variant_count"],
        "report": str(report_path),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["verdict"] == "PASS" else 1


def evaluate(root: Path, corpus_path: Path) -> dict[str, Any]:
    logging.disable(logging.CRITICAL)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    findings: list[dict[str, Any]] = []
    evidence: dict[str, Any] = {}
    _check_static_contract(root, findings)
    corpus = _load_corpus(root, corpus_path, findings)
    if corpus:
        evidence["corpus"] = _evaluate_corpus(corpus, findings)
    evidence["api_probe"] = _api_probe(root, findings)
    evidence["agent_chat_probe"] = _agent_chat_probe(root, findings)
    provider_dispatch_count = _provider_count(evidence)
    if provider_dispatch_count != 0:
        findings.append(_finding("P0", "provider_gate", "provider dispatch count is non-zero"))
    p0 = sum(1 for item in findings if item["severity"] == "P0")
    p1 = sum(1 for item in findings if item["severity"] == "P1")
    return {
        "artifact_type": "afs_m3_zero_cost_independent_evaluator_report",
        "schema_version": "afs.m3_zero_cost_independent_evaluator.v0.1",
        "verdict": "PASS" if p0 == 0 and p1 == 0 else "FAIL",
        "P0": p0,
        "P1": p1,
        "P2": sum(1 for item in findings if item["severity"] == "P2"),
        "P3": sum(1 for item in findings if item["severity"] == "P3"),
        "findings": findings,
        "provider_dispatch_count": provider_dispatch_count,
        "remote_dispatch_count": _remote_count(evidence),
        "case_count": int((evidence.get("corpus") or {}).get("case_count") or 0),
        "adversarial_variant_count": int((evidence.get("corpus") or {}).get("adversarial_variant_count") or 0),
        "evidence": evidence,
        "evaluation_trace_id": _stable_trace(evidence),
        "non_claims": [
            "not_provider_story_planning",
            "not_provider_script_understanding",
            "not_media_generation",
            "not_human_creative_quality_assurance",
            "not_owner_acceptance",
            "not_business_validation",
        ],
    }


def _check_static_contract(root: Path, findings: list[dict[str, Any]]) -> None:
    files = {
        "runtime_m3": root / "apps/api/runtime_m3_zero_cost_kernel.py",
        "runtime_service": root / "apps/api/runtime_service.py",
        "runtime_client": root / "apps/studio/src/runtime-client.js",
        "agent_chat": root / "apps/studio/src/agent-chat-lifecycle.js",
        "script_truth": root / "apps/api/runtime_script_core_truth.py",
        "plan_truth": root / "apps/api/runtime_dynamic_production_plan.py",
    }
    text: dict[str, str] = {}
    for key, path in files.items():
        if not path.exists():
            findings.append(_finding("P0", key, f"missing file {path.relative_to(root)}"))
            text[key] = ""
            continue
        text[key] = path.read_text(encoding="utf-8")

    required_markers = {
        "runtime_m3": [
            "KNOWLEDGE_ENTRY_SCHEMA_VERSION",
            "KNOWLEDGE_PACK_SCHEMA_VERSION",
            "ContextPack",
            "FeedbackCandidate",
            "PromotionDecision",
            "QUALITY_RUBRIC_SCHEMA_VERSION",
            "EvaluationReport",
            "source",
            "provenance",
            "rights",
            "rollback",
            "feedback_is_not_memory",
            "draft_is_not_truth",
            "provider_dispatch_count: int = Field(default=0, ge=0, le=0)",
            "retrieve_relevant_knowledge_refs",
            "evaluate_zero_cost_creative_chain_corpus",
        ],
        "runtime_service": ["register_runtime_m3_zero_cost_kernel_routes(app, store, auth)"],
        "runtime_client": [
            "previewM3ContextPack",
            "confirmM3ContextPack",
            "undoM3ContextPack",
            "recordM3FeedbackCandidate",
            "recordM3PromotionDecision",
            "recordM3EvaluationReport",
        ],
        "agent_chat": [
            "build_m3_context_pack",
            "m3_zero_cost_context_pack",
            "feedback_not_memory_contract",
            "knowledge_pack_scoped_retrieval",
            "runtimeM3ContextPackPayload",
            "undoM3ContextPack",
        ],
        "plan_truth": ["production_plan_projection_for_project"],
    }
    for key, markers in required_markers.items():
        for marker in markers:
            if marker not in text.get(key, ""):
                findings.append(_finding("P0", key, f"missing marker {marker}"))

    production_text = "\n".join(text.values())
    forbidden_markers = (
        "KNOWN_",
        "_HINTS",
        "FALLBACK_SCENES",
        "structuredShotFromSegment",
        "4x15",
        "4×15",
        "fixed 4",
        "provider_dispatch_count: 1",
        "remote_dispatch_count: 1",
    )
    for marker in forbidden_markers:
        for match in re.finditer(re.escape(marker), production_text):
            if _allowed_runtime_llm_dispatch_marker(production_text, match.start()):
                continue
            findings.append(_finding("P1", "production_pollution", f"forbidden production marker present: {marker}"))


def _allowed_runtime_llm_dispatch_marker(production_text: str, marker_index: int) -> bool:
    function_start = production_text.rfind("function runtimeConversationAnswer", 0, marker_index)
    if function_start < 0:
        return False
    function_end = production_text.find("\n}\n", marker_index)
    if function_end < 0:
        return False
    function_body = production_text[function_start:function_end]
    return 'source: "runtime_llm"' in function_body and "graph_mutation" in function_body


def _load_corpus(root: Path, corpus_path: Path, findings: list[dict[str, Any]]) -> dict[str, Any]:
    path = corpus_path if corpus_path.is_absolute() else root / corpus_path
    if not path.exists():
        findings.append(_finding("P0", "corpus", f"missing corpus {path}"))
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        findings.append(_finding("P0", "corpus", f"invalid JSON: {exc}"))
        return {}


def _evaluate_corpus(corpus: dict[str, Any], findings: list[dict[str, Any]]) -> dict[str, Any]:
    from apps.api.runtime_m3_zero_cost_kernel import evaluate_zero_cost_creative_chain_corpus

    report = evaluate_zero_cost_creative_chain_corpus(corpus)
    findings.extend(report.get("findings") or [])
    cases = corpus.get("cases") or []
    categories = {str(case.get("category") or "") for case in cases}
    expected_fragments = ("60-90", "45-75", "2-3", "30-60", "90-180")
    for fragment in expected_fragments:
        if not any(fragment in category for category in categories):
            findings.append(_finding("P1", "corpus", f"missing required duration/category family {fragment}"))
    if _contains_fixed_template(cases):
        findings.append(_finding("P0", "corpus", "fixed shot count/duration template detected"))
    return report


def _api_probe(root: Path, findings: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        from apps.api.runtime_m3_zero_cost_kernel import (
            EVALUATION_REPORT_SCHEMA_VERSION,
            FEEDBACK_CANDIDATE_SCHEMA_VERSION,
            M3_CONTEXT_COMMAND_SCHEMA_VERSION,
            PROMOTION_DECISION_SCHEMA_VERSION,
        )
        from apps.api.runtime_script_core_truth import ANALYSIS_CANDIDATE_SCHEMA_VERSION
        from apps.api.runtime_service import create_runtime_app
    except Exception as exc:  # pragma: no cover - reported as evaluator finding
        findings.append(_finding("P0", "api_probe", f"import failed: {exc}"))
        return {}

    with tempfile.TemporaryDirectory(prefix="afs-m3-evaluator-") as tmp:
        client = TestClient(create_runtime_app(runtime_root=Path(tmp)))
        project_id = "m3-evaluator-project"
        created = client.post("/projects", json={"project_id": project_id, "goal": "M3 evaluator probe"})
        if created.status_code != 200:
            findings.append(_finding("P0", "api_probe", f"project create failed {created.status_code}"))
            return {}
        text = "Nia waits in the night workshop while Oren studies the locked drawer."
        revision = client.post(
            f"/projects/{project_id}/script-revisions",
            json={"source_kind": "script", "source_text": text, "provenance": {"probe": "m3_evaluator"}},
        )
        if revision.status_code != 200:
            findings.append(_finding("P0", "api_probe", f"script revision failed {revision.status_code} {revision.text}"))
            return {}
        rev = revision.json()["revision"]
        analysis = client.post(
            f"/projects/{project_id}/script-revisions/{rev['revision_id']}/analysis-candidates",
            json={
                "project_id": project_id,
                "revision_id": rev["revision_id"],
                "source_digest": rev["source_digest"],
                "schema_version": ANALYSIS_CANDIDATE_SCHEMA_VERSION,
                "named_characters": [
                    {
                        "display_name": "Nia",
                        "aliases": [],
                        "pronoun_links": [],
                        "evidence_spans": [_span(text, "Nia")],
                        "confidence": 0.93,
                        "status": "candidate",
                    }
                ],
                "main_scenes": [
                    {
                        "name": "Night Workshop",
                        "evidence_spans": [_span(text, "night workshop")],
                        "confidence": 0.91,
                        "status": "candidate",
                    }
                ],
                "style": "contained",
                "genre": "short drama",
                "tone": "tense",
                "actions": ["Oren studies a drawer"],
                "events": ["Nia waits"],
                "beats": [{"summary": "withheld object creates pressure"}],
                "provider_dispatch_count": 0,
                "remote_dispatch_count": 0,
            },
        )
        if analysis.status_code != 200:
            findings.append(_finding("P0", "api_probe", f"analysis failed {analysis.status_code} {analysis.text}"))
            return {}
        payload = {
            "project_id": project_id,
            "script_revision_id": rev["revision_id"],
            "source_digest": rev["source_digest"],
            "schema_version": M3_CONTEXT_COMMAND_SCHEMA_VERSION,
            "instruction": "Build a zero-cost context pack for professional script and shot audit.",
            "selected_node_id": "script_truth_revision_node",
            "selected_node_type": "script",
            "requested_domains": ["story_plan", "asset_bible", "context", "safety", "evaluation"],
            "constraints": {"draft_is_not_truth": True, "provider_disabled": True},
            "preferences": {"pace": "restrained"},
            "upstream_refs": [rev["revision_id"]],
            "downstream_refs": ["story_plan_candidate", "asset_bible_candidate"],
            "exclusions": ["full_chat_history", "private_user_data", "prompt_injection"],
            "token_budget": 760,
            "provider_gates": {name: False for name in ZERO_PROVIDER_GATES},
            "tool_gates": {"model_call": False, "external_download": False, "media_generation": False},
            "trace_id": "trace_m3_evaluator_context",
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        }
        bad_digest = client.post(
            f"/projects/{project_id}/m3-zero-cost/context-packs/preview",
            json={**payload, "source_digest": "0" * 64},
        )
        if bad_digest.status_code != 409:
            findings.append(_finding("P0", "api_probe", "source digest mismatch did not fail closed"))
        preview = client.post(f"/projects/{project_id}/m3-zero-cost/context-packs/preview", json=payload)
        confirm = client.post(f"/projects/{project_id}/m3-zero-cost/context-packs/confirm", json=payload)
        if preview.status_code != 200 or confirm.status_code != 200:
            findings.append(_finding("P0", "api_probe", f"context pack preview/confirm failed {preview.status_code}/{confirm.status_code}"))
            return {}
        context_pack = confirm.json()["context_pack"]
        pack = client.get(f"/projects/{project_id}/m3-zero-cost/knowledge-pack").json()["knowledge_pack"]
        if len(context_pack["relevant_knowledge_refs"]) >= pack["entry_count"]:
            findings.append(_finding("P1", "api_probe", "context pack injected entire knowledge pack"))
        if not all(value is False for value in context_pack["provider_gates"].values()):
            findings.append(_finding("P0", "api_probe", "provider gates opened in context pack"))
        feedback = client.post(
            f"/projects/{project_id}/m3-zero-cost/feedback-candidates",
            json={
                "project_id": project_id,
                "schema_version": FEEDBACK_CANDIDATE_SCHEMA_VERSION,
                "source_kind": "user_edit",
                "output_ref": f"script_revision:{rev['revision_id']}",
                "output_digest": rev["source_digest"],
                "reason": "User kept subtext and removed exposition.",
                "privacy_scope": "private_project",
                "rights": {"allow_project_reuse": True, "allow_global_reuse": False},
                "provider_dispatch_count": 0,
                "remote_dispatch_count": 0,
            },
        )
        if feedback.status_code != 200:
            findings.append(_finding("P0", "api_probe", f"feedback candidate failed {feedback.status_code}"))
            return context_pack
        feedback_id = feedback.json()["feedback_candidate"]["feedback_candidate_id"]
        blocked_global = client.post(
            f"/projects/{project_id}/m3-zero-cost/promotion-decisions",
            json={
                "project_id": project_id,
                "schema_version": PROMOTION_DECISION_SCHEMA_VERSION,
                "feedback_candidate_id": feedback_id,
                "target_scope": "global",
                "decision": "promoted",
                "reviewer": "m3-evaluator",
                "provider_dispatch_count": 0,
                "remote_dispatch_count": 0,
            },
        )
        if blocked_global.status_code != 422:
            findings.append(_finding("P0", "api_probe", "global promotion bypassed privacy/rights review"))
        for role in (
            "story_editor",
            "director_cinematographer_editor",
            "asset_production_continuity",
            "agent_context_safety_product",
        ):
            report = client.post(
                f"/projects/{project_id}/m3-zero-cost/evaluation-reports",
                json={
                    "project_id": project_id,
                    "schema_version": EVALUATION_REPORT_SCHEMA_VERSION,
                    "role": role,
                    "target_ref": "m3-case:evaluator-probe",
                    "target_digest": rev["source_digest"],
                    "independence": {"separate_pass": True, "implementation_author": False},
                    "rubric_refs": ["m3_zero_cost_professional_kernel_rubric"],
                    "dimensions": [{"name": "provider_gate", "score": 1, "evidence": ["Provider gates false"]}],
                    "critical_failures": [],
                    "provider_dispatch_count": 0,
                    "remote_dispatch_count": 0,
                },
            )
            if report.status_code != 200:
                findings.append(_finding("P0", "api_probe", f"evaluation role report failed: {role}"))
        projection = client.get(f"/projects/{project_id}/m3-zero-cost/audit-truth").json()["projection"]
        return {
            "context_pack_id": context_pack["context_pack_id"],
            "knowledge_ref_count": len(context_pack["relevant_knowledge_refs"]),
            "knowledge_pack_entry_count": pack["entry_count"],
            "feedback_memory_status": feedback.json()["feedback_candidate"]["memory_status"],
            "blocked_global_promotion_status": blocked_global.status_code,
            "evaluator_roles_covered": projection["evaluator_roles_covered"],
            "provider_dispatch_count": projection["provider_dispatch_count"],
            "remote_dispatch_count": projection["remote_dispatch_count"],
        }


def _agent_chat_probe(root: Path, findings: list[dict[str, Any]]) -> dict[str, Any]:
    script = r"""
import {
  agentChatContextKey,
  agentChatContextSnapshot,
  createAgentChatContextStore,
  executePendingAgentCommandWithRuntime,
  submitAgentChatMessage,
  undoAgentReceiptWithRuntime,
} from "./apps/studio/src/agent-chat-lifecycle.js";

const digest = "d".repeat(64);
const revision = {
  revision_id: "scrrev_m3_probe",
  source_kind: "script",
  source_digest: digest,
  source_length: 84,
  analysis_state: "confirmed",
};
const state = {
  meta: { projectId: "m3-agent-chat", projectName: "M3", canvasName: "Canvas", seq: 9 },
  viewport: { x: 0, y: 0, scale: 1 },
  nodes: {
    script_node: {
      id: "script_node",
      type: "script",
      title: "剧本",
      content: "Nia waits in the night workshop while Oren studies the locked drawer.",
      status: "ready",
    },
  },
  edges: {},
  groups: {},
  assets: [],
  order: ["script_node"],
  selection: { nodeIds: ["script_node"], edgeId: null },
  ui: {},
  production: {
    script_core_truth_projection: {
      current_revision_id: revision.revision_id,
      source_digest: digest,
      analysis_state: "confirmed",
      current_revision: revision,
      provider_dispatch_count: 0,
      remote_dispatch_count: 0,
    },
    dynamic_production_plan_projection: {
      plan_id: "plan_m3_probe",
      plan_digest: "e".repeat(64),
      planning_state: "planned",
      plan_version: 1,
      shot_count: 3,
      chunk_count: 4,
      provider_dispatch_count: 0,
      remote_dispatch_count: 0,
    },
  },
};
const selectedNode = state.nodes.script_node;
const context = agentChatContextSnapshot({ studioState: state, selectedNode, section: "canvas" });
const store = createAgentChatContextStore();
const session = store.get(agentChatContextKey(context));
const submit = submitAgentChatMessage(session, "/m3-context-pack 专业剧本与分镜审计", context);
if (submit.status !== "preview" || submit.command.command_type !== "build_m3_context_pack") {
  throw new Error(`unexpected preview: ${submit.status}/${submit.command.command_type}`);
}
if (session.messages.some((message) => String(message.text).includes("/m3-context-pack"))) {
  throw new Error("raw slash command leaked into default chat history");
}
let previewPayload = null;
let confirmPayload = null;
let undoPayload = null;
const runtime = {
  previewM3ContextPack: async (payload) => {
    previewPayload = payload;
    return {
      command: { status: "preview", command_type: "build_context_pack" },
      context_pack: { context_pack_id: "ctx_m3_probe", relevant_knowledge_refs: ["kp_story_causal_theme_v1"], provider_dispatch_count: 0 },
      provider_dispatch_count: 0,
      remote_dispatch_count: 0,
    };
  },
  confirmM3ContextPack: async (payload) => {
    confirmPayload = payload;
    return {
      command: { status: "confirmed", command_type: "build_context_pack" },
      context_pack: {
        context_pack_id: "ctx_m3_probe",
        canonical_truth_digest: "f".repeat(64),
        relevant_knowledge_refs: ["kp_story_causal_theme_v1", "kp_context_privacy_injection_v1"],
        provider_dispatch_count: 0,
        remote_dispatch_count: 0,
      },
      receipt: {
        receipt_id: "receipt_m3_probe",
        summary: "已确认精准上下文包；Provider 保持关闭。",
        undo_available: true,
        provider_dispatch_count: 0,
        remote_dispatch_count: 0,
      },
      projection: { context_pack_count: 1, provider_dispatch_count: 0, remote_dispatch_count: 0 },
      provider_dispatch_count: 0,
      remote_dispatch_count: 0,
    };
  },
  undoM3ContextPack: async (payload) => {
    undoPayload = payload;
    return {
      receipt: {
        receipt_id: "receipt_m3_undo",
        status: "undone",
        summary: "精准上下文包选择已撤销。",
        provider_dispatch_count: 0,
        remote_dispatch_count: 0,
      },
      projection: { current_context_pack_id: "", provider_dispatch_count: 0, remote_dispatch_count: 0 },
      provider_dispatch_count: 0,
      remote_dispatch_count: 0,
    };
  },
};
const stateStore = { get: () => state, set: (mutator) => mutator(state) };
const receipt = await executePendingAgentCommandWithRuntime(session, stateStore, runtime);
if (receipt.runtime_domain !== "m3_context" || receipt.command_type !== "build_m3_context_pack") {
  throw new Error("M3 context receipt domain/type mismatch");
}
if (!previewPayload || !confirmPayload || previewPayload.provider_dispatch_count !== 0 || confirmPayload.provider_dispatch_count !== 0) {
  throw new Error("M3 context runtime payload did not preserve Provider0");
}
if (confirmPayload.exclusions.includes("prompt_injection") === false || confirmPayload.tool_gates.model_call !== false) {
  throw new Error("context exclusions/tool gates missing");
}
await undoAgentReceiptWithRuntime(session, receipt, stateStore, runtime);
if (!undoPayload || undoPayload.context_pack_id !== "ctx_m3_probe") {
  throw new Error("M3 context undo did not call runtime");
}
const defaultText = session.messages.map((message) => message.text).join("\n");
if (defaultText.includes("raw_command_text") || defaultText.includes("schema_version") || defaultText.includes("/m3-context-pack")) {
  throw new Error("internal command data leaked into default chat presentation");
}
console.log(JSON.stringify({
  status: "passed",
  commandType: submit.command.command_type,
  runtimeDomain: receipt.runtime_domain,
  contextPackId: receipt.context_pack_id,
  providerDispatchCount: receipt.provider_dispatch_count || 0,
  remoteDispatchCount: receipt.remote_dispatch_count || 0,
  storyboardWrite: receipt.storyboard_write || false,
  previewKnowledgeRefs: confirmPayload.requested_domains.length,
}, null, 2));
"""
    result = _node_eval(root, script)
    if result["returncode"] != 0:
        findings.append(_finding("P0", "agent_chat_probe", result["stderr"] or result["stdout"] or "node probe failed"))
        return {"providerDispatchCount": 0, "remoteDispatchCount": 0, "failed": True}
    try:
        return json.loads(result["stdout"])
    except json.JSONDecodeError as exc:
        findings.append(_finding("P0", "agent_chat_probe", f"invalid node probe output: {exc}"))
        return {"providerDispatchCount": 0, "remoteDispatchCount": 0, "failed": True}


def _node_eval(root: Path, script: str) -> dict[str, Any]:
    import subprocess

    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {"returncode": completed.returncode, "stdout": completed.stdout.strip(), "stderr": completed.stderr.strip()}


def _span(text: str, quote: str) -> dict[str, Any]:
    start = text.index(quote)
    return {"start": start, "end": start + len(quote), "quote": quote}


def _contains_fixed_template(cases: list[dict[str, Any]]) -> bool:
    case_counts = [len(((case.get("story_plan_candidate") or {}).get("shots") or [])) for case in cases]
    if len(set(case_counts)) == 1:
        return True
    for case in cases:
        shots = (case.get("story_plan_candidate") or {}).get("shots") or []
        durations = [float(shot.get("duration_seconds") or 0) for shot in shots]
        if len(shots) == 4 and all(abs(duration - 15) < 0.001 for duration in durations):
            return True
    return False


def _provider_count(evidence: dict[str, Any]) -> int:
    return _sum_counts(evidence, "provider_dispatch_count", "providerDispatchCount")


def _remote_count(evidence: dict[str, Any]) -> int:
    return _sum_counts(evidence, "remote_dispatch_count", "remoteDispatchCount")


def _sum_counts(value: Any, *keys: str) -> int:
    if isinstance(value, dict):
        total = 0
        for key, item in value.items():
            if key in keys and isinstance(item, int):
                total += item
            else:
                total += _sum_counts(item, *keys)
        return total
    if isinstance(value, list):
        return sum(_sum_counts(item, *keys) for item in value)
    return 0


def _stable_trace(evidence: dict[str, Any]) -> str:
    digest = json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    import hashlib

    return hashlib.sha256(digest).hexdigest()[:12]


def _finding(severity: str, scope: str, issue: str) -> dict[str, Any]:
    return {"severity": severity, "scope": scope, "issue": issue}


if __name__ == "__main__":
    raise SystemExit(main())
