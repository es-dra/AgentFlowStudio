"""Evaluator for the M6.5 embedded creative action product shell gate."""
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
        "scope": "embedded_runtime",
        "issue": "embedded creative action runtime route is missing structured server_codex preview contract",
        "path": "apps/api/runtime_embedded_creative_actions.py",
        "must_include": (
            "EMBEDDED_CREATIVE_CONTRACT_ID",
            "SERVER_CODEX_SERVICE_ID",
            "structured_output_schema_digest",
            "not_canvas_mutation_until_user_apply",
            "dynamic_shot_breakdown",
        ),
        "must_exclude": ("provider_raw_response_stored\": True", "fallback template"),
    },
    {
        "severity": "P0",
        "scope": "embedded_frontend",
        "issue": "node-local optimize/breakdown still route through global AI transcript",
        "path": "apps/studio/src/prompt-bar.js",
        "must_include": ("startEmbeddedCreativeAction", '"script_revision"', '"shot_breakdown"'),
        "must_exclude": ("/optimize-selected-default", "/plan-selected-script-shots"),
    },
    {
        "severity": "P0",
        "scope": "embedded_frontend",
        "issue": "node action handler does not keep preview/apply/cancel inside the selected node",
        "path": "apps/studio/src/canvas-node-action-handler.js",
        "must_include": (
            "startEmbeddedCreativeAction",
            "applyEmbeddedCreativeAction",
            "cancelEmbeddedCreativeAction",
            "embedded-creative-apply",
        ),
        "must_exclude": ("afs:agent-chat-submit",),
    },
    {
        "severity": "P0",
        "scope": "template_rejection",
        "issue": "global optimization path must start the same embedded task instead of a canned local revision",
        "path": "apps/studio/src/agent-chat-lifecycle.js",
        "must_include": ("start_embedded_creative_action", "embeddedCreativeActionCommand", "same_node_revision_preview"),
        "must_exclude": ("核心意图", "叙事推进", "制作优化"),
    },
    {
        "severity": "P1",
        "scope": "palette",
        "issue": "node palette has not been reduced to creator-facing primary choices",
        "path": "apps/studio/src/panels/add-node-menu.js",
        "must_include": (
            'QUICK_ACTION_IDS = ["node_text", "node_script", "node_sequence", "asset_character", "node_image", "node_video"]',
            "更多/高级",
            "HANDLE_PRIMARY_TYPES",
        ),
        "must_exclude": ("参考节点", "disabled", "beta"),
    },
    {
        "severity": "P1",
        "scope": "edge_geometry",
        "issue": "persistent edge endpoint geometry is not anchored to visible frame/handle state",
        "path": "apps/studio/src/interaction/port-geometry.js",
        "must_include": ("nodeCardBorderPoint", "isPortVisiblyExposed", "VISIBLE_PORT_OPACITY"),
        "must_exclude": (),
    },
    {
        "severity": "P1",
        "scope": "shell_ia",
        "issue": "topbar/help/account IA remains noisy or undiscoverable",
        "path": "apps/studio/src/product-shell.js",
        "must_include": ("buildHelpEntry", "buildHelpMenu", "buildAccountEntry", "任意节点开始"),
        "must_exclude": ("<span>AgentFlow Studio</span>", "<span>AI 漫剧</span>"),
    },
    {
        "severity": "P1",
        "scope": "ai_panel",
        "issue": "AI panel still defaults to raw metadata and receipt stack",
        "path": "apps/studio/src/agent-chat-panel.js",
        "must_include": ("agent-context-chip", "agent-context-details", "活动记录"),
        "must_exclude": ("<strong>Agent Chat</strong>", "已记录到当前上下文"),
    },
)


NODE_PROBE = r"""
import {
  applyEmbeddedCreativeAction,
  cancelEmbeddedCreativeAction,
  startEmbeddedCreativeAction,
} from './apps/studio/src/embedded-creative-actions.js';

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const originalText = '孙悟空大战猪八戒。';
const state = {
  meta: { projectId: 'm6_5_probe', projectName: 'M6.5 Probe' },
  nodes: {
    n1: {
      id: 'n1',
      type: 'text',
      title: '短想法',
      content: originalText,
      prompt: originalText,
      status: 'draft',
      x: 100,
      y: 100,
      w: 280,
      h: 220,
      params: {},
    },
  },
  edges: {},
  order: ['n1'],
  assets: [],
  production: {},
  selection: { nodeIds: ['n1'], edgeId: null },
  ui: {},
};
let flushCount = 0;
const store = {
  get: () => state,
  set: (mutator) => mutator(state),
  flushRuntimeSave: async () => {
    flushCount += 1;
  },
};
const runtime = {
  previewEmbeddedCreativeAction: async (payload) => ({
    mode: 'llm',
    provider_calls_started: true,
    preview: {
      preview_id: 'preview_probe_1',
      action_type: payload.action_type,
      mode: payload.mode,
      revised_text: '花果山黄昏，孙悟空误会猪八戒偷吃供果，举棒追问；八戒护着篮子边躲边辩，二人的嬉闹逐步露出妖怪留下的真正线索。',
      change_summary: ['补足冲突起因', '加入动作与关系变化'],
      rationale: '从短想法扩展为可拍场面，仍保持同一节点身份。',
      unresolved_decisions: [],
      quality_flags: ['preview_only'],
      screenplay_candidate: {
        title: '花果山误会',
        version_label: 'v1',
        logline: '孙悟空误会猪八戒偷吃供果，两人从冲突转向发现妖怪踪迹后的联手。',
        characters: [
          { name: '孙悟空', goal: '查清供果失踪', conflict: '急躁误判伙伴', change: '从逼问转为联手' },
          { name: '猪八戒', goal: '证明自己清白', conflict: '馋嘴名声让解释失效', change: '从躲闪转为指出线索' },
        ],
        scenes: [{
          heading: '外景 - 花果山果林 - 傍晚',
          space_type: '外景',
          location: '花果山果林',
          time_of_day: '傍晚',
          purpose: '建立误会、冲突和联手转折',
          blocks: [
            { type: 'action', text: '空篮倒在石阶旁，孙悟空握棒逼近猪八戒。' },
            { type: 'character', text: '孙悟空' },
            { type: 'dialogue', text: '呆子，供果少了三颗，你还敢护着篮子？' },
            { type: 'character', text: '猪八戒' },
            { type: 'dialogue', text: '猴哥，我只闻了闻，真动手的是林子里那股腥风。' },
          ],
        }],
      },
    },
    provider_lineage: {
      service_id: 'server_codex',
      provider: 'codex_local',
      model_surface: 'server-codex-login',
      request_id: 'req_probe',
      structured_output_contract_id: 'afs.runtime.embedded_creative_action.v0.2',
      structured_output_schema_digest: 'digest_probe',
      provider_calls_started: true,
      external_paid_cost_usd: 0,
    },
    graph_mutation: { before_version: 1, after_version: 1, before_digest: 'a'.repeat(64), after_digest: 'a'.repeat(64), mutated: false },
    latency_ms: 24,
    cost_usd: 0,
  }),
};

await startEmbeddedCreativeAction(store, runtime, state.nodes.n1, 'script_revision', { mode: 'professional_expansion' });
assert(state.nodes.n1.content === originalText, 'preview must not mutate node content');
assert(state.order.length === 1, 'preview must not add a script-version node');
assert(state.nodes.n1.params.embeddedCreativeAction?.status === 'preview', 'preview must be stored on the selected node');
cancelEmbeddedCreativeAction(store, 'n1');
assert(state.nodes.n1.content === originalText, 'cancel must keep node content unchanged');

await startEmbeddedCreativeAction(store, runtime, state.nodes.n1, 'script_revision', { mode: 'professional_expansion' });
applyEmbeddedCreativeAction(store, 'n1');
assert(state.nodes.n1.content !== originalText, 'apply must update current node content');
assert(state.order.length === 1, 'apply must preserve node count and identity');
assert(state.nodes.n1.params.revisions.length === 1, 'apply must append same-node revision history');
assert(state.nodes.n1.params.revisions[0].same_node_identity === true, 'revision must record same-node identity');
assert(state.nodes.n1.params.embeddedCreativeAction.status === 'applied', 'apply must show applied state');

process.stdout.write(JSON.stringify({
  status: 'passed',
  flushCount,
  nodeCount: state.order.length,
  revisionCount: state.nodes.n1.params.revisions.length,
  providerCallsStarted: state.nodes.n1.params.revisions[0].provider_lineage.provider_calls_started,
  graphMutated: state.nodes.n1.params.revisions[0].graph_mutation.mutated,
}));
"""


def evaluate(root: Path) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    source_evidence = _evaluate_source_contracts(root, findings)
    node_probe = _run_node_probe(root, findings)
    summary = {
        "status": "PASS" if not any(item["severity"] in {"P0", "P1"} for item in findings) else "FAIL",
        "p0": sum(1 for item in findings if item["severity"] == "P0"),
        "p1": sum(1 for item in findings if item["severity"] == "P1"),
        "p2": sum(1 for item in findings if item["severity"] == "P2"),
    }
    return {
        "evaluator": "AFS_M6_5_REAL_SCRIPT_EXPANSION_EMBEDDED_AI_ACTION_PRODUCT_SHELL",
        "summary": summary,
        "findings": findings,
        "source_contracts": source_evidence,
        "node_probe": node_probe,
        "non_claims": [
            "not_owner_human_acceptance",
            "not_business_validation",
            "not_paid_image_video_generation",
        ],
    }


def _evaluate_source_contracts(root: Path, findings: list[dict[str, str]]) -> dict[str, Any]:
    evidence: dict[str, Any] = {}
    for contract in SOURCE_CONTRACTS:
        path = root / contract["path"]
        if not path.is_file():
            findings.append(_finding(contract, f"missing file: {contract['path']}"))
            continue
        source = path.read_text(encoding="utf-8")
        missing = [marker for marker in contract["must_include"] if marker not in source]
        present = [marker for marker in contract["must_exclude"] if marker and marker in source]
        if missing or present:
            details = []
            if missing:
                details.append(f"missing={missing}")
            if present:
                details.append(f"prohibited={present}")
            findings.append(_finding(contract, "; ".join(details)))
        evidence[contract["scope"]] = {"path": contract["path"], "checked": True}
    return evidence


def _finding(contract: dict[str, Any], detail: str) -> dict[str, str]:
    return {
        "severity": str(contract["severity"]),
        "scope": str(contract["scope"]),
        "issue": str(contract["issue"]),
        "detail": detail,
    }


def _run_node_probe(root: Path, findings: list[dict[str, str]]) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            ["node", "--input-type=module", "-e", NODE_PROBE],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except subprocess.CalledProcessError as exc:
        findings.append({
            "severity": "P0",
            "scope": "node_probe",
            "issue": "embedded creative action mutation contract failed",
            "detail": exc.stderr or exc.stdout,
        })
        return {}
    return json.loads(completed.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--report", default="")
    args = parser.parse_args()
    report = evaluate(Path(args.repo_root).resolve())
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["summary"]["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
