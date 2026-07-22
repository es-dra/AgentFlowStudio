"""Evaluator for the M6.4 freeform canvas and AI creative copilot gate."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]

SOURCE_CONTRACTS = (
    {
        "severity": "P0",
        "scope": "ai_panel",
        "issue": "primary AI panel still uses generic Agent Chat label",
        "path": "apps/studio/src/agent-chat-panel.js",
        "must_include": ("AI 创作搭档",),
        "must_exclude": ("<strong>Agent Chat</strong>", "发送到 Agent Chat", "展开 Agent Chat"),
    },
    {
        "severity": "P0",
        "scope": "ai_panel",
        "issue": "AI panel non-command conversation does not route through runtime LLM when runtime is available",
        "path": "apps/studio/src/agent-chat-lifecycle.js",
        "must_include": ("submitAgentChatMessageWithRuntime", "runtime.agentChatConversation", "runtime_llm_unavailable"),
        "must_exclude": ("已记录到当前上下文。需要改动画布时，请发送可预览命令。",),
    },
    {
        "severity": "P0",
        "scope": "runtime_llm_route",
        "issue": "Runtime agent chat route is missing server_codex structured provider contract",
        "path": "apps/api/runtime_agent_chat_conversation.py",
        "must_include": ("AGENT_CHAT_CONTRACT_ID", "SERVER_CODEX_SERVICE_ID", "structured_output_schema_digest", "graph_mutation"),
        "must_exclude": ("provider raw response persisted", "raw_provider_stdout_stored"),
    },
    {
        "severity": "P0",
        "scope": "revision_semantics",
        "issue": "ordinary optimize must revise the same node instead of creating a script-version node",
        "path": "apps/studio/src/agent-chat-lifecycle.js",
        "must_include": ("command_type: \"revise_selected_node\"", "applySameNodeRevision", "fork_selected_node"),
        "must_exclude": (),
    },
    {
        "severity": "P0",
        "scope": "freeform_nodes",
        "issue": "required freeform node types are not registered",
        "path": "apps/studio/src/nodes.js",
        "must_include": ("sequence:", "scene:", "shot:", "character:", "location:", "prop:", "ref:"),
        "must_exclude": (),
    },
    {
        "severity": "P0",
        "scope": "direct_reference_entry",
        "issue": "reference image upload is still limited to image/video nodes",
        "path": "apps/studio/src/node-upload-actions.js",
        "must_include": ("IMAGE_UPLOAD_NODE_TYPES", "\"ref\"", "\"character\"", "\"location\"", "\"prop\"", "\"shot\""),
        "must_exclude": ("[\"image\", \"video\"].includes(node.type)",),
    },
    {
        "severity": "P0",
        "scope": "freeform_canvas_input",
        "issue": "node plus/handle events can still be swallowed by generic chrome filtering",
        "path": "apps/studio/src/canvas-input.js",
        "must_include": ("const portBtn", "startConnectSession", "if (isChromeTarget(e)) return null"),
        "must_exclude": (),
    },
    {
        "severity": "P1",
        "scope": "plan_surface",
        "issue": "production plan surface remains permanent instead of contextual and collapsible",
        "path": "apps/studio/src/product-shell.js",
        "must_include": ("buildContextualPlanSurface", "planningPanelOpen", "调整制作方案面板高度", "可自由开始"),
        "must_exclude": ("需要确认制作方案",),
    },
    {
        "severity": "P1",
        "scope": "edge_semantics",
        "issue": "edge semantics and selected-path animation are not protected",
        "path": "apps/studio/src/canvas-edges.js",
        "must_include": ("relationLabel", "edgeAccessibleLabel", "edgeRelatedToFocus", "selected-path"),
        "must_exclude": (),
    },
    {
        "severity": "P1",
        "scope": "reference_entry",
        "issue": "canvas drop/paste reference image entry is missing",
        "path": "apps/studio/src/canvas-reference-entry.js",
        "must_include": ("bindCanvasReferenceEntry", "dragover", "drop", "paste", "uploadSelectedImage"),
        "must_exclude": (),
    },
)


NODE_PROBE = r"""
import {
  agentChatContextKey,
  cancelAgentCommand,
  createAgentChatContextStore,
  executePendingAgentCommand,
  submitAgentChatMessageWithRuntime,
  submitAgentChatMessage,
} from './apps/studio/src/agent-chat-lifecycle.js';

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const context = {
  project_id: 'm6_4_probe',
  section: 'canvas',
  selected_node_id: 'node_1',
  selected_node_type: 'text',
  selected_node_title: '雨夜想法',
  selected_node_status: 'draft',
  selected_node_text: '女孩在雨夜天台寻找失踪的哥哥，她必须在灯牌熄灭前找到线索。',
  canvas_node_count: 1,
  canvas_edge_count: 0,
  counts: { nodes: 1, assets: 0, shots: 0 },
  remote_dispatch_count: 0,
  provider_dispatch_count: 0,
};

const sessions = createAgentChatContextStore();
const session = sessions.get(agentChatContextKey(context));
const greeting = submitAgentChatMessage(session, '你好', context);
assert(greeting.status === 'answered', 'greeting must answer without command preview');
assert(!session.pendingCommand, 'greeting must not create pending command');
assert(greeting.conversation?.provider_dispatch_count === 0 && greeting.conversation?.remote_dispatch_count === 0, 'greeting must not dispatch provider');
assert(!session.messages.at(-1).text.includes('已记录到当前上下文'), 'greeting must not use canned recorded-context copy');
assert(session.messages.at(-1).text.includes('AI 创作搭档'), 'greeting should identify the creative copilot');

const runtimeSession = sessions.get(`${agentChatContextKey(context)}:runtime`);
let runtimePayload = null;
const runtimeGreeting = await submitAgentChatMessageWithRuntime(runtimeSession, '你好', context, {
  agentChatConversation: async (payload) => {
    runtimePayload = payload;
    return {
      mode: 'llm',
      reply: '你好，我会结合当前画布回答；这个想法节点还在草稿状态，下一步可以先补角色目标和场景。',
      provider_calls_started: true,
      provider_lineage: { request_id: 'req_runtime_probe' },
      graph_mutation: { mutated: false, before_digest: 'a'.repeat(64), after_digest: 'a'.repeat(64) },
      latency_ms: 12,
      cost_usd: 0,
    };
  },
});
assert(runtimeGreeting.status === 'answered', 'runtime greeting must answer through runtime route');
assert(runtimeGreeting.conversation?.source === 'runtime_llm', 'runtime greeting must be marked runtime_llm');
assert(runtimeGreeting.conversation?.provider_dispatch_count === 1, 'runtime greeting must record provider dispatch');
assert(runtimePayload?.provider_service_id === 'server_codex', 'runtime greeting must request server_codex');
assert(runtimePayload?.message === '你好', 'runtime greeting must pass exact user message');
assert(runtimePayload?.canvas_summary?.selected_node_title === '雨夜想法', 'runtime greeting must include safe selected-node context');

const nodeQuestion = submitAgentChatMessage(session, '这个节点是什么', context);
assert(nodeQuestion.status === 'answered', 'node question must answer conversationally');
assert(!session.pendingCommand, 'node question must not mutate');

const state = {
  meta: { seq: 1, projectId: 'm6_4_probe' },
  nodes: {
    node_1: {
      id: 'node_1',
      type: 'text',
      title: '雨夜想法',
      x: 120,
      y: 140,
      w: 280,
      h: 260,
      prompt: context.selected_node_text,
      content: context.selected_node_text,
      status: 'draft',
      params: {},
      result: null,
      collapsed: false,
    },
  },
  edges: {},
  order: ['node_1'],
  groups: {},
  assets: [],
  selection: { nodeIds: ['node_1'], edgeId: null },
  ui: {},
};

const beforeNodeCount = state.order.length;
const optimizePreview = submitAgentChatMessage(session, '优化当前文本', context);
assert(optimizePreview.status === 'preview', 'optimize must return a preview');
assert(session.pendingCommand?.command_type === 'revise_selected_node', 'ordinary optimize must be same-node revision');
assert(session.pendingCommand.impact.node_ids.includes('node_1'), 'optimize impact must name selected node');
const reviseReceipt = executePendingAgentCommand(session, state);
assert(state.order.length === beforeNodeCount, 'same-node revision must not create a node');
assert(state.nodes.node_1.params.revisions.length === 1, 'same-node revision history must be stored');
assert(state.nodes.node_1.status === 'draft', 'revised node must remain draft/reviewable');
assert(reviseReceipt.provider_dispatch_count === 0, 'local revision must not dispatch provider');

const forkPreview = submitAgentChatMessage(session, '创建分支版本：换成哥哥视角', context);
assert(forkPreview.status === 'preview', 'fork must return preview');
assert(session.pendingCommand?.command_type === 'fork_selected_node', 'explicit fork must be separate command');
const forkReceipt = executePendingAgentCommand(session, state);
assert(state.order.length === beforeNodeCount + 1, 'explicit fork must create one new node');
assert(forkReceipt.created_edge_ids.length === 1, 'explicit fork must create provenance edge');
assert(state.edges[forkReceipt.created_edge_ids[0]].relation_type === 'fork', 'fork edge must be semantic');

const edgeId = forkReceipt.created_edge_ids[0];
const edgeContext = {
  ...context,
  selected_node_id: '',
  selected_node_type: '',
  selected_node_text: '',
  selected_edge_id: edgeId,
  selected_edge_relation_type: 'fork',
  selected_edge_from_title: '雨夜想法',
  selected_edge_to_title: state.nodes[forkReceipt.created_node_id].title,
};
const edgeQuestion = submitAgentChatMessage(session, '这条连线代表什么', edgeContext);
assert(edgeQuestion.status === 'answered', 'edge question must answer conversationally');
assert(!session.pendingCommand, 'edge question must not mutate');
const relationPreview = submitAgentChatMessage(session, '把这条连线改成参考', edgeContext);
assert(relationPreview.status === 'preview', 'relation change must preview');
assert(session.pendingCommand?.command_type === 'change_edge_relation', 'relation change must use edge command');
executePendingAgentCommand(session, state);
assert(state.edges[edgeId].relation_type === 'reference', 'relation command must update only selected edge');

const deletePreview = submitAgentChatMessage(session, '删除选中连线', { ...edgeContext, selected_edge_relation_type: 'reference' });
assert(deletePreview.status === 'preview', 'delete edge must preview');
cancelAgentCommand(session);
assert(state.edges[edgeId], 'cancelled delete preview must not mutate graph');

const scenePreview = submitAgentChatMessage(session, '创建场景节点', context);
assert(scenePreview.status === 'preview', 'scene node creation must preview');
assert(session.pendingCommand?.create_node?.type === 'scene', '创建场景节点 must create a narrative scene node, not a location asset');
const sceneReceipt = executePendingAgentCommand(session, state);
assert(state.nodes[sceneReceipt.created_node_id].type === 'scene', 'scene receipt must create scene node');

const locationPreview = submitAgentChatMessage(session, '创建场景空间节点', context);
assert(locationPreview.status === 'preview', 'location node creation must preview');
assert(session.pendingCommand?.create_node?.type === 'location', '创建场景空间节点 must create a location/space asset node');
const locationReceipt = executePendingAgentCommand(session, state);
assert(state.nodes[locationReceipt.created_node_id].type === 'location', 'location receipt must create location node');

console.log(JSON.stringify({
  status: 'passed',
  node_count: state.order.length,
  edge_count: Object.keys(state.edges).length,
  revision_count: state.nodes.node_1.params.revisions.length,
  provider_dispatch_count: 0,
  cost_usd: 0
}));
"""


def evaluate(root: Path, round_a_report: Path | None, round_b_report: Path | None, issue_ledger: Path | None) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    source_results = _evaluate_sources(root, findings)
    node_probe = _run_node_probe(root, findings)
    browser_rounds = _evaluate_browser_reports(round_a_report, round_b_report, findings)
    ledger = _evaluate_issue_ledger(issue_ledger, findings)
    p0 = sum(item["severity"] == "P0" for item in findings)
    p1 = sum(item["severity"] == "P1" for item in findings)
    p2 = sum(item["severity"] == "P2" for item in findings)
    return {
        "schema_version": "afs.m6_4.freeform_canvas_ai_copilot_evaluator.v0.1",
        "verdict": "PASS" if not findings else "FAIL",
        "P0": p0,
        "P1": p1,
        "P2": p2,
        "findings": findings,
        "source_contracts": source_results,
        "node_lifecycle_probe": node_probe,
        "browser_rounds": browser_rounds,
        "issue_ledger": ledger,
        "provider_dispatch_count": 0,
        "cost_usd": 0,
        "non_claims": [
            "not_owner_acceptance",
            "not_business_validation",
            "not_paid_image_video_smoke",
            "not_human_creative_acceptance",
            "not_public_release",
        ],
    }


def _evaluate_sources(root: Path, findings: list[dict[str, str]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for contract in SOURCE_CONTRACTS:
        path = root / contract["path"]
        if not path.exists():
            findings.append({"severity": contract["severity"], "scope": contract["scope"], "issue": f"{contract['issue']}: missing {path}"})
            results.append({"path": contract["path"], "status": "missing"})
            continue
        text = path.read_text(encoding="utf-8")
        missing = [token for token in contract["must_include"] if token not in text]
        leaked = [token for token in contract["must_exclude"] if token in text]
        if missing or leaked:
            findings.append({
                "severity": contract["severity"],
                "scope": contract["scope"],
                "issue": contract["issue"],
                "missing": ", ".join(missing),
                "leaked": ", ".join(leaked),
            })
        results.append({"path": contract["path"], "status": "passed" if not missing and not leaked else "failed"})
    return results


def _run_node_probe(root: Path, findings: list[dict[str, str]]) -> dict[str, Any]:
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", NODE_PROBE],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    )
    if completed.returncode != 0:
        findings.append({
            "severity": "P0",
            "scope": "node_lifecycle_probe",
            "issue": "AI conversation/freeform mutation lifecycle probe failed",
            "stderr": completed.stderr[-900:],
        })
        return {"status": "failed", "returncode": completed.returncode, "stderr_tail": completed.stderr[-900:]}
    try:
        payload = json.loads(completed.stdout.strip())
    except json.JSONDecodeError as exc:
        findings.append({"severity": "P0", "scope": "node_lifecycle_probe", "issue": f"probe did not emit JSON: {exc}"})
        return {"status": "failed", "stdout": completed.stdout[-900:]}
    if payload.get("status") != "passed":
        findings.append({"severity": "P0", "scope": "node_lifecycle_probe", "issue": "probe status is not passed"})
    return payload


def _evaluate_browser_reports(round_a_report: Path | None, round_b_report: Path | None, findings: list[dict[str, str]]) -> dict[str, Any]:
    if not round_a_report and not round_b_report:
        return {"status": "not_requested"}
    rounds: dict[str, Any] = {}
    for label, path in (("A", round_a_report), ("B", round_b_report)):
        if not path:
            findings.append({"severity": "P1", "scope": "browser_rounds", "issue": f"Round {label} report not supplied"})
            rounds[label] = {"status": "missing"}
            continue
        payload = _load_json(path, findings, f"round_{label.lower()}")
        rounds[label] = _browser_round_summary(label, payload, findings)
    return rounds


def _browser_round_summary(label: str, payload: dict[str, Any], findings: list[dict[str, str]]) -> dict[str, Any]:
    if not payload:
        return {"status": "missing"}
    if payload.get("status") != "passed":
        findings.append({"severity": "P0", "scope": "browser_rounds", "issue": f"Round {label} browser report did not pass"})
    checks = payload.get("checks") if isinstance(payload.get("checks"), dict) else {}
    required_checks = (
        "greeting_zero_mutation",
        "command_cancel_zero_mutation",
        "command_confirm_declared_mutation",
        "same_node_revision",
        "explicit_fork_creates_node",
        "plus_node_creation",
        "manual_connection",
        "edge_inspect_change_delete_undo",
        "reference_image_entry",
        "plan_panel_contextual",
        "mobile_freeform_usable",
        "console_network_clean",
    )
    for check in required_checks:
        if checks.get(check) is not True:
            findings.append({"severity": "P1", "scope": "browser_rounds", "issue": f"Round {label} failed check {check}"})
    roles = payload.get("role_task_completion_matrix") if isinstance(payload.get("role_task_completion_matrix"), dict) else {}
    expected_roles = (
        "first_time_nontechnical_creator",
        "screenwriter",
        "director_storyboard_artist",
        "concept_artist",
        "asset_continuity_supervisor",
        "producer_cost_reviewer",
        "editor_recovery_operator",
        "advanced_graph_user",
        "keyboard_low_vision_reduced_motion",
        "owner_adversarial_tester",
    )
    for role in expected_roles:
        if roles.get(role, {}).get("completed") is not True:
            findings.append({"severity": "P1", "scope": "role_matrix", "issue": f"Round {label} role incomplete: {role}"})
    return {
        "status": payload.get("status"),
        "check_count": len(checks),
        "screenshot_count": len(payload.get("screenshots") or {}),
        "console_error_count": payload.get("console_error_count"),
        "response_error_count": payload.get("response_error_count"),
    }


def _evaluate_issue_ledger(path: Path | None, findings: list[dict[str, str]]) -> dict[str, Any]:
    if not path:
        return {"status": "not_requested"}
    payload = _load_json(path, findings, "issue_ledger")
    if not payload:
        return {"status": "missing"}
    issues = payload.get("issues")
    if not isinstance(issues, list) or not issues:
        findings.append({"severity": "P1", "scope": "issue_ledger", "issue": "issue ledger missing resolved issues"})
        return {"status": "failed"}
    open_user_visible = []
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        severity = str(issue.get("severity") or "").upper()
        status = str(issue.get("status") or "").lower()
        if severity in {"P0", "P1", "P2"} and status != "resolved":
            open_user_visible.append(issue.get("id") or "<unknown>")
    if open_user_visible:
        findings.append({"severity": "P0", "scope": "issue_ledger", "issue": f"user-visible issues remain open: {', '.join(open_user_visible)}"})
    return {"status": "passed" if not open_user_visible else "failed", "issue_count": len(issues), "open_user_visible": open_user_visible}


def _load_json(path: Path, findings: list[dict[str, str]], label: str) -> dict[str, Any]:
    if not path.exists():
        findings.append({"severity": "P0", "scope": label, "issue": f"{label} missing: {path}"})
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        findings.append({"severity": "P0", "scope": label, "issue": f"{label} is not valid JSON: {exc}"})
        return {}
    return payload if isinstance(payload, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate M6.4 freeform canvas and AI creative copilot contracts.")
    parser.add_argument("--root", default=str(REPO_ROOT))
    parser.add_argument("--round-a-report", default="")
    parser.add_argument("--round-b-report", default="")
    parser.add_argument("--issue-ledger", default="")
    args = parser.parse_args()
    report = evaluate(
        Path(args.root).resolve(),
        Path(args.round_a_report).resolve() if args.round_a_report else None,
        Path(args.round_b_report).resolve() if args.round_b_report else None,
        Path(args.issue_ledger).resolve() if args.issue_ledger else None,
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
