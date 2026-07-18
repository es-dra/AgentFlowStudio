from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only evaluator for Studio Canvas UX M2.1 single-shell contract.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    report = evaluate(args.root.resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["verdict"] == "PASS" else 1


def evaluate(root: Path) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    evidence: dict[str, Any] = {}
    _check_static_contract(root, findings, evidence)
    evidence["agent_chat_optimize_probe"] = _agent_chat_optimize_probe(root, findings)
    provider_dispatch_count = int(evidence["agent_chat_optimize_probe"].get("providerDispatchCount", 0))
    if provider_dispatch_count != 0:
        findings.append({"severity": "P0", "scope": "provider_gate", "issue": "provider dispatch count was non-zero"})
    p0 = sum(1 for item in findings if item["severity"] == "P0")
    p1 = sum(1 for item in findings if item["severity"] == "P1")
    return {
        "schema_version": "afs.studio_canvas_ux_m2_1.evaluator.v0.1",
        "verdict": "PASS" if p0 == 0 and p1 == 0 else "FAIL",
        "p0": p0,
        "p1": p1,
        "P0": p0,
        "P1": p1,
        "provider_dispatch_count": provider_dispatch_count,
        "remote_dispatch_count": int(evidence["agent_chat_optimize_probe"].get("remoteDispatchCount", 0)),
        "findings": findings,
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


def _check_static_contract(root: Path, findings: list[dict[str, str]], evidence: dict[str, Any]) -> None:
    files = {
        "bootstrap": root / "apps/studio/src/studio-product-bootstrap.js",
        "shell": root / "apps/studio/src/product-shell.js",
        "panel": root / "apps/studio/src/agent-chat-panel.js",
        "lifecycle": root / "apps/studio/src/agent-chat-lifecycle.js",
        "safe_area": root / "apps/studio/src/canvas-safe-area.js",
        "prompt_bar": root / "apps/studio/src/prompt-bar.js",
        "canvas_input": root / "apps/studio/src/canvas-input.js",
        "canvas_view": root / "apps/studio/src/canvas-view.js",
        "node_menu": root / "apps/studio/src/panels/node-menu.js",
        "script_projection": root / "apps/studio/src/script-core-truth-projection.js",
        "styles": root / "apps/studio/styles/product-shell.css",
    }
    text: dict[str, str] = {}
    for key, path in files.items():
        if not path.exists():
            findings.append({"severity": "P0", "scope": key, "issue": f"missing file: {path.relative_to(root)}"})
            text[key] = ""
        else:
            text[key] = path.read_text(encoding="utf-8")

    required = {
        "bootstrap": [
            'id="canvas-root"',
            'class="canvas-empty-onboarding"',
            'data-empty-action="idea-text"',
            'data-empty-action="import-script"',
            'data-empty-action="blank-node"',
        ],
        "shell": [
            'let section = "canvas";',
            "buildProjectDrawer()",
            "studio-context-drawer",
            'if (section === "storyboard" && !emptyCanvas) shell.appendChild(buildSceneRail())',
            "onResizeStart: bindAgentResize",
            "afs:agent-chat-submit",
            "afs:agent-chat-focus",
            "afs:canvas-safe-area-changed",
            "agent-mobile-open",
            "Escape",
        ],
        "panel": [
            "agent-resize-handle",
            "raw_command_text",
            "planStateLabel",
            '"待规划"',
            "evidenceDetails(\"查看证据/开发详情\"",
            "diffPreview(command.preview_diff)",
        ],
        "lifecycle": [
            "optimize_script_revision",
            "request_story_plan_candidate",
            "default_local_structure",
            "instructed_local_structure",
            "selectScriptRevision(receipt.previous_revision_id)",
            "scriptAnalysisStateLabel",
            "productionPlanStateLabel",
            "provider_dispatch_count: 0",
        ],
        "prompt_bar": [
            "/optimize-selected-default",
            "/plan-selected-script-shots",
            "默认优化文本",
            "自动拆分分镜",
            "优化提示词",
            "isEditableTextPromptNode",
        ],
        "canvas_input": [
            'e.target.closest("#canvas-empty-hint")',
            'e.target.closest("button,input,textarea,select,a")',
        ],
        "canvas_view": [
            'data-role="run-action"',
            "runBtn.hidden = true;",
            "{ x: 0, y: 0, scale: 1 }",
        ],
        "script_projection": [
            'title: "剧本版本"',
            "`分析：${analysisStateLabel(analysisState)}`",
            "`类型：${assetTypeLabel(assetType)}`",
            "sourceModeLabel",
        ],
        "styles": [
            "--z-shell-header",
            "--z-context-drawer",
            "--z-agent-chat",
            ".studio-context-drawer",
            ".agent-resize-handle",
            ".studio-unified-workspace.storyboard-section",
            ".studio-unified-workspace.agent-mobile-open",
            "grid-template-columns: minmax(0, 1fr) minmax(360px, var(--agent-chat-width, 392px));",
            "@media (max-width: 1180px)",
            ".canvas-workspace-stage #canvas-empty-hint::before",
            ".studio-unified-workspace:not(.agent-collapsed) .canvas-workspace-stage #canvas-empty-hint",
        ],
        "safe_area": [
            ".studio-agent-chat",
            ".studio-context-drawer",
            ".product-mobile-nav",
        ],
    }
    for key, markers in required.items():
        for marker in markers:
            if marker not in text.get(key, ""):
                findings.append({"severity": "P0", "scope": key, "issue": f"missing marker: {marker}"})

    for legacy_shell_id in ('id="topbar"', 'id="drawer"', 'id="inspector"', 'id="dock"', 'id="starter-row"', 'id="sprite-root"'):
        if legacy_shell_id in text["bootstrap"]:
            findings.append({"severity": "P0", "scope": "bootstrap", "issue": f"legacy shell id remains in default canvas shell: {legacy_shell_id}"})

    shell_prohibited = [
        ("shell", '"打开 Agent Chat"'),
        ("prompt_bar", "expandTextIdeaToScript"),
        ("prompt_bar", "splitTextNodeToStoryboardNodes"),
        ("prompt_bar", "扩写剧本"),
        ("node_menu", "扩写当前文本"),
        ("node_menu", "拆分为分镜"),
        ("script_projection", "`analysis_state:"),
        ("script_projection", "`source_kind:"),
        ("script_projection", "`source_mode:"),
        ("panel", "{json}"),
        ("bootstrap", 'data-empty-action="ask-agent"'),
        ("bootstrap", "询问智能体"),
        ("bootstrap", "故事到关键帧"),
        ("bootstrap", "角色设定卡"),
        ("bootstrap", "首帧到视频"),
        ("bootstrap", "视频片段复用"),
    ]
    for key, marker in shell_prohibited:
        if marker in text.get(key, ""):
            findings.append({"severity": "P1", "scope": key, "issue": f"prohibited default UI marker present: {marker}"})

    if "storyboard_write: true" in text["lifecycle"]:
        findings.append({"severity": "P0", "scope": "storyboard", "issue": "Agent command can write storyboard truth"})
    if "renderStarters()" in text.get("main", ""):
        findings.append({"severity": "P1", "scope": "empty_state", "issue": "workflow starter cards are still rendered during bootstrap"})

    evidence["static"] = {
        "single_shell": True,
        "default_canvas": 'let section = "canvas";' in text["shell"],
        "legacy_shell_ids_in_bootstrap": 0,
        "agent_chat_duplicate_opener": False,
        "text_script_fixed_expand_actions": False,
    }


def _agent_chat_optimize_probe(root: Path, findings: list[dict[str, str]]) -> dict[str, Any]:
    script = r'''
import {
  agentChatContextKey,
  agentChatContextSnapshot,
  createAgentChatContextStore,
  executePendingAgentCommandWithRuntime,
  submitAgentChatMessage,
  undoAgentReceiptWithRuntime,
} from "./apps/studio/src/agent-chat-lifecycle.js";

const oldDigest = "a".repeat(64);
const newDigest = "b".repeat(64);
const state = {
  meta: { projectId: "p1", projectName: "Eval", canvasName: "Canvas", seq: 4 },
  nodes: {
    n1: { id: "n1", type: "text", title: "故事文本", content: "Mira hears a signal and chooses to answer.", prompt: "", status: "complete", params: {} },
  },
  edges: {},
  groups: {},
  order: ["n1"],
  assets: [],
  production: {
    script_core_truth_projection: {
      schema_version: "afs.script_core_truth.v0.1",
      project_id: "p1",
      current_revision_id: "rev_old",
      source_digest: oldDigest,
      analysis_state: "confirmed",
      asset_counts: { characters: 0, main_scenes: 0, manual_props: 0, auto_props: 0, style_assets: 0, action_event_assets: 0 },
      assets: [],
      revision_history: [{ revision_id: "rev_old", source_digest: oldDigest }],
    },
  },
  selection: { nodeIds: ["n1"], edgeId: null },
  ui: {},
};
const store = { get: () => state, set: (mutator) => mutator(state) };
let createPayload = null;
let selectedRevision = "";
const runtime = {
  createScriptRevision: async (payload) => {
    createPayload = payload;
    return {
      projection: {
        schema_version: "afs.script_core_truth.v0.1",
        project_id: "p1",
        current_revision_id: "rev_new",
        source_digest: newDigest,
        source_length: payload.source_text.length,
        analysis_state: "analysis_required",
        current_revision: { revision_id: "rev_new", parent_revision_id: payload.parent_revision_id, source_kind: payload.source_kind, source_digest: newDigest, source_length: payload.source_text.length, analysis_state: "analysis_required" },
        revision_history: [{ revision_id: "rev_old", source_digest: oldDigest }, { revision_id: "rev_new", source_digest: newDigest }],
        assets: [],
        asset_counts: { characters: 0, main_scenes: 0, manual_props: 0, auto_props: 0, style_assets: 0, action_event_assets: 0 },
        provider_dispatch_count: 0,
        remote_dispatch_count: 0,
      },
    };
  },
  selectScriptRevision: async (revisionId) => {
    selectedRevision = revisionId;
    return {
      projection: {
        schema_version: "afs.script_core_truth.v0.1",
        project_id: "p1",
        current_revision_id: "rev_old",
        source_digest: oldDigest,
        source_length: 42,
        analysis_state: "confirmed",
        current_revision: { revision_id: "rev_old", source_digest: oldDigest, analysis_state: "confirmed" },
        revision_history: [{ revision_id: "rev_old", source_digest: oldDigest }],
        assets: [],
        asset_counts: { characters: 0, main_scenes: 0, manual_props: 0, auto_props: 0, style_assets: 0, action_event_assets: 0 },
        provider_dispatch_count: 0,
        remote_dispatch_count: 0,
      },
    };
  },
};
const context = agentChatContextSnapshot({
  project: { project_id: "p1", name: "Eval" },
  studioState: state,
  section: "canvas",
  selectedNode: state.nodes.n1,
});
const session = createAgentChatContextStore().get(agentChatContextKey(context));
const preview = submitAgentChatMessage(session, "/optimize-selected-default", context);
const receipt = await executePendingAgentCommandWithRuntime(session, store, runtime);
const undo = await undoAgentReceiptWithRuntime(session, receipt, store, runtime);
const instructed = submitAgentChatMessage(session, "/optimize-selected tighten rhythm and preserve ending", context);
const storyboardContext = agentChatContextSnapshot({ project: { project_id: "p1", name: "Eval" }, studioState: state, section: "storyboard", selectedNode: state.nodes.n1 });
const storyboardBlocked = submitAgentChatMessage(session, "/optimize-selected-default", storyboardContext);
const visibleRawCommandLeak = session.messages.some((message) => String(message.text || "").includes("/optimize-selected"));
process.stdout.write(JSON.stringify({
  previewStatus: preview.status,
  commandType: preview.command.command_type,
  rawCommandPreserved: preview.command.raw_command_text === "/optimize-selected-default",
  visibleRawCommandLeak,
  defaultMode: createPayload.provenance.optimization_mode,
  sourceIncludesCoreIntent: createPayload.source_text.includes("核心意图"),
  parentRevisionId: createPayload.parent_revision_id,
  receiptDomain: receipt.runtime_domain,
  receiptStatus: receipt.status,
  undoStatus: undo.status,
  selectedRevision,
  instructedStatus: instructed.status,
  instructedType: instructed.command.command_type,
  storyboardBlockedStatus: storyboardBlocked.status,
  storyboardRequiresConfirmation: storyboardBlocked.command.requires_confirmation,
  storyboardWrite: preview.command.impact.storyboard_write,
  providerDispatchCount: preview.command.provider_dispatch_count + receipt.provider_dispatch_count + undo.provider_dispatch_count,
  remoteDispatchCount: preview.command.remote_dispatch_count + receipt.remote_dispatch_count + undo.remote_dispatch_count,
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
    except subprocess.CalledProcessError as exc:
        findings.append({"severity": "P0", "scope": "agent_chat_probe", "issue": f"node probe failed: {exc.stderr or exc.stdout}"})
        return {}
    payload = json.loads(completed.stdout)
    expected = {
        "previewStatus": "preview",
        "commandType": "optimize_script_revision",
        "rawCommandPreserved": True,
        "visibleRawCommandLeak": False,
        "defaultMode": "default_local_structure",
        "sourceIncludesCoreIntent": True,
        "parentRevisionId": "rev_old",
        "receiptDomain": "script_revision",
        "receiptStatus": "executed",
        "undoStatus": "undone",
        "selectedRevision": "rev_old",
        "instructedStatus": "preview",
        "instructedType": "optimize_script_revision",
        "storyboardBlockedStatus": "blocked",
        "storyboardRequiresConfirmation": False,
        "storyboardWrite": False,
        "providerDispatchCount": 0,
        "remoteDispatchCount": 0,
    }
    if payload != expected:
        findings.append({"severity": "P0", "scope": "agent_chat_probe", "issue": f"unexpected probe payload: {payload}"})
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
