"""Evaluator for the M6.6 visible creative tasks, screenplay, and graph actions gate."""
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
        "scope": "runtime_screenplay_contract",
        "issue": "embedded LLM route accepts prose-only script revisions",
        "path": "apps/api/runtime_embedded_creative_actions.py",
        "must_include": (
            "afs.runtime.embedded_creative_action.v0.2",
            "_screenplay_candidate_schema",
            "_safe_screenplay_candidate",
            "screenplay candidate lacks professional scene/action structure",
            "long prose story must fail",
        ),
        "must_exclude": ("fallback template", 'provider_raw_response_stored": True'),
    },
    {
        "severity": "P0",
        "scope": "visible_creative_task",
        "issue": "node-local LLM actions lack durable visible task state",
        "path": "apps/studio/src/creative-task-contract.js",
        "must_include": (
            "CREATIVE_TASK_PHASES",
            "task_id",
            "dispatching",
            "validating",
            "preview_ready",
            "nodeVersion",
            "activeEmbeddedTask",
        ),
        "must_exclude": ("percentage", "percent"),
    },
    {
        "severity": "P0",
        "scope": "sidebar_review",
        "issue": "long creative previews still expand the node instead of the right task review",
        "path": "apps/studio/src/agent-chat-panel.js",
        "must_include": (
            "agent-current-task-review",
            "screenplayCandidateView",
            "shotPlanReview",
            "applyEmbeddedCreativeAction",
            "executeEmbeddedCreativeCommand",
            "start_embedded_creative_action",
        ),
        "must_exclude": ("执行回执栈",),
    },
    {
        "severity": "P0",
        "scope": "compact_node_task",
        "issue": "node body still embeds the full preview and can cover ports/actions",
        "path": "apps/studio/src/canvas-node-body.js",
        "must_include": (
            "compactCreativeTaskResult",
            "完整预览、差异、应用和取消在右侧 AI 创作搭档中审阅",
        ),
        "must_exclude": ("panel.appendChild(creativePreview(action))",),
    },
    {
        "severity": "P0",
        "scope": "visible_shot_candidate_graph",
        "issue": "shot breakdown apply only stores a hidden draft instead of a visible candidate subgraph",
        "path": "apps/studio/src/embedded-creative-actions.js",
        "must_include": (
            "materializeShotCandidateSubgraph",
            "afs.m6_6.visible_shot_candidate_subgraph.v0.1",
            "m6_6_shot_sequence_candidate",
            "m6_6_scene_candidate",
            "m6_6_shot_candidate",
            "created_edge_ids",
        ),
        "must_exclude": ("fixed4x15", "10x6"),
    },
    {
        "severity": "P1",
        "scope": "prompt_collision",
        "issue": "floating prompt bar can cover task review/actions",
        "path": "apps/studio/src/prompt-bar.js",
        "must_include": ("activeEmbeddedTask", "!activeEmbeddedTask(node)"),
        "must_exclude": (),
    },
    {
        "severity": "P1",
        "scope": "companion_graph_actions",
        "issue": "AI companion commands cannot operate selected canvas objects through typed task contracts",
        "path": "apps/studio/src/agent-chat-lifecycle.js",
        "must_include": (
            "把当前节点剧本化",
            "embeddedCreativeActionCommand",
            "same_node_revision_preview",
            "visible_candidate_storyboard_subgraph",
        ),
        "must_exclude": ("请点击节点上的“优化”", "核心意图", "叙事推进", "制作优化"),
    },
)


NODE_PROBE = r"""
import {
  agentChatContextKey,
  createAgentChatContextStore,
  submitAgentChatMessage,
} from './apps/studio/src/agent-chat-lifecycle.js';
import {
  applyEmbeddedCreativeAction,
  startEmbeddedCreativeAction,
} from './apps/studio/src/embedded-creative-actions.js';

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const originalText = '孙悟空大战猪八戒。';
const state = {
  meta: { projectId: 'm6_6_probe', projectName: 'M6.6 Probe', seq: 1 },
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
  flushRuntimeSave: async () => { flushCount += 1; },
};
const screenplayCandidate = {
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
};
const shotPlan = {
  total_shots: 3,
  estimated_duration_sec: 18,
  scenes: [{
    title: '花果山误会',
    purpose: '从误会推进到联手',
    shots: [
      { title: '空篮证据', duration_sec: 4, shot_size: '中近景', camera_angle: '略低机位', movement: '缓慢推进', blocking: '悟空逼近空篮', sound: '桃核滚落', transition: '动作切', narrative_purpose: '建立误会证据' },
      { title: '棍耙交错', duration_sec: 8, shot_size: '全景转近景', camera_angle: '侧向跟拍', movement: '横移追随', blocking: '悟空追打八戒闪躲', sound: '金属碰撞', transition: '节奏切', narrative_purpose: '把冲突推高' },
      { title: '妖影转折', duration_sec: 6, shot_size: '双人中景', camera_angle: '平视', movement: '停顿后摇向树林', blocking: '两人同时停手看向黑影', sound: '风声压低', transition: '悬念切', narrative_purpose: '转向共同目标' },
    ],
  }],
};
const runtime = {
  previewEmbeddedCreativeAction: async (payload) => ({
    mode: 'llm',
    provider_calls_started: true,
    preview: payload.action_type === 'shot_breakdown'
      ? {
        preview_id: 'preview_shot',
        action_type: payload.action_type,
        mode: payload.mode,
        revised_text: '这一场拆为误会证据、动作冲突和妖影转折三组镜头，数量和时长由动作节拍决定。',
        change_summary: ['动态镜头数', '每镜头有叙事目的'],
        rationale: '分镜候选先可见审阅，应用后创建候选子图。',
        unresolved_decisions: [],
        quality_flags: ['dynamic_count'],
        shot_plan: shotPlan,
      }
      : {
        preview_id: 'preview_script',
        action_type: payload.action_type,
        mode: payload.mode,
        revised_text: '外景 - 花果山果林 - 傍晚\n\n空篮倒在石阶旁，孙悟空握棒逼近猪八戒。\n\n孙悟空\n呆子，供果少了三颗，你还敢护着篮子？\n\n猪八戒\n猴哥，我只闻了闻，真动手的是林子里那股腥风。',
        change_summary: ['改成专业剧本场景', '加入角色目标、冲突和对白'],
        rationale: '剧本化预览保留同一节点身份，应用前不写图。',
        unresolved_decisions: [],
        quality_flags: ['screenplay_format'],
        screenplay_candidate: screenplayCandidate,
      },
    provider_lineage: {
      service_id: 'server_codex',
      provider: 'codex_local',
      model_surface: 'server-codex-login',
      request_id: `req_${payload.action_type}`,
      structured_output_contract_id: 'afs.runtime.embedded_creative_action.v0.2',
      structured_output_schema_digest: 'digest_probe',
      provider_calls_started: true,
      external_paid_cost_usd: 0,
    },
    creative_task: {
      task_id: `task_${payload.action_type}`,
      node_id: payload.node_id,
      action_type: payload.action_type,
      mode: payload.mode,
      state: 'preview_ready',
      phase: 'preview_ready',
      completed_phases: ['queued', 'context', 'dispatching', 'validating', 'preview_ready'],
    },
    graph_mutation: { before_version: 1, after_version: 1, before_digest: 'a'.repeat(64), after_digest: 'a'.repeat(64), mutated: false },
    latency_ms: 32,
    cost_usd: 0,
  }),
};

const context = {
  project_id: 'm6_6_probe',
  section: 'canvas',
  selected_node_id: 'n1',
  selected_node_type: 'text',
  selected_node_title: '短想法',
  selected_node_status: 'draft',
  selected_node_text: originalText,
  studio_state_revision_id: 'studio-state-1',
  counts: { nodes: 1, scenes: 0, shots: 0 },
};
const sessions = createAgentChatContextStore();
const session = sessions.get(agentChatContextKey(context));
const commandPreview = submitAgentChatMessage(session, '把当前节点剧本化', context);
assert(commandPreview.status === 'preview', 'companion screenplay command must create preview');
assert(session.pendingCommand?.command_type === 'start_embedded_creative_action', 'companion command must use embedded task contract');
assert(session.pendingCommand?.action_type === 'script_revision', 'screenplay command must target script revision action');

await startEmbeddedCreativeAction(store, runtime, state.nodes.n1, 'script_revision', { mode: 'professional_screenplay' });
assert(state.nodes.n1.params.embeddedCreativeAction?.status === 'preview', 'screenplay task must become preview');
assert(state.nodes.n1.params.embeddedCreativeAction?.creative_task?.phase === 'preview_ready', 'screenplay task must expose preview_ready phase');
assert(state.nodes.n1.content === originalText, 'screenplay preview must not mutate graph');
applyEmbeddedCreativeAction(store, 'n1');
assert(state.order.length === 1, 'screenplay apply must preserve stable node identity');
assert(state.nodes.n1.params.revisions[0].screenplay_candidate?.scenes?.length === 1, 'revision must store typed screenplay candidate');
assert(state.nodes.n1.content.includes('外景 - 花果山'), 'screenplay apply must use formatted screenplay projection');

await startEmbeddedCreativeAction(store, runtime, state.nodes.n1, 'shot_breakdown', { mode: 'dynamic_shot_breakdown' });
const beforeShotNodeCount = state.order.length;
applyEmbeddedCreativeAction(store, 'n1');
const roles = Object.values(state.nodes).map((node) => node.params?.nodeRole).filter(Boolean);
assert(state.order.length > beforeShotNodeCount, 'shot apply must create visible candidate nodes');
assert(roles.includes('m6_6_shot_sequence_candidate'), 'shot apply must create sequence candidate node');
assert(roles.includes('m6_6_scene_candidate'), 'shot apply must create scene candidate node');
assert(roles.filter((role) => role === 'm6_6_shot_candidate').length === 3, 'shot apply must create all dynamic shot nodes');
const edgeValues = Object.values(state.edges);
assert(edgeValues.some((edge) => edge.from === 'n1' && edge.relation_type === 'proposed'), 'source must connect to candidate sequence with proposed edge');
assert(edgeValues.filter((edge) => edge.relation_type === 'sequence').length >= 4, 'candidate scenes and shots must be visibly connected');

process.stdout.write(JSON.stringify({
  status: 'passed',
  flushCount,
  nodeCount: state.order.length,
  edgeCount: Object.keys(state.edges).length,
  screenplayRevisionCount: state.nodes.n1.params.revisions.length,
  candidateRoles: roles,
  companionCommandType: session.pendingCommand.command_type,
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
        "evaluator": "AFS_M6_6_VISIBLE_CREATIVE_TASKS_PROFESSIONAL_SCREENPLAY_GRAPH_ACTIONS",
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
        evidence[contract["scope"]] = {
            "path": contract["path"],
            "missing": missing,
            "forbidden_present": present,
        }
        if missing or present:
            details = []
            if missing:
                details.append(f"missing {missing}")
            if present:
                details.append(f"forbidden {present}")
            findings.append(_finding(contract, "; ".join(details)))
    return evidence


def _run_node_probe(root: Path, findings: list[dict[str, str]]) -> dict[str, Any]:
    result = subprocess.run(
        ["node", "--input-type=module", "-e", NODE_PROBE],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        findings.append({
            "severity": "P0",
            "scope": "node_probe",
            "issue": "M6.6 node/task graph behavior probe failed",
            "details": (result.stderr or result.stdout)[-1200:],
        })
        return {"status": "failed", "returncode": result.returncode, "stderr": result.stderr[-1200:]}
    return json.loads(result.stdout or "{}")


def _finding(contract: dict[str, Any], details: str) -> dict[str, str]:
    return {
        "severity": contract["severity"],
        "scope": contract["scope"],
        "issue": contract["issue"],
        "details": details,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    report = evaluate(args.root.resolve())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"{report['evaluator']} {report['summary']['status']} P0={report['summary']['p0']} P1={report['summary']['p1']} P2={report['summary']['p2']}")
        for finding in report["findings"]:
            print(f"- {finding['severity']} {finding['scope']}: {finding['details']}")
    return 0 if report["summary"]["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
