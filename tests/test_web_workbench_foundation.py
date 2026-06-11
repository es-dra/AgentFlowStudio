from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


WORKBENCH_ROOT = Path("apps/workbench")

ACTIVE_JS = [
    WORKBENCH_ROOT / "src" / "dom.js",
    WORKBENCH_ROOT / "src" / "runtime-client.js",
    WORKBENCH_ROOT / "src" / "state.js",
    WORKBENCH_ROOT / "src" / "workspace-config.js",
    WORKBENCH_ROOT / "src" / "prompt-optimizer-knowledge.js",
    WORKBENCH_ROOT / "src" / "prompt-optimizer-runtime.js",
    WORKBENCH_ROOT / "src" / "render.js",
    WORKBENCH_ROOT / "src" / "render-project-hub.js",
    WORKBENCH_ROOT / "src" / "render-studio-workspace.js",
    WORKBENCH_ROOT / "src" / "studio-workflow-graph.js",
    WORKBENCH_ROOT / "src" / "studio-node-actions.js",
    WORKBENCH_ROOT / "src" / "studio-node-control-state.js",
    WORKBENCH_ROOT / "src" / "render-studio-node-context.js",
    WORKBENCH_ROOT / "src" / "canvas-relation-focus.js",
    WORKBENCH_ROOT / "src" / "canvas-interaction-geometry.js",
    WORKBENCH_ROOT / "src" / "canvas-node-drag.js",
    WORKBENCH_ROOT / "src" / "canvas-selection-actions.js",
    WORKBENCH_ROOT / "src" / "canvas-viewport-actions.js",
    WORKBENCH_ROOT / "src" / "canvas-interactions.js",
    WORKBENCH_ROOT / "src" / "render-studio-panels.js",
    WORKBENCH_ROOT / "src" / "render-studio-canvas-topbar.js",
    WORKBENCH_ROOT / "src" / "render-studio-add-node-flow.js",
    WORKBENCH_ROOT / "src" / "render-studio-director-node-flow.js",
    WORKBENCH_ROOT / "src" / "render-studio-video-node-flow.js",
    WORKBENCH_ROOT / "src" / "render-studio-audio-node-flow.js",
    WORKBENCH_ROOT / "src" / "render-studio-starter-flows.js",
    WORKBENCH_ROOT / "src" / "render-studio-canvas-header.js",
    WORKBENCH_ROOT / "src" / "render-studio-toolbox.js",
    WORKBENCH_ROOT / "src" / "render-visible-assets.js",
    WORKBENCH_ROOT / "src" / "render-director-desk.js",
    WORKBENCH_ROOT / "src" / "director-setup-model.js",
    WORKBENCH_ROOT / "src" / "render-node-prompt.js",
    WORKBENCH_ROOT / "src" / "render-node-control-summary.js",
    WORKBENCH_ROOT / "src" / "render-prompt-optimizer.js",
    WORKBENCH_ROOT / "src" / "studio-experience-events.js",
    WORKBENCH_ROOT / "src" / "app-actions.js",
    WORKBENCH_ROOT / "src" / "app.js",
]

ACTIVE_UI_FILES = [
    WORKBENCH_ROOT / "index.html",
    WORKBENCH_ROOT / "styles-libtv-shell.css",
    WORKBENCH_ROOT / "styles-studio-canvas-experience.css",
    WORKBENCH_ROOT / "styles-studio-canvas-interactions.css",
    WORKBENCH_ROOT / "styles-studio-edge-toolbar.css",
    WORKBENCH_ROOT / "styles-studio-node-ports.css",
    WORKBENCH_ROOT / "styles-studio-node-transitions.css",
    WORKBENCH_ROOT / "styles-studio-node-controls.css",
    WORKBENCH_ROOT / "styles-studio-director-node-flow.css",
    WORKBENCH_ROOT / "styles-studio-mobile-node-workspace.css",
    WORKBENCH_ROOT / "styles-prompt-optimizer.css",
    WORKBENCH_ROOT / "src" / "workspace-config.js",
    WORKBENCH_ROOT / "src" / "render.js",
    WORKBENCH_ROOT / "src" / "render-project-hub.js",
    WORKBENCH_ROOT / "src" / "render-studio-workspace.js",
    WORKBENCH_ROOT / "src" / "studio-workflow-graph.js",
    WORKBENCH_ROOT / "src" / "studio-node-actions.js",
    WORKBENCH_ROOT / "src" / "studio-node-control-state.js",
    WORKBENCH_ROOT / "src" / "render-studio-node-context.js",
    WORKBENCH_ROOT / "src" / "canvas-relation-focus.js",
    WORKBENCH_ROOT / "src" / "canvas-interaction-geometry.js",
    WORKBENCH_ROOT / "src" / "canvas-node-drag.js",
    WORKBENCH_ROOT / "src" / "canvas-selection-actions.js",
    WORKBENCH_ROOT / "src" / "canvas-viewport-actions.js",
    WORKBENCH_ROOT / "src" / "canvas-interactions.js",
    WORKBENCH_ROOT / "src" / "render-studio-panels.js",
    WORKBENCH_ROOT / "src" / "render-studio-canvas-topbar.js",
    WORKBENCH_ROOT / "src" / "render-studio-add-node-flow.js",
    WORKBENCH_ROOT / "src" / "render-studio-director-node-flow.js",
    WORKBENCH_ROOT / "src" / "render-studio-video-node-flow.js",
    WORKBENCH_ROOT / "src" / "render-studio-audio-node-flow.js",
    WORKBENCH_ROOT / "src" / "render-studio-starter-flows.js",
    WORKBENCH_ROOT / "src" / "render-studio-canvas-header.js",
    WORKBENCH_ROOT / "src" / "render-studio-toolbox.js",
    WORKBENCH_ROOT / "src" / "render-visible-assets.js",
    WORKBENCH_ROOT / "src" / "render-director-desk.js",
    WORKBENCH_ROOT / "src" / "director-setup-model.js",
    WORKBENCH_ROOT / "src" / "render-node-prompt.js",
    WORKBENCH_ROOT / "src" / "render-node-control-summary.js",
    WORKBENCH_ROOT / "src" / "render-prompt-optimizer.js",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _active_source() -> str:
    return "\n".join(_read(path) for path in ACTIVE_UI_FILES)


def test_workbench_uses_libtv_product_shell_entrypoint() -> None:
    index = _read(WORKBENCH_ROOT / "index.html")
    workspace_config = _read(WORKBENCH_ROOT / "src" / "workspace-config.js")
    render = _read(WORKBENCH_ROOT / "src" / "render.js")

    assert '<html lang="zh-CN">' in index
    assert '<title>AgentFlow Studio</title>' in index
    assert '<link rel="stylesheet" href="./styles-libtv-shell.css" />' in index
    assert '<link rel="stylesheet" href="./styles-studio-canvas-interactions.css" />' in index
    assert '<link rel="stylesheet" href="./styles-studio-edge-toolbar.css" />' in index
    assert '<link rel="stylesheet" href="./styles-studio-node-ports.css" />' in index
    assert '<link rel="stylesheet" href="./styles-studio-node-transitions.css" />' in index
    assert '<link rel="stylesheet" href="./styles-studio-node-controls.css" />' in index
    assert '<link rel="stylesheet" href="./styles-studio-director-node-flow.css" />' in index
    assert '<link rel="stylesheet" href="./styles-studio-mobile-node-workspace.css" />' in index
    assert 'id: "Projects"' in workspace_config and 'label: "首页"' in workspace_config
    assert 'id: "Create"' in workspace_config and 'label: "创作画布"' in workspace_config
    assert 'id: "Assets"' in workspace_config and 'label: "资产库"' in workspace_config

    for removed in ["Style Memory", "Jobs", "Settings", "项目记忆", "任务中心", "诊断"]:
      assert removed not in workspace_config

    assert "renderProjectHub" in render
    assert "renderStudioWorkspace" in render
    assert "renderVisibleAssetsLibrary" in render
    for disconnected in ["renderCommandHub", "renderProductionBoard", "renderOperationsWorkspace", "renderStyleMemoryWorkspace", "renderDiagnosticPanel"]:
      assert disconnected not in render
    assert "debugMode" in render and "Alt+D" in render


def test_user_visible_product_path_has_no_engineering_terms_or_mojibake() -> None:
    source = _active_source()
    forbidden = [
        "项目记忆",
        "生成能力门",
        "Provider",
        "Runtime",
        "高级诊断",
        "任务中心",
        "连接与诊断",
        "CommandHub",
        "ProductionBoard",
        "本地规则降级",
        "权重",
        "候选记忆",
        "隐性资产",
        "鍓",
        "鎻",
        "鈻",
    ]
    for term in forbidden:
        assert term not in source

    for required in [
        "开始创作",
        "个人最近项目",
        "灵感创作",
        "模板入口",
        "创作画布",
        "资产库",
        "添加节点",
        "导演台",
        "提示词优化",
    ]:
        assert required in source


def test_prompt_optimizer_is_node_popover_only() -> None:
    node_prompt = _read(WORKBENCH_ROOT / "src" / "render-node-prompt.js")
    renderer = _read(WORKBENCH_ROOT / "src" / "render-prompt-optimizer.js")

    assert "node-prompt-box" in node_prompt
    assert "data-node-prompt-input" in node_prompt
    assert "optimize-current-prompt" in node_prompt
    assert "promptSurface" in node_prompt
    assert "prompt-optimizer-popover" in renderer
    assert "已按影视结构优化" in renderer
    assert "已结合当前项目风格" in renderer
    assert "已参考角色/场景设定" in renderer
    assert "已用本地优化" in renderer
    for hidden_copy in ["专业知识库 70%", "项目风格 20%", "个人偏好 10%", "权重", "Provider", "Runtime"]:
        assert hidden_copy not in renderer


def test_prompt_optimizer_uses_runtime_api_before_local_fallback() -> None:
    client = _read(WORKBENCH_ROOT / "src" / "runtime-client.js")
    actions = _read(WORKBENCH_ROOT / "src" / "app-actions.js")
    runtime = _read(WORKBENCH_ROOT / "src" / "prompt-optimizer-runtime.js")
    renderer = _read(WORKBENCH_ROOT / "src" / "render-prompt-optimizer.js")

    assert "optimizePrompt(projectId, payload)" in client
    assert "/prompt-optimizations" in client
    assert "await client().optimizePrompt" in actions
    assert "buildRuntimePromptOptimizationRequest" in actions
    assert 'optimization_source: "runtime_service"' in runtime
    assert 'optimization_source: "local_rule_fallback"' in runtime
    assert "已用本地优化" in renderer
    assert "Provider" not in renderer


def test_prompt_optimizer_maps_libtv_node_kinds_to_runtime_contract() -> None:
    actions = _read(WORKBENCH_ROOT / "src" / "app-actions.js")
    runtime = _read(WORKBENCH_ROOT / "src" / "prompt-optimizer-runtime.js")

    for marker in [
        'text: "text"',
        'image: "image"',
        'video: "video"',
        'audio: "audio"',
        'script: "script"',
        'director: "director"',
        'video_merge: "video_merge"',
    ]:
        assert marker in runtime
    assert "safeArtifactRefs" in runtime
    for forbidden in ["showOpenFilePicker", "FileReader", "readAsDataURL", "AFS_ALLOW_REMOTE_LLM"]:
        assert forbidden not in actions
        assert forbidden not in runtime


def test_active_workbench_files_stay_below_maintenance_threshold() -> None:
    for path in [WORKBENCH_ROOT / "styles-libtv-shell.css", *ACTIVE_JS]:
        assert len(_read(path).splitlines()) <= 300, path


def test_active_workbench_javascript_syntax() -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not available")
    for path in ACTIVE_JS:
        subprocess.run([node, "--check", str(path)], check=True)
