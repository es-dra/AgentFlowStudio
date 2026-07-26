from __future__ import annotations

import json
import subprocess
from pathlib import Path


STUDIO_ROOT = Path("apps/studio")


def _read(path: str) -> str:
    return (STUDIO_ROOT / path).read_text(encoding="utf-8")


def _all_studio_source() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for suffix in ("*.html", "*.css", "*.js")
        for path in STUDIO_ROOT.rglob(suffix)
    )


def test_project_hub_surface_is_present_and_runtime_safe() -> None:
    assert (STUDIO_ROOT / "src" / "project-hub.js").is_file()
    source = _read("src/project-hub.js")
    combined = _all_studio_source()

    for marker in (
        "renderProjectHub",
        "project-hub",
        "PROJECT_MENU_EVENT",
        "project-menu",
        "project-menu-head",
        "project-menu-summary",
        "project-menu-actions",
        "project-menu-starters",
        "project-menu-list",
        "project-menu-row",
        "project-menu-links",
        "project-menu-project",
        "project-menu-note",
        "canvas-empty-title",
    ):
        assert marker in source or marker in combined
    for forbidden in ("api_key", "Authorization", "signed_url", "provider raw"):
        assert forbidden not in source.lower()


def test_workflow_starter_templates_create_multi_node_flows() -> None:
    assert (STUDIO_ROOT / "src" / "workflow-starters.js").is_file()
    source = _read("src/workflow-starters.js")

    for marker in (
        "WORKFLOW_STARTERS",
        "createWorkflowStarter",
        "story_to_keyframe",
        "character_asset_card",
        "scene_asset_card",
        "first_frame_to_video",
        "video_asset_revision",
        "connect(store",
    ):
        assert marker in source
    assert source.count("createNode(store") >= 8


def test_action_registry_drives_add_node_menu_taxonomy() -> None:
    assert (STUDIO_ROOT / "src" / "action-registry.js").is_file()
    registry = _read("src/action-registry.js")
    menu = _read("src/panels/add-node-menu.js")

    for marker in (
        "ACTION_GROUPS",
        "basic_nodes",
        "production_nodes",
        "asset_nodes",
        "resource_actions",
        "requires_gate",
        "createActionNode",
    ):
        assert marker in registry
    assert "ACTION_GROUPS" in menu
    assert "createActionNode" in menu


def test_navigator_inspector_and_job_center_modules_are_wired() -> None:
    for path in (
        "src/panels/project-navigator.js",
        "src/panels/inspector-panel.js",
        "src/panels/job-center.js",
        "src/panels/creation-process-panel.js",
    ):
        assert (STUDIO_ROOT / path).is_file()

    drawer = _read("src/panels/drawer.js")
    main = _read("src/main.js")
    combined = _all_studio_source()

    for marker in (
        "renderProjectNavigator",
        "renderInspectorPanel",
        "renderJobCenter",
        "inspector-actions",
        "inspector-section",
        "inspector-focus",
        "algorithm-console",
        "algorithm-disclosure",
        "afs:studio-open-generation-panel",
        "afs:studio-fix-visual-asset",
        "afs:video-asset-card-draft",
        "job-center",
        "creation-process",
        "inspector-panel",
    ):
        assert marker in drawer or marker in main or marker in combined


def test_desktop_frontend_wave_has_visual_tokens_and_project_noise_controls() -> None:
    combined = _all_studio_source()

    for marker in (
        "studio-home-btn",
        "project-menu",
        "project-menu-row",
        "project-menu-summary",
        "project-menu-links",
        "project-menu-starters",
        "workflow-starter-card",
        "drawer-section-count",
        "project-noise-toggle",
        "node-state-strip",
        "starter-card",
        "navigator-item",
        "inspector-section",
        "algorithm-console",
        "algorithm-step-track",
        "algorithm-call-summary",
        "algorithm-stat",
        "quick-create-panel",
        "quick-create-card",
        "studio-interactions.css",
        "data-tone",
        "node-preview-frame",
        "media-result-actions",
        "job-thumb",
        "studio-portal.css",
        "work-card",
        "creation-process-modal",
    ):
        assert marker in combined
    assert "@media (max-width: 520px)" in _read("styles/shell.css")


def test_frontend_maturity_wave_has_canvas_generation_and_work_actions() -> None:
    for path in (
        "src/canvas-context-menu.js",
        "src/panels/generation-panel.js",
        "styles/studio-canvas-maturity.css",
        "styles/studio-media-experience.css",
    ):
        assert (STUDIO_ROOT / path).is_file()

    combined = _all_studio_source()
    for marker in (
        "bindCanvasContextMenu",
        "canvas-context-menu",
        "openGenerationPanel",
        "generation-panel",
        "node-content-editor",
        "generation-progress-layer",
        "port-hovering",
        "inspector-actions",
        "rich-empty",
        "candidate-grid",
        "candidate-card",
        "continue-generate",
        "afs:studio-open-generation-panel",
        "afs:studio-open-creation-process",
        "afs:studio-fix-visual-asset",
        "studio-canvas-maturity.css",
        "studio-media-experience.css",
    ):
        assert marker in combined
    assert "node-context-toolbar" not in combined
    for retired_action in ("继续生成", "保存素材", "整理卡片", "看过程"):
        assert retired_action not in _read("src/canvas-view.js")

    assert "window.prompt(" not in combined
    assert "provider raw" not in combined.lower()


def test_generation_panel_uses_node_specific_settings_profiles() -> None:
    panel = _read("src/panels/generation-panel.js")
    profile = _read("src/panels/generation-panel-profile.js")
    specs = _read("src/presets/specs.js")

    assert "generationProfile(current)" in panel
    assert "applyGenerationProfileSettings(target, profile, controls)" in panel
    assert "profile.runsGeneration !== false" in panel
    assert "generation-setting-${profile.kind}" in panel
    assert "generation-setting-count-${profile.fields.length}" in panel
    assert "保存设置" in panel
    assert "target.params.spec = { ...(target.params.spec || {}), ratio: controls.ratio?.value || \"9:16\", count }" in profile
    assert "target.params.candidateCount = count" in profile
    assert "const VIDEO_MOTIONS = [" in profile
    assert "{ key: \"motion\", label: \"镜头运动 / 运镜\", kind: \"select\", options: VIDEO_MOTIONS" in profile
    assert "target.params.motion = controls.motion?.value || \"固定机位\"" in profile
    assert "缓慢推进" in profile
    assert "轻微环绕主体" in profile
    assert "target.params.candidateCount = 1" not in profile
    assert "videoCandidateCount" not in profile
    assert "当前视频模型仅支持生成 1 个候选视频" not in profile
    assert "镜头 / 构图" not in profile
    assert "视图 / 构图要求" not in profile
    assert "文本规划节点当前不直接使用生成设置" in profile
    assert "导演台请使用专门的导演台面板编辑" in profile
    assert "当前视频片段复用还没有接入真实生成设置" in profile
    for unused_setting in (
        "scriptPlanning",
        "directorGenerationSettings",
        "videoReuseSettings",
        "scriptStyle",
        "cameraLanguage",
        "reuseSource",
    ):
        assert unused_setting not in profile
    assert "VIDEO_DURATIONS" in specs
    assert "\"2s\"" in specs or "length: 15" in specs
    assert "\"7s\"" in specs or "length: 15" in specs
    assert "\"14s\"" in specs or "length: 15" in specs
    assert "VIDEO_RESOLUTIONS = [\"480P\", \"720P\"]" in specs
    assert "VIDEO_RATIOS = [\"16:9\", \"9:16\", \"1:1\", \"4:3\", \"3:4\"]" in specs
    assert "20s" not in specs
    assert "1080P" not in specs
    assert "VIDEO_RATIOS = [\"16:9\", \"9:16\", \"1:1\", \"4:3\", \"21:9\"]" not in specs
    styles = _read("styles/studio-media-experience.css")
    assert ".generation-panel .generation-setting-image" in styles
    assert "grid-template-columns: minmax(0, 1fr) 112px" in styles
    assert ".generation-setting-grid .generation-field:last-child" not in styles


def test_video_duration_options_cover_one_to_fifteen_seconds() -> None:
    script = r'''
import { VIDEO_DURATIONS } from "./apps/studio/src/presets/specs.js";
import { generationProfile } from "./apps/studio/src/panels/generation-panel-profile.js";

const profile = generationProfile({ type: "video", params: {} });
const durationField = profile.fields.find((field) => field.key === "duration");
process.stdout.write(JSON.stringify({
  durations: VIDEO_DURATIONS,
  profileOptions: durationField?.options || [],
}));
'''
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
    )
    payload = json.loads(completed.stdout)

    expected = [f"{second}s" for second in range(1, 16)]
    assert payload["durations"] == expected
    assert payload["profileOptions"] == expected
    for representative in ("2s", "7s", "14s"):
        assert representative in payload["durations"]


def test_generation_projection_is_split_from_node_actions() -> None:
    for path in (
        "src/node-generation-progress.js",
        "src/node-generation-results.js",
        "src/node-generation-guards.js",
        "src/node-generation-context.js",
        "src/node-keyframe-actions.js",
        "src/node-video-actions.js",
    ):
        assert (STUDIO_ROOT / path).is_file()

    node_actions = _read("src/node-actions.js")
    keyframe_actions = _read("src/node-keyframe-actions.js")
    video_actions = _read("src/node-video-actions.js")
    progress = _read("src/node-generation-progress.js")
    results = _read("src/node-generation-results.js")
    guards = _read("src/node-generation-guards.js")

    assert len(node_actions.splitlines()) <= 260
    assert len(keyframe_actions.splitlines()) <= 180
    assert len(video_actions.splitlines()) <= 300
    assert "setSubmittingGenerationState" in keyframe_actions + video_actions
    assert "updateNodeGenerationState" in keyframe_actions + video_actions
    assert "function startRemoteKeyframeGeneration" not in node_actions
    assert "function applyKeyframeResponse" not in node_actions
    assert "startRemoteKeyframeGeneration" in keyframe_actions
    assert "applyKeyframeResponse" in keyframe_actions
    assert "function startRemoteVideoGeneration" not in node_actions
    assert "function applyVideoResponse" not in node_actions
    assert "startRemoteVideoGeneration" in video_actions
    assert "applyVideoResponse" in video_actions
    assert "STATUS_PROGRESS" in progress
    assert "candidate_previews" in progress
    assert "candidatePreviewUrls" in progress
    assert "terminalProgress" in progress
    assert "progressPercent" in progress
    assert "function keyframeResultText" in results
    assert "function videoResultText" in results
    assert "function showCarryConfirmModal" in guards
    assert "function keyframeResultText" not in node_actions
    assert "function showCarryConfirmModal" not in node_actions


def test_keyframe_progress_uses_percentage_long_polling_without_timeout_failure() -> None:
    startup = _read("src/studio-startup-project.js")
    progress = _read("src/node-generation-progress.js")
    keyframe_actions = _read("src/node-keyframe-actions.js")
    project_controller = _read("src/studio-project-controller.js")
    body = _read("src/canvas-node-body.js")

    assert "ACTIVE_STATUS_PROGRESS" in progress
    assert "submitted: 8" in progress
    assert "running: 58" in progress
    assert "mode: progressMode(response, status)" in progress
    assert "MAX_KEYFRAME_POLL_ATTEMPTS" in keyframe_actions
    assert "markKeyframeStillProcessing" in keyframe_actions
    assert "refreshPendingKeyframeGenerations" in keyframe_actions
    assert "activeKeyframePolls" in keyframe_actions
    assert "startBackgroundKeyframePolling" in keyframe_actions
    assert "void startBackgroundKeyframePolling" in keyframe_actions
    assert "runtime.pollKeyframe(jobId)" in keyframe_actions
    assert "refreshPendingKeyframeGenerations(store, runtimeClient, { isCurrent: current })" in startup
    assert "onProjectReady?.(runtimeClient, { isCurrent: transitionCurrent })" in project_controller
    assert "throw new Error(`图片生成仍在处理中" not in keyframe_actions
    assert "const isIndeterminate = !progress || progress?.percent == null" in body
    assert "`${progress.percent}%`" in body
    assert "生成中" in body


def test_runtime_media_urls_are_normalized_only_at_render_boundaries() -> None:
    runtime_client = _read("src/runtime-client.js")
    runtime_media_source = _read("src/runtime-media-source.js")
    keyframe_actions = _read("src/node-keyframe-actions.js")
    upload_actions = _read("src/node-upload-actions.js")
    result_view = _read("src/node-result-view.js")
    job_center = _read("src/panels/job-center.js")
    drawer_assets = _read("src/panels/drawer-assets.js")
    runtime_asset_sync = _read("src/runtime-asset-sync.js")

    assert "runtimeMediaUrl" in runtime_client
    assert "runtimeMediaUrl(value)" in runtime_media_source
    assert "Authorization: `Bearer ${token}`" in runtime_media_source
    assert 'url.pathname.startsWith("/projects/")' in runtime_media_source
    assert "toMediaUrl(value)" in runtime_client
    assert "setRuntimeMediaSource" in result_view
    assert "setRuntimeMediaSource" in job_center
    assert "setRuntimeMediaSource" in drawer_assets
    assert "runtimeMediaUrl" not in keyframe_actions
    assert "runtimeMediaUrl" not in upload_actions
    assert "runtimeMediaUrl" not in runtime_asset_sync


def test_runtime_media_source_caches_authorized_project_media_between_rerenders() -> None:
    runtime_media_source = _read("src/runtime-media-source.js")

    assert "mediaBlobCache" in runtime_media_source
    assert "cachedAuthorizedMediaUrl" in runtime_media_source
    assert "syncAuthorizedMediaSession(token)" in runtime_media_source
    assert "mediaAuthGeneration" in runtime_media_source
    assert "current?.authGeneration === mediaAuthGeneration" in runtime_media_source
    assert "for (const objectUrl of mediaBlobCache.values()) URL.revokeObjectURL(objectUrl)" in runtime_media_source
    assert "element.dataset.afsMediaRaw" in runtime_media_source
    assert "assignCachedMediaUrl" in runtime_media_source
    assert "revokeRuntimeMediaSource(element, { keepCached: true })" in runtime_media_source


def test_runtime_media_source_does_not_fallback_to_anonymous_project_media() -> None:
    runtime_media_source = _read("src/runtime-media-source.js")

    assert "failAuthorizedMediaLoad(element)" in runtime_media_source
    assert 'element.removeAttribute("src")' in runtime_media_source
    assert 'typeof element.dispatchEvent === "function"' in runtime_media_source
    assert 'queueMicrotask(() => element.dispatchEvent(new Event("error")))' in runtime_media_source
    assert "if (element.dataset.afsMediaRequest === requestId) assignMediaUrl(element, url)" not in runtime_media_source


def test_runtime_media_source_fails_without_auth_and_reauthorizes_after_session_change() -> None:
    runtime_media_source = (STUDIO_ROOT / "src" / "runtime-media-source.js").resolve()
    script = f"""
      let token = "";
      const requests = [];
      let objectOrdinal = 0;
      const revoked = [];
      let releaseRace = null;
      globalThis.window = {{
        location: {{ protocol: "http:", href: "http://127.0.0.1:8790/studio/" }},
        localStorage: {{ getItem: () => token }},
      }};
      globalThis.fetch = async (url, options) => {{
        requests.push({{ url, authorization: options?.headers?.Authorization || "" }});
        if (url.includes("asset-race")) {{
          await new Promise((resolve) => {{ releaseRace = resolve; }});
        }}
        return {{ ok: true, blob: async () => new Blob(["candidate"]) }};
      }};
      URL.createObjectURL = () => `blob:test-${{++objectOrdinal}}`;
      URL.revokeObjectURL = (value) => revoked.push(value);
      const {{ setRuntimeMediaSource }} = await import({json.dumps(runtime_media_source.as_uri())});
      const element = () => ({{
        tagName: "IMG",
        dataset: {{}},
        src: "",
        errors: 0,
        removeAttribute(name) {{ if (name === "src") this.src = ""; }},
        dispatchEvent(event) {{ if (event.type === "error") this.errors += 1; }},
      }});
      const route = "/projects/project-a/image-assets/asset-a/preview";
      const noAuth = element();
      const noAuthResult = await setRuntimeMediaSource(noAuth, route);
      token = "session-a";
      const first = element();
      await setRuntimeMediaSource(first, route);
      const sameSession = element();
      await setRuntimeMediaSource(sameSession, route);
      token = "session-b";
      await setRuntimeMediaSource(first, route);
      token = "";
      await setRuntimeMediaSource(first, route);
      token = "session-a";
      const race = element();
      const raceResultPromise = setRuntimeMediaSource(
        race,
        "/projects/project-a/image-assets/asset-race/preview",
      );
      await new Promise((resolve) => setTimeout(resolve, 0));
      token = "session-b";
      releaseRace();
      const raceResult = await raceResultPromise;
      console.log(JSON.stringify({{
        noAuthResult,
        noAuthErrors: noAuth.errors,
        requests,
        changedElementErrors: first.errors,
        changedElementSrc: first.src,
        sameSessionSrc: sameSession.src,
        raceResult,
        raceErrors: race.errors,
        raceSrc: race.src,
        revoked,
      }}));
    """
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)

    assert result["noAuthResult"] == ""
    assert result["noAuthErrors"] == 1
    assert [item["authorization"] for item in result["requests"]] == [
        "Bearer session-a",
        "Bearer session-b",
        "Bearer session-a",
    ]
    assert result["sameSessionSrc"] == "blob:test-1"
    assert result["changedElementErrors"] == 1
    assert result["changedElementSrc"] == ""
    assert result["raceResult"] == ""
    assert result["raceErrors"] == 1
    assert result["raceSrc"] == ""
    assert result["revoked"] == ["blob:test-1", "blob:test-2", "blob:test-3"]


def test_completed_image_nodes_use_full_bleed_preview_body() -> None:
    canvas_body = _read("src/canvas-node-body.js")
    result_view = _read("src/node-result-view.js")
    styles = _read("styles/node-result.css")

    assert "imageCompleteBody(node)" in canvas_body
    assert "node.type === \"image\" && node.previewUrl" in canvas_body
    assert 'classList.add("full-bleed-image")' in result_view
    assert ".node.type-image .node-body.full-bleed-media" in styles
    assert ".node-result.full-bleed-image .node-preview-overlay" in styles


def test_asset_drawer_has_app_context_menu_and_image_delete_action() -> None:
    drawer_assets = _read("src/panels/drawer-assets.js")
    drawer_actions = _read("src/panels/drawer-asset-actions.js")
    runtime_client = _read("src/runtime-client.js")
    asset_detail = _read("src/panels/asset-detail-popover.js")
    styles = _read("styles/assets.css")

    for marker in (
        "asset-context-menu",
        "contextmenu",
        "openAssetContextMenu",
        "删除图片素材",
        "preventDefault",
    ):
        assert marker in drawer_assets
    assert "thumb.addEventListener(\"contextmenu\"" in drawer_assets
    assert "deleteImageAsset(assetId)" in runtime_client
    assert "deleteImageAssetFromDrawer" in drawer_actions
    assert "removeImageAssetFromStore" in drawer_actions
    assert "visualAssetIdFromRef" in asset_detail
    assert 'typeof assetRef === "object"' in asset_detail
    assert "runtime.getVisualAsset(visualAssetId)" in asset_detail
    assert 'asset.kind === "image_reference"' in asset_detail
    assert ".asset-context-menu" in styles


def test_sprite_input_keeps_dom_while_typing_and_filters_prompt_leaks() -> None:
    sprite_widget = _read("src/sprite-widget.js")
    sprite_context = _read("src/sprite-chat-context.js")

    assert "spriteInputShouldKeepDom(root)" in sprite_widget
    assert "document.activeElement === input" in sprite_widget
    assert "isSpriteInputComposing()" in sprite_widget
    assert "SPRITE_PROMPT_LEAK_FRAGMENTS" in sprite_context
    assert "你是团团" in sprite_context
    assert "第一人称" in sprite_context


def test_canvas_fit_uses_visible_safe_area_not_full_root_bounds() -> None:
    assert (STUDIO_ROOT / "src" / "canvas-safe-area.js").is_file()
    safe_area = _read("src/canvas-safe-area.js")
    keyboard = _read("src/studio-keyboard.js")
    context_menu = _read("src/canvas-context-menu.js")
    dock = _read("src/panels/dock.js")
    navigator = _read("src/panels/project-navigator.js")
    drawer_actions = _read("src/panels/drawer-asset-actions.js")
    geometry = _read("src/geometry.js")

    for marker in ("#drawer", "#inspector", "#topbar", "#dock", "fitVisibleCanvasViewport", "visibleCanvasCenter"):
      assert marker in safe_area
    assert "safeArea = {}" in geometry
    assert "fitVisibleCanvasViewport(s.nodes)" in keyboard
    assert "visibleCanvasCenter()" in keyboard
    assert "fitVisibleCanvasViewport(s.nodes)" in context_menu
    assert "fitVisibleCanvasViewport(s.nodes)" in dock
    assert "visibleCanvasCenter()" in dock
    assert "visibleCanvasCenter()" in navigator
    assert "panViewportToNode(s.viewport, node)" in navigator
    assert "fitVisibleCanvasViewport({ [node.id]: node }, 220)" in drawer_actions


def test_frontend_wave_sources_have_no_common_mojibake_fragments() -> None:
    combined = _all_studio_source()

    for marker in (
        "鍒",
        "鐢",
        "鏈",
        "鑺",
        "璧",
        "閸",
        "鏆",
        "娌",
        "鎿",
        "�",
    ):
        assert marker not in combined
