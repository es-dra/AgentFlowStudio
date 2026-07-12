from __future__ import annotations

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
