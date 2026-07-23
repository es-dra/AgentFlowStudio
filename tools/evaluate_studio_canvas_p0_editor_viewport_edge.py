from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only evaluator for Studio Canvas P0 editor/viewport/edge contract.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    report = evaluate(args.root.resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["verdict"] == "PASS" else 1


def evaluate(root: Path) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    evidence: dict[str, Any] = {}
    _check_static_contract(root, findings, evidence)
    evidence["fit_probe"] = _node_probe(root, FIT_PROBE, findings, "fit_probe")
    evidence["port_geometry_probe"] = _node_probe(root, PORT_GEOMETRY_PROBE, findings, "port_geometry_probe")
    evidence["agent_split_probe"] = _node_probe(root, AGENT_SPLIT_PROBE, findings, "agent_split_probe")
    expected_split = {
        "commandType": "start_embedded_creative_action",
        "previewStatus": "preview",
        "title": "拆分分镜",
        "actionType": "shot_breakdown",
        "mode": "dynamic_shot_breakdown",
        "rawPreserved": True,
        "visibleRawLeak": False,
        "relation": "visible_candidate_storyboard_subgraph",
        "storyboardWrite": True,
        "providerDispatchCount": 0,
        "remoteDispatchCount": 0,
    }
    if evidence["agent_split_probe"] and evidence["agent_split_probe"] != expected_split:
        findings.append({
            "severity": "P0",
            "scope": "agent_split_probe",
            "issue": f"unexpected embedded shot breakdown payload: {evidence['agent_split_probe']}",
        })
    provider_dispatch_count = int(evidence["agent_split_probe"].get("providerDispatchCount", 0) or 0)
    if provider_dispatch_count != 0:
      findings.append({"severity": "P0", "scope": "provider_gate", "issue": "provider dispatch count was non-zero"})
    p0 = sum(1 for item in findings if item["severity"] == "P0")
    p1 = sum(1 for item in findings if item["severity"] == "P1")
    return {
        "schema_version": "afs.studio_canvas_p0_editor_viewport_edge.evaluator.v0.1",
        "verdict": "PASS" if p0 == 0 and p1 == 0 else "FAIL",
        "p0": p0,
        "p1": p1,
        "P0": p0,
        "P1": p1,
        "provider_dispatch_count": provider_dispatch_count,
        "remote_dispatch_count": int(evidence["agent_split_probe"].get("remoteDispatchCount", 0) or 0),
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
        "main": root / "apps/studio/src/main.js",
        "shell": root / "apps/studio/src/product-shell.js",
        "store": root / "apps/studio/src/store.js",
        "store_notify": root / "apps/studio/src/store-notify-meta.js",
        "store_persistence": root / "apps/studio/src/store-runtime-persistence-controller.js",
        "stable_input": root / "apps/studio/src/stable-text-input.js",
        "node_body": root / "apps/studio/src/canvas-node-body.js",
        "prompt_bar": root / "apps/studio/src/prompt-bar.js",
        "lifecycle": root / "apps/studio/src/agent-chat-lifecycle.js",
        "geometry": root / "apps/studio/src/geometry.js",
        "port_geometry": root / "apps/studio/src/interaction/port-geometry.js",
        "canvas_input": root / "apps/studio/src/canvas-input.js",
        "add_node_menu": root / "apps/studio/src/panels/add-node-menu.js",
        "safe_area": root / "apps/studio/src/canvas-safe-area.js",
        "edges": root / "apps/studio/src/canvas-edges.js",
        "edge_state": root / "apps/studio/src/canvas-edge-state.js",
        "edge_css": root / "apps/studio/styles/canvas-edges.css",
        "edge_motion_css": root / "apps/studio/styles/canvas-edge-motion.css",
    }
    text: dict[str, str] = {}
    for key, path in files.items():
        if not path.exists():
            findings.append({"severity": "P0", "scope": key, "issue": f"missing file: {path.relative_to(root)}"})
            text[key] = ""
        else:
            text[key] = path.read_text(encoding="utf-8")

    required = {
        "store": ["mergeNotifyMeta"],
        "store_notify": ["renderScopes", "emptyNotifyMeta", "mergeNotifyMeta"],
        "store_persistence": ['renderScope: "save-status"'],
        "main": ["shouldRenderProductShell", "isCanvasTextEditingActive", "canvas-local-edit"],
        "shell": ["options.render === false", "syncSaveStatusElement"],
        "stable_input": ["compositionstart", "compositionupdate", "compositionend", "beforeinput", "paste", "inputType"],
        "node_body": ["bindStableTextInputLifecycle", 'renderScope: "canvas-local-edit"'],
        "prompt_bar": ["bindStableTextInputLifecycle", 'renderScope: "canvas-local-edit"', "拆分分镜", "startEmbeddedCreativeAction", '"shot_breakdown"'],
        "lifecycle": ["request_story_plan_candidate", "planning_required", "需要智能规划器提交结构化候选"],
        "geometry": ["clientToCanvasPoint", "clientToWorld"],
        "port_geometry": ["nodePortCanvasCenter", "clientToCanvasPoint"],
        "canvas_input": ["clientToCanvasPoint", "clientToWorld"],
        "add_node_menu": ["coordinateSpace", "canvasPointFromMenuPoint", "clientPointFromMenuPoint"],
        "safe_area": ["isVisibleCanvasFrameUsable", "return null", 'coordinateSpace: "canvas"'],
        "edges": ["edgeLifecycleState"],
        "edge_state": ["edge-failed", "edge-paused"],
        "edge_css": ["edge-failed", "edge-paused"],
        "edge_motion_css": ["prefers-reduced-motion: reduce"],
    }
    for key, markers in required.items():
        for marker in markers:
            if marker not in text.get(key, ""):
                findings.append({"severity": "P0", "scope": key, "issue": f"missing marker: {marker}"})

    prohibited = {
        "prompt_bar": ["expandTextIdeaToScript", "splitTextNodeToStoryboardNodes", "structuredShotFromSegment", "扩写剧本"],
        "lifecycle": ["structuredShotFromSegment", "KNOWN_", "_HINTS"],
        "edges": ["touchesSelection"],
    }
    for key, markers in prohibited.items():
        for marker in markers:
            if marker in text.get(key, ""):
                findings.append({"severity": "P1", "scope": key, "issue": f"prohibited production marker present: {marker}"})

    evidence["static"] = {
        "stable_canvas_text_input": not any(item["scope"] in {"main", "shell", "store", "stable_input", "node_body", "prompt_bar"} for item in findings),
        "auto_split_entry_restored": "拆分分镜" in text["prompt_bar"] and "startEmbeddedCreativeAction" in text["prompt_bar"],
        "legacy_split_not_bound": "splitTextNodeToStoryboardNodes" not in text["prompt_bar"],
        "edge_selection_spark_removed": "touchesSelection" not in text["edges"],
    }


def _node_probe(root: Path, script: str, findings: list[dict[str, str]], scope: str) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        return json.loads(completed.stdout)
    except Exception as exc:  # pragma: no cover - surfaced as evaluator evidence
        findings.append({"severity": "P0", "scope": scope, "issue": str(exc)})
        return {}


FIT_PROBE = r'''
import { fitVisibleCanvasViewport } from "./apps/studio/src/canvas-safe-area.js";
const root = { hidden: false, isConnected: true, getBoundingClientRect: () => ({ left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 }) };
globalThis.window = { getComputedStyle: () => ({ display: "block", visibility: "visible", pointerEvents: "auto" }) };
globalThis.document = { getElementById: (id) => id === "canvas-root" ? root : null, querySelector: () => null };
const fit = fitVisibleCanvasViewport({ n1: { x: 0, y: 0, w: 280, h: 280 } });
process.stdout.write(JSON.stringify({ hiddenFitWritesViewport: fit !== null }));
'''


PORT_GEOMETRY_PROBE = r'''
import { nodeFramePortWorldPoint } from "./apps/studio/src/interaction/port-geometry.js";
const rootRect = { left: 11, top: 68, right: 1011, bottom: 768, width: 1000, height: 700 };
const portRect = { left: 491, top: 330, width: 20, height: 20 };
const portEl = { getBoundingClientRect: () => portRect };
const nodeEl = { dataset: { nodeId: "n1" }, querySelector: () => portEl };
globalThis.document = {
  getElementById: (id) => id === "canvas-root" ? { getBoundingClientRect: () => rootRect } : null,
  querySelectorAll: () => [nodeEl],
};
const viewport = { x: 30, y: 40, scale: 0.5 };
const node = { id: "n1", x: 100, y: 200, w: 300, h: 280 };
const point = nodeFramePortWorldPoint(node, "out", viewport);
const expectedX = ((portRect.left + portRect.width / 2 - rootRect.left) - viewport.x) / viewport.scale;
const expectedY = ((portRect.top + portRect.height / 2 - rootRect.top) - viewport.y) / viewport.scale;
process.stdout.write(JSON.stringify({ point, expectedX, expectedY, aligned: Math.abs(point.x - expectedX) < 0.001 && Math.abs(point.y - expectedY) < 0.001 }));
'''


AGENT_SPLIT_PROBE = r'''
import {
  agentChatContextKey,
  createAgentChatContextStore,
  submitAgentChatMessage,
} from "./apps/studio/src/agent-chat-lifecycle.js";
const context = {
  project_id: "p0",
  project_name: "P0",
  section: "canvas",
  script_revision_id: "rev_current",
  script_source_digest: "a".repeat(64),
  selected_node_id: "n1",
  selected_node_type: "script",
  selected_node_title: "剧本文本",
  selected_node_text: "林夏走进车站，听见十年后的留言。",
  counts: { nodes: 1, scenes: 0, shots: 0 },
};
const session = createAgentChatContextStore().get(agentChatContextKey(context));
const preview = submitAgentChatMessage(session, "/plan-selected-script-shots", context);
const visibleRawLeak = session.messages.some((message) => String(message.text || "").includes("/plan-selected-script-shots"));
process.stdout.write(JSON.stringify({
  commandType: preview.command.command_type,
  previewStatus: preview.status,
  title: preview.command.title,
  actionType: preview.command.action_type,
  mode: preview.command.mode,
  rawPreserved: preview.command.raw_command_text === "/plan-selected-script-shots",
  visibleRawLeak,
  relation: preview.command.impact.relation,
  storyboardWrite: preview.command.impact.storyboard_write,
  providerDispatchCount: preview.command.provider_dispatch_count,
  remoteDispatchCount: preview.command.remote_dispatch_count
}));
'''


if __name__ == "__main__":
    raise SystemExit(main())
