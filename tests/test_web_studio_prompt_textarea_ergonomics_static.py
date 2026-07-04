from studio_static_helpers import STUDIO_ROOT


def test_prompt_bar_textarea_can_resize_and_reclamp_to_viewport() -> None:
    prompt_bar = (STUDIO_ROOT / "src" / "prompt-bar.js").read_text(encoding="utf-8")
    prompt_position = (STUDIO_ROOT / "src" / "prompt-bar-position.js").read_text(encoding="utf-8")
    prompt_bar_css = (STUDIO_ROOT / "styles" / "prompt-bar.css").read_text(encoding="utf-8")

    assert "bindBarResizePositioning(bar, store, node.id)" in prompt_bar
    assert "new ResizeObserver" in prompt_position
    assert "positionBar(bar, state, fresh)" in prompt_position
    assert "openExpandEditor(store, runtime, node)" in prompt_bar
    assert 'node.type === "video" || node.type === "script") {' not in prompt_bar
    assert ".prompt-bar textarea" in prompt_bar_css
    assert "resize: vertical;" in prompt_bar_css
    assert "max-height: min(280px, calc(100vh - 210px));" in prompt_bar_css
    assert "padding-right: 28px;" in prompt_bar_css


def test_expanded_prompt_editor_preserves_node_values_for_long_prompts() -> None:
    expand_editor = (STUDIO_ROOT / "src" / "prompt-bar-expand.js").read_text(encoding="utf-8")
    prompt_bar_css = (STUDIO_ROOT / "styles" / "prompt-bar.css").read_text(encoding="utf-8")

    assert "expandedPromptValue(fresh)" in expand_editor
    assert "assetCardUserAdjustmentText(node)" in expand_editor
    assert "assetCardPromptPlaceholder" in expand_editor
    assert "node.content = value" in expand_editor
    assert "node.params.assetCardDraft.user_edited_text = value" in expand_editor
    assert "buildUserAssetCardRevisionState" in expand_editor
    assert ".prompt-expand textarea" in prompt_bar_css
    assert "min-height: 260px;" in prompt_bar_css
    assert "max-height: calc(100vh - 190px);" in prompt_bar_css


def test_generation_panel_prompt_textarea_is_resizable_without_hiding_actions() -> None:
    generation_css = (STUDIO_ROOT / "styles" / "studio-canvas-maturity.css").read_text(encoding="utf-8")
    media_css = (STUDIO_ROOT / "styles" / "studio-media-experience.css").read_text(encoding="utf-8")

    assert ".generation-field textarea" in generation_css
    assert "min-height: 132px;" in generation_css
    assert "max-height: min(360px, 46vh);" in generation_css
    assert "resize: vertical;" in generation_css
    assert "overflow: auto;" in generation_css
    assert ".generation-panel-backdrop .generation-panel" in media_css
    assert "max-height: calc(100vh - 140px);" in media_css
