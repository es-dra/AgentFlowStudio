from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only evaluator for Studio M1 canvas topology and Agent Chat.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    report = evaluate(args.root.resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["verdict"] == "PASS" else 1


def evaluate(root: Path) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    files = {
        "main": root / "apps" / "studio" / "src" / "main.js",
        "shell": root / "apps" / "studio" / "src" / "product-shell.js",
        "panel": root / "apps" / "studio" / "src" / "agent-chat-panel.js",
        "lifecycle": root / "apps" / "studio" / "src" / "agent-chat-lifecycle.js",
        "styles": root / "apps" / "studio" / "styles" / "product-shell.css",
    }
    text: dict[str, str] = {}
    for key, path in files.items():
        if not path.exists():
            findings.append({"severity": "P0", "scope": key, "issue": f"missing file: {path.relative_to(root)}"})
            text[key] = ""
            continue
        text[key] = path.read_text(encoding="utf-8")

    _check_topology(text, findings)
    _check_agent_contract(text, findings)
    _check_storyboard_boundary(text, findings)
    _check_fixture_pollution(text, findings)
    lifecycle_probe = _probe_lifecycle(root, findings)

    p0 = sum(1 for item in findings if item["severity"] == "P0")
    p1 = sum(1 for item in findings if item["severity"] == "P1")
    return {
        "schema_version": "afs.studio_m1_topology_agent_chat.evaluator.v0.1",
        "verdict": "PASS" if p0 == 0 and p1 == 0 else "FAIL",
        "p0": p0,
        "p1": p1,
        "findings": findings,
        "provider_dispatch_count": lifecycle_probe.get("providerDispatchCount", 0),
        "remote_dispatch_count": lifecycle_probe.get("remoteDispatchCount", 0),
        "evidence": {
            "default_section": "canvas",
            "right_panel": "studio-agent-chat",
            "storyboard_mode": "read_only_deferred",
            "lifecycle_probe": lifecycle_probe,
        },
        "non_claims": [
            "not_provider_smoke",
            "not_complete_auto_production_chain",
            "not_generated_media_quality",
            "not_human_acceptance",
            "not_business_validation",
        ],
    }


def _check_topology(text: dict[str, str], findings: list[dict[str, str]]) -> None:
    shell = text["shell"]
    styles = text["styles"]
    main = text["main"]
    if 'let section = "canvas";' not in shell:
        findings.append({"severity": "P0", "scope": "topology", "issue": "default section is not canvas"})
    if "productShell?.showCanvas();" not in main:
        findings.append({"severity": "P1", "scope": "topology", "issue": "studio home navigation does not return to canvas"})
    if _index(shell, 'viewButton("canvas"') > _index(shell, 'viewButton("storyboard"'):
        findings.append({"severity": "P1", "scope": "topology", "issue": "storyboard appears before canvas in the primary switch"})
    if "buildAgentChatPanel" not in shell or "buildAgentChat()" not in shell:
        findings.append({"severity": "P0", "scope": "topology", "issue": "right panel is not Agent Chat"})
    if "studio-agent-chat" not in styles:
        findings.append({"severity": "P0", "scope": "topology", "issue": "Agent Chat has no fixed panel style"})
    if "function buildDirector" in shell or "directorTab" in shell:
        findings.append({"severity": "P1", "scope": "topology", "issue": "old director status panel remains active"})


def _check_agent_contract(text: dict[str, str], findings: list[dict[str, str]]) -> None:
    combined = text["panel"] + "\n" + text["lifecycle"]
    required = [
        "createAgentChatContextStore",
        "agentChatContextSnapshot",
        "submitAgentChatMessage",
        "session.pendingCommand",
        "executePendingAgentCommand",
        "recordAgentCommandError",
        "undoAgentReceipt",
        "store.set((state) => executePendingAgentCommand(session, state))",
        "execution_receipt",
        "safe_error_recovery",
        "undo_receipt",
    ]
    for marker in required:
        if marker not in combined:
            findings.append({"severity": "P0", "scope": "agent_chat", "issue": f"missing lifecycle marker: {marker}"})
    static_fail_markers = ["runtime.spriteChat", "fixed success", "static success", "demo receipt"]
    for marker in static_fail_markers:
        if marker in combined:
            findings.append({"severity": "P0", "scope": "agent_chat", "issue": f"static chat marker present: {marker}"})


def _check_storyboard_boundary(text: dict[str, str], findings: list[dict[str, str]]) -> None:
    shell = text["shell"]
    lifecycle = text["lifecycle"]
    if 'storyboard_mode: "read_only_deferred"' not in lifecycle:
        findings.append({"severity": "P0", "scope": "storyboard", "issue": "Agent context does not declare read-only deferred storyboard"})
    if "storyboard_read_only" not in lifecycle:
        findings.append({"severity": "P1", "scope": "storyboard", "issue": "storyboard context is not separated from canvas context"})
    if "storyboard_write: true" in lifecycle:
        findings.append({"severity": "P0", "scope": "storyboard", "issue": "Agent command can write storyboard truth"})
    if "showStoryboard" not in shell:
        findings.append({"severity": "P1", "scope": "storyboard", "issue": "storyboard switch is not explicit"})


def _check_fixture_pollution(text: dict[str, str], findings: list[dict[str, str]]) -> None:
    combined = "\n".join(text.values())
    for marker in ["FALLBACK_SCENES", "巷口", "雨巷", "老宅", "4x15", "4×15", "keyword fallback"]:
        if marker in combined:
            findings.append({"severity": "P1", "scope": "pollution", "issue": f"forbidden fixture or fallback marker present: {marker}"})


def _probe_lifecycle(root: Path, findings: list[dict[str, str]]) -> dict[str, Any]:
    script = r'''
import {
  agentChatContextKey,
  agentChatContextSnapshot,
  createAgentChatContextStore,
  executePendingAgentCommand,
  submitAgentChatMessage,
  undoAgentReceipt,
} from "./apps/studio/src/agent-chat-lifecycle.js";

const state = {
  meta: { projectId: "p1", projectName: "Eval", canvasName: "Canvas", seq: 9 },
  nodes: { n1: { id: "n1", type: "text", title: "Original", status: "failed", params: {} } },
  edges: {},
  order: ["n1"],
  assets: [],
  production: {},
  selection: { nodeIds: ["n1"], edgeId: null },
};
const context = agentChatContextSnapshot({
  project: { project_id: "p1", name: "Eval" },
  studioState: state,
  section: "canvas",
  selectedNode: state.nodes.n1,
  currentShot: { nodeId: "n1", title: "Original" },
});
const session = createAgentChatContextStore().get(agentChatContextKey(context));
const preview = submitAgentChatMessage(session, "/rename-selected Renamed", context);
const receipt = executePendingAgentCommand(session, state);
const renamed = state.nodes.n1.title;
const undo = undoAgentReceipt(session, receipt, state);
const restored = state.nodes.n1.title;
const storyboardContext = agentChatContextSnapshot({
  project: { project_id: "p1", name: "Eval" },
  studioState: state,
  section: "storyboard",
  selectedNode: state.nodes.n1,
  currentShot: { nodeId: "n1", title: state.nodes.n1.title },
});
const storyboardSession = createAgentChatContextStore().get(agentChatContextKey(storyboardContext));
const storyboardBlocked = submitAgentChatMessage(storyboardSession, "/rename-selected Should Not Write", storyboardContext);
process.stdout.write(JSON.stringify({
  previewStatus: preview.status,
  commandType: preview.command.command_type,
  storyboardWrite: preview.command.impact.storyboard_write,
  providerDispatchCount: preview.command.provider_dispatch_count + receipt.provider_dispatch_count + undo.provider_dispatch_count,
  remoteDispatchCount: preview.command.remote_dispatch_count + receipt.remote_dispatch_count + undo.remote_dispatch_count,
  receiptStatus: receipt.status,
  undoStatus: undo.status,
  renamed,
  restored,
  storyboardBlockedStatus: storyboardBlocked.status,
  storyboardRequiresConfirmation: storyboardBlocked.command.requires_confirmation,
  messages: session.messages.length,
  receipts: session.receipts.length,
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
        findings.append({"severity": "P0", "scope": "agent_chat", "issue": f"lifecycle probe failed: {error}"})
        return {}

    expected = {
        "previewStatus": "preview",
        "commandType": "rename_selected_node",
        "storyboardWrite": False,
        "providerDispatchCount": 0,
        "remoteDispatchCount": 0,
        "receiptStatus": "executed",
        "undoStatus": "undone",
        "renamed": "Renamed",
        "restored": "Original",
        "storyboardBlockedStatus": "blocked",
        "storyboardRequiresConfirmation": False,
        "messages": 5,
        "receipts": 2,
    }
    for key, value in expected.items():
        if probe.get(key) != value:
            findings.append({"severity": "P0", "scope": "agent_chat", "issue": f"lifecycle probe mismatch: {key}"})
    return probe


def _index(value: str, marker: str) -> int:
    found = value.find(marker)
    return found if found >= 0 else sys.maxsize


if __name__ == "__main__":
    raise SystemExit(main())
