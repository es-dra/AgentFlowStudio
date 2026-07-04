import json
import subprocess

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
    prompt_bar = (STUDIO_ROOT / "src" / "prompt-bar.js").read_text(encoding="utf-8")
    prompt_bar_css = (STUDIO_ROOT / "styles" / "prompt-bar.css").read_text(encoding="utf-8")

    assert "expandedPromptValue(fresh)" in expand_editor
    assert "assetCardUserAdjustmentText(node)" in expand_editor
    assert "assetCardPromptPlaceholder" in expand_editor
    assert "node.content = value" in expand_editor
    assert "node.params.assetCardDraft.user_edited_text = value" in expand_editor
    assert "buildUserAssetCardRevisionState" in expand_editor
    assert "textarea.value = promptTextValue(node)" in prompt_bar
    assert "const expectedPrompt = promptTextValue(node)" in prompt_bar
    assert "if (!isPromptTextEditing(bar) && textarea.value !== expectedPrompt)" in prompt_bar
    assert ".prompt-expand textarea" in prompt_bar_css
    assert "min-height: 260px;" in prompt_bar_css
    assert "max-height: calc(100vh - 190px);" in prompt_bar_css


def test_expanded_prompt_state_syncs_to_inline_textarea_without_clobbering_inline_edit() -> None:
    script = r'''
globalThis.document = { activeElement: null };
const { syncPromptBarState } = await import("./apps/studio/src/prompt-bar.js");

function classListRecorder() {
  return { toggle: () => {} };
}

const textarea = {
  tagName: "TEXTAREA",
  value: "old inline prompt",
  placeholder: "",
  classList: classListRecorder(),
};
const bar = {
  classList: classListRecorder(),
  contains: (node) => node === textarea,
  querySelector: (selector) => selector === "textarea" ? textarea : null,
};

syncPromptBarState(bar, {
  id: "image_1",
  type: "image",
  prompt: "expanded editor saved value",
  content: "",
  params: { spec: { mode: "text_to_image" } },
});
const synced = textarea.value;

textarea.value = "active inline draft";
globalThis.document.activeElement = textarea;
syncPromptBarState(bar, {
  id: "image_1",
  type: "image",
  prompt: "external state value",
  content: "",
  params: { spec: { mode: "text_to_image" } },
});

process.stdout.write(JSON.stringify({
  synced,
  activeInlineValue: textarea.value,
}));
'''
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    result = json.loads(completed.stdout)

    assert result["synced"] == "expanded editor saved value"
    assert result["activeInlineValue"] == "active inline draft"


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
