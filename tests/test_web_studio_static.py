from __future__ import annotations

import json
import subprocess
from pathlib import Path

from studio_static_helpers import STUDIO_ROOT, _source, _styles

def test_studio_static_entrypoint_is_the_only_user_frontend() -> None:
    assert STUDIO_ROOT.exists()
    assert not Path("apps/workbench").exists()
    assert not Path("apps/web").exists()

    index = (STUDIO_ROOT / "index.html").read_text(encoding="utf-8")
    assert '<html lang="zh-CN">' in index
    assert '<meta charset="utf-8" />' in index
    assert "<title>AFS Studio 创作图谱</title>" in index
    assert '<link rel="icon" href="./favicon.svg" type="image/svg+xml" />' in index
    assert (STUDIO_ROOT / "favicon.svg").is_file()
    assert './src/main.js' in index
    assert './styles/director.css' in index
    assert "/workbench" not in index


def test_package_exposes_frontend_js_syntax_check() -> None:
    package = json.loads(Path("package.json").read_text(encoding="utf-8"))
    script = Path("tools/check-web-js.mjs")

    assert package["type"] == "module"
    assert package["scripts"]["check:studio-js"] == "node tools/check-web-js.mjs"
    assert script.is_file()
    source = script.read_text(encoding="utf-8")
    assert "apps/studio" in source
    assert "apps/site" in source
    assert "--check" in source


def test_studio_user_surface_has_no_common_mojibake_markers() -> None:
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for suffix in ("*.html", "*.css", "*.js", "*.md")
        for path in STUDIO_ROOT.rglob(suffix)
    )

    for marker in (
        "\u9352",  # common mojibake marker seen when 创 is corrupted
        "\u9422",  # common mojibake marker seen when 画 is corrupted
        "\u93bb",  # common mojibake marker seen when 提 is corrupted
        "\u93c8",  # common mojibake marker seen when 本 is corrupted
        "\ufffd",
    ):
        assert marker not in combined


def test_studio_disallows_native_blocking_dialogs_and_global_canvas_fallback() -> None:
    source = _source()
    store_source = (STUDIO_ROOT / "src" / "store.js").read_text(encoding="utf-8")
    persistence_source = (STUDIO_ROOT / "src" / "store-persistence.js").read_text(encoding="utf-8")
    state_source = (STUDIO_ROOT / "src" / "store-state.js").read_text(encoding="utf-8")
    env_example = Path(".env.example").read_text(encoding="utf-8")

    for forbidden in ("window.prompt(", "window.confirm(", "window.alert("):
        assert forbidden not in source
    assert '|| localStorage.getItem(STORAGE_KEY)' not in persistence_source
    assert '|| localStorage.getItem(LEGACY_STORAGE_KEY)' not in persistence_source
    assert "migrateLegacyCanvasStorage" in store_source
    assert "localStorage.removeItem(STORAGE_KEY)" in persistence_source
    assert "localStorage.removeItem(LEGACY_STORAGE_KEY)" in persistence_source
    assert 'return { source: "stale", projectId: targetProjectId }' in store_source
    assert 'return { source: "local_newer" }' in store_source
    assert "shouldKeepLocalOverRemote" in store_source
    assert "hasStudioMeta(remoteState)" in store_source
    assert 'next.type === "video" && next.params.lastVideoPreviewUrl' in state_source
    assert '!String(next.previewUrl).includes("/video-generations/")' in state_source
    main_source = (STUDIO_ROOT / "src" / "main.js").read_text(encoding="utf-8")
    project_controller = (STUDIO_ROOT / "src" / "studio-project-controller.js").read_text(encoding="utf-8")
    assert "syncCurrentProjectMetaFromSummaries" in project_controller
    assert "const currentId = runtime.projectId || store.get().meta.projectId;" in project_controller
    assert 'input.type = "text";' in project_controller
    assert "createProjectController" in main_source
    drawer_source = (STUDIO_ROOT / "src" / "panels" / "drawer.js").read_text(encoding="utf-8")
    assert "state.meta.projectId, state.meta.projectName, state.meta.canvasName" in drawer_source
    canvas_body_source = (STUDIO_ROOT / "src" / "canvas-node-body.js").read_text(encoding="utf-8")
    assert '!["image", "video"].includes(node.type)' in canvas_body_source
    prompt_bar_source = (STUDIO_ROOT / "src" / "prompt-bar.js").read_text(encoding="utf-8")
    assert 'node.type === "video" || node.type === "script"' in prompt_bar_source
    assert "AFS_ALLOW_REMOTE_IMAGE" in env_example


def test_studio_has_homepage_navigation_and_account_session_surface() -> None:
    runtime_client = (STUDIO_ROOT / "src" / "runtime-client.js").read_text(encoding="utf-8")
    auth_gate = (STUDIO_ROOT / "src" / "auth-gate.js").read_text(encoding="utf-8")
    overlay = (STUDIO_ROOT / "src" / "overlay.js").read_text(encoding="utf-8")
    topbar = (STUDIO_ROOT / "src" / "studio-topbar.js").read_text(encoding="utf-8")
    main = (STUDIO_ROOT / "src" / "main.js").read_text(encoding="utf-8")

    assert "AUTH_TOKEN_STORAGE_KEY" in runtime_client
    assert "Authorization" in runtime_client
    assert "authStatus()" in runtime_client
    assert "login(payload)" in runtime_client
    assert "register(payload)" in runtime_client
    assert "logout()" in runtime_client
    assert "saveStudioState(state, expectedVersion" in runtime_client
    assert "expected_version" in runtime_client
    assert "ensureAuthSession" in main
    assert "ensureAccessibleStartupProject" in main
    assert "closeOnOutside: false" in auth_gate
    assert "options.closeOnOutside === false" in overlay
    assert "site-home-btn" in topbar
    assert 'href = "/site/"' in topbar
    assert "onBeforeSiteHome" in topbar
    assert "store.flushRuntimeSave()" in main
    assert "首页" in topbar


def test_studio_state_save_tracks_runtime_version_conflicts() -> None:
    store_source = (STUDIO_ROOT / "src" / "store.js").read_text(encoding="utf-8")

    assert "runtimeStateVersion" in store_source
    assert "payload?.state_version" in store_source
    assert "saveStudioState(snapshotStudioState(state), runtimeStateVersion)" in store_source
    assert "error?.status === 409" in store_source
    assert "项目已在其他窗口更新" in store_source
    state_source = (STUDIO_ROOT / "src" / "store-state.js").read_text(encoding="utf-8")
    assert "sanitizeSnapshotForPersistence" in state_source
    assert "SAFE_PREVIEW_ROUTE_RE" in state_source
    assert "图像生成等待超时，已尝试从素材库恢复结果。" in state_source


def test_studio_user_surface_does_not_reintroduce_old_workbench_terms() -> None:
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for suffix in ("*.html", "*.css", "*.js")
        for path in STUDIO_ROOT.rglob(suffix)
    )
    for term in ("/workbench", "LibTV", "memory-workbench", "provider raw"):
        assert term not in combined


def test_studio_keeps_flow_native_canvas_controls() -> None:
    source = _source()

    for marker in (
        "openAddNodeMenu",
        "openOptimizer",
        "director",
        "prompt-optimizations",
        "keyframe-generations",
        "image-assets",
        "uploadNodeImage",
        "collectConnectedImageAssetRefs",
        "connected_reference_nodes",
        "candidate_previews",
        "reusable_image_assets",
        "mergeImageAssets",
        "node-preview-img",
        "node-preview-video",
        "resizeNodeForImagePreview",
        "previewAspectRatio",
        "has-image-preview",
        "startNodeGeneration",
        "studio-state",
        "loadStudioState",
        "saveStudioState",
        "createNode",
        "undo()",
        "redo()",
    ):
        assert marker in source


def test_studio_prompt_textareas_are_resizable_for_long_prompts() -> None:
    base = (STUDIO_ROOT / "styles" / "base.css").read_text(encoding="utf-8")
    prompt_bar = (STUDIO_ROOT / "styles" / "prompt-bar.css").read_text(encoding="utf-8")
    maturity = (STUDIO_ROOT / "styles" / "studio-canvas-maturity.css").read_text(encoding="utf-8")
    modals = (STUDIO_ROOT / "styles" / "modals.css").read_text(encoding="utf-8")

    assert "textarea { resize: none; }" not in base
    assert "textarea {\n  resize: vertical;\n  overflow: auto;\n}" in base
    assert ".prompt-bar textarea" in prompt_bar
    assert "max-height: min(320px, calc(100vh - 220px));" in prompt_bar
    assert "resize: vertical;" in prompt_bar
    assert ".prompt-expand {" in prompt_bar
    assert "resize: both;" in prompt_bar
    assert ".prompt-expand textarea" in prompt_bar
    assert ".node .node-content-editor" in maturity
    assert "max-height: min(460px, calc(100vh - 220px));" in maturity
    assert ".generation-field textarea" in maturity
    assert "max-height: min(420px, 60vh);" in maturity
    assert ".visual-asset-panel textarea" in modals
    assert "max-height: min(360px, 52vh);" in modals


def test_runtime_error_detail_objects_are_rendered_without_object_object() -> None:
    runtime_client = (STUDIO_ROOT / "src" / "runtime-client.js").read_text(encoding="utf-8")
    upload_actions = (STUDIO_ROOT / "src" / "node-upload-actions.js").read_text(encoding="utf-8")

    assert "runtimeErrorDetail(payload)" in runtime_client
    assert "Array.isArray(detail)" in runtime_client
    assert "runtimeValidationIssueText" in runtime_client
    assert 'typeof detail === "object"' in runtime_client
    assert "detail.reason" in runtime_client
    assert "detail.error" in runtime_client
    assert "detail.detail_code" in runtime_client
    assert 'field=${detail.field}' in runtime_client
    assert 'item !== "body"' in runtime_client
    assert "String(payload?.detail" not in runtime_client
    assert "[object Object]" not in runtime_client
    assert "图片上传失败" in upload_actions


def test_runtime_error_detail_object_and_validation_array_are_readable() -> None:
    code = r"""
import { createRuntimeClient } from './apps/studio/src/runtime-client.js';

const responses = [
  {
    ok: false,
    status: 422,
    text: async () => JSON.stringify({
      detail: {
        error: 'reference_image_upload_invalid_base64',
        detail_code: 'reference_image_upload_invalid_base64',
        field: 'data_base64',
        reason: '上传图片数据不是有效的 base64，请重新选择图片后再试。',
      },
    }),
  },
  {
    ok: false,
    status: 422,
    text: async () => JSON.stringify({
      detail: [{ loc: ['body', 'data_base64'], msg: 'Field required', type: 'missing' }],
    }),
  },
];
globalThis.window = {
  location: { protocol: 'http:', href: 'http://127.0.0.1:8796/studio/', hostname: '127.0.0.1', port: '8796' },
  localStorage: { getItem() { return ''; } },
};
globalThis.fetch = async () => responses.shift();
const runtime = createRuntimeClient('proj_error_detail');

for (const expected of ['reference_image_upload_invalid_base64', 'field=data_base64: Field required']) {
  try {
    await runtime.uploadImageAsset({
      node_id: 'image_1',
      filename: 'reference.png',
      mime_type: 'image/png',
      data_base64: '',
      role: 'reference_image',
      generated_at: '2026-07-05T10:00:00+08:00',
    });
  } catch (error) {
    if (String(error.message).includes('[object Object]')) throw new Error(error.message);
    if (!String(error.message).includes(expected)) throw new Error(`missing ${expected}: ${error.message}`);
    continue;
  }
  throw new Error('expected Runtime request to fail');
}
"""
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", code],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_studio_asset_context_workflow_is_single_canvas() -> None:
    source = _source()
    styles = _styles()

    for marker in (
        "buildContextSubgraph",
        "context_subgraph",
        "runtime_work_mode",
        "temporary_lock_overrides",
        "visual_asset_ids",
        "promoteVisualAsset",
        "visualAssets",
        "fix-visual-asset",
        "context_bundle",
        "lastContextBundle",
        "connectNamedAssetToTarget",
        "connect-named-asset",
        "temporary-unlock",
        "temporaryLockOverrides",
        "uniqueLockWarnings",
        "visual-asset-panel",
    ):
        assert marker in source
    for marker in ("opt-context-assets", "opt-inline-btn", "context-bundle-summary", "visual-asset-panel"):
        assert marker in styles
    assert "mode-tab asset_capture" not in source
    assert "mode-tab context_generate" not in source


def test_image_node_prompt_bar_keeps_only_model_optimize_and_generate_controls() -> None:
    source = _source()
    prompt_bar = (STUDIO_ROOT / "src" / "prompt-bar.js").read_text(encoding="utf-8")
    node_menu = (STUDIO_ROOT / "src" / "panels" / "node-menu.js").read_text(encoding="utf-8")
    node_actions = (STUDIO_ROOT / "src" / "node-actions.js").read_text(encoding="utf-8")

    assert "openModelPopover" in prompt_bar
    assert "openOptimizer" in prompt_bar
    assert "startNodeGeneration" in prompt_bar
    for removed in (
        "openImageSpecPopover",
        "openCameraPopover",
        "IMAGE_COUNTS",
        "IMAGE_QUALITY",
        "IMAGE_RESOLUTION",
        "IMAGE_RATIOS",
    ):
        assert removed not in prompt_bar
    assert "isRemoteVideoModel" in prompt_bar
    assert "pollNodeVideoGeneration" in prompt_bar
    assert "runPromptBarGeneration" in prompt_bar
    assert "声音" not in prompt_bar
    assert 'send.title = "继续轮询"' in prompt_bar
    assert "isPromptTextEditing" in prompt_bar
    assert '["TEXTAREA", "INPUT"].includes' in prompt_bar
    canvas_view = (STUDIO_ROOT / "src" / "canvas-view.js").read_text(encoding="utf-8")
    canvas_body = (STUDIO_ROOT / "src" / "canvas-node-body.js").read_text(encoding="utf-8")
    assert '!["image", "video"].includes(node.type)' in canvas_body
    assert "bar-cost" not in prompt_bar
    assert "当前版本仅图片节点支持真实生成" in prompt_bar
    assert "uploadNodeImage" in node_menu
    assert "setNodeVideoFrame" in node_menu
    assert "pollNodeVideoGeneration" in node_menu
    assert "openPositionNear" in (STUDIO_ROOT / "src" / "panels" / "add-node-menu.js").read_text(encoding="utf-8")
    assert "syncRunAction" in canvas_view
    assert 'dataset.action = "video-poll"' in canvas_view
    canvas_action_handler = (STUDIO_ROOT / "src" / "canvas-node-action-handler.js").read_text(encoding="utf-8")
    assert "pollNodeVideoGeneration" in canvas_action_handler
    keyframe_actions = (STUDIO_ROOT / "src" / "node-keyframe-actions.js").read_text(encoding="utf-8")
    video_actions = (STUDIO_ROOT / "src" / "node-video-actions.js").read_text(encoding="utf-8")
    generation_actions = node_actions + keyframe_actions + video_actions
    assert generation_actions.count("restoreCancelledGeneration(store, node.id, previousNodeState);") == 3
    assert generation_actions.count("await store.flushRuntimeSave?.();\n      return;") >= 2
    drawer_source = "".join(
        path.read_text(encoding="utf-8")
        for path in (
            STUDIO_ROOT / "src" / "panels" / "drawer.js",
            STUDIO_ROOT / "src" / "panels" / "drawer-assets.js",
            STUDIO_ROOT / "src" / "panels" / "drawer-asset-actions.js",
        )
    )
    assert 'asset.kind === "visual_asset" && asset.asset_type === "character"' in drawer_source
    assert 'asset.kind === "character_asset"' in drawer_source
    assert 'character_asset: "角色资产"' in drawer_source
    assert "asset.preview_url" in drawer_source
    assert "node.params.visualAssets" in drawer_source
    assert "visualAssetRef" in drawer_source
    assert "setVideoFrameFromAsset" in drawer_source
    assert "firstFrameImageAssetId" in drawer_source
    assert "设为首帧" in drawer_source
    assert "retireVisualAsset" in drawer_source
    assert "draftAssetCard" in source
    assert "asset-card-drafts" in source
    assert "applyRetiredAsset" in drawer_source
    assert "确认停用" in drawer_source
    assert "asset.runtime_status" in drawer_source
    assert "上传/替换参考图" in node_menu
    assert "VIDEO_MODES" not in prompt_bar
    assert "VIDEO_COUNTS" not in prompt_bar
    assert "mode-tabs" not in prompt_bar
