from __future__ import annotations

import json
import subprocess

from studio_static_helpers import STUDIO_ROOT, _styles


def test_keyframe_constraints_editor_is_wired_to_generation_panel_without_runtime_endpoint_changes() -> None:
    panel = (STUDIO_ROOT / "src" / "panels" / "generation-panel.js").read_text(encoding="utf-8")
    editor = (STUDIO_ROOT / "src" / "panels" / "keyframe-constraints-editor.js").read_text(encoding="utf-8")
    contract = (STUDIO_ROOT / "src" / "keyframe-constraints.js").read_text(encoding="utf-8")
    optimizer = (STUDIO_ROOT / "src" / "optimizer-contract.js").read_text(encoding="utf-8")
    styles = _styles()

    assert "const isKeyframeTarget = isKeyframeConstraintNode(current)" in panel
    assert "isKeyframeTarget ? createKeyframeConstraintsEditor(current)" in panel
    assert "keyframeConstraints?.applyToNode(target)" in panel
    assert "target.params.keyframeConstraints" in editor
    assert "target.params.temporaryAssetExclusions" in editor
    assert "syncTemporaryAssetExclusionsFromKeyframeConstraints(target)" in editor
    assert "addKeyframeConstraintRow" in contract
    assert "projectKeyframeConstraintsForProvider" in contract
    assert "containsUnsafeText" in contract
    assert "appendKeyframeConstraintPrompt" in optimizer
    assert "node.params?.keyframeConstraints" in optimizer
    assert ".keyframe-constraints-editor" in styles
    assert ".keyframe-constraint-row" in styles
    assert "/keyframe-generations" not in editor + contract
    assert "generateKeyframe" not in editor + contract


def test_keyframe_constraints_modules_stay_focused() -> None:
    contract = (STUDIO_ROOT / "src" / "keyframe-constraints.js").read_text(encoding="utf-8")
    editor = (STUDIO_ROOT / "src" / "panels" / "keyframe-constraints-editor.js").read_text(encoding="utf-8")

    assert len(contract.splitlines()) <= 300
    assert len(editor.splitlines()) <= 220


def test_fixed_asset_constraint_row_never_renders_internal_identity_or_provider_terms() -> None:
    script = r'''
import { createKeyframeConstraintsEditor } from "./apps/studio/src/panels/keyframe-constraints-editor.js";

function makeElement(tagName) {
  return {
    tagName: String(tagName || "").toUpperCase(),
    children: [], dataset: {}, style: {}, className: "", title: "",
    value: "", placeholder: "", textContent: "", innerHTML: "",
    appendChild(child) { this.children.push(child); return child; },
    append(...children) { this.children.push(...children); },
    replaceChildren(...children) { this.children = [...children]; },
    addEventListener() {},
  };
}
globalThis.document = { createElement: makeElement };

const node = {
  params: {
    visualAssets: [{ asset_id: "raw-asset-id-001", label: "林晚角色定稿", status: "fixed" }],
    keyframeConstraints: {
      rows: [{
        id: "fixed_1", section: "fixed_asset", projection: "audit_only", enabled: true,
        asset_id: "raw-asset-id-001", label: "林晚角色定稿",
        text: "Exclude fixed asset raw-asset-id-001 for the next run",
      }],
    },
  },
};
const editor = createKeyframeConstraintsEditor(node);
function visible(node) {
  const own = [node.textContent, String(node.innerHTML || "").replace(/<[^>]+>/g, " ")];
  if (["INPUT", "TEXTAREA"].includes(node.tagName)) own.push(node.value, node.placeholder, node.title);
  return [...own, ...node.children.map(visible)].filter(Boolean).join(" ").replace(/\s+/g, " ").trim();
}
process.stdout.write(JSON.stringify({ rendered: visible(editor.wrap) }));
'''
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    rendered = json.loads(completed.stdout)["rendered"]

    assert "本次生成不使用：林晚角色定稿" in rendered
    assert "参与生成" in rendered
    assert "仅作记录" in rendered
    assert "raw-asset-id-001" not in rendered
    assert "Provider" not in rendered
    assert "Audit" not in rendered
    assert "asset_id" not in rendered
