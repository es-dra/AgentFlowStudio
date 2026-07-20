from __future__ import annotations

import json
import subprocess
from pathlib import Path


STUDIO = Path("apps/studio")


def test_product_shell_is_chinese_first_and_hides_diagnostics_from_primary_flow() -> None:
    shell = (STUDIO / "src" / "product-shell.js").read_text(encoding="utf-8")
    i18n = (STUDIO / "src" / "i18n.js").read_text(encoding="utf-8")
    index = (STUDIO / "index.html").read_text(encoding="utf-8")

    for label in ("工作空间", "项目", "单集", "制作团队", "审核", "交付", "项目状态", "待主创决策", "剧组动态", "交付准备度"):
        assert label in i18n
    assert 'return localStorage.getItem(STORAGE_KEY) === "en" ? "en" : "zh-CN"' in i18n
    assert "runtime-status" not in shell
    assert "provider" not in shell.lower()
    assert "<pre" not in shell.lower()
    assert "raw_json" not in shell.lower()
    assert "新建项目" in shell
    assert "onCreateProject" in shell
    assert "? 40 : 0" in shell
    assert './styles/product-shell.css' in index


def test_mobile_shell_has_no_canvas_mount_and_no_horizontal_page_overflow_contract() -> None:
    bootstrap = (STUDIO / "src" / "studio-product-bootstrap.js").read_text(encoding="utf-8")
    styles = (STUDIO / "styles" / "product-shell.css").read_text(encoding="utf-8")

    assert 'const editorMounted = !window.matchMedia("(max-width: 760px)").matches;' in bootstrap
    assert "if (editorMounted) {" in bootstrap
    assert "@media (max-width: 760px)" in styles
    assert "html, body { max-width: 100%; overflow-x: clip; }" in styles
    assert "#studio-editor-shell { display: none !important; }" in styles
    assert "grid-template-columns: repeat(4, 1fr)" in styles
    assert "min-height: 52px" in styles


def test_product_shell_exposes_loading_empty_error_recovery_and_focus_states() -> None:
    main = (STUDIO / "src" / "main.js").read_text(encoding="utf-8")
    shell = (STUDIO / "src" / "product-shell.js").read_text(encoding="utf-8")
    styles = (STUDIO / "styles" / "product-shell.css").read_text(encoding="utf-8")

    for state in ('statePanel("loading")', 'statePanel("error")', 'statePanel("empty")'):
        assert state in shell
    assert 'document.getElementById("product-main")?.focus()' in shell
    assert 'setAttribute("aria-current"' in shell
    assert 'setAttribute("aria-label"' in shell
    assert "if (hasActiveProject())" in main
    assert "function hasActiveProject()" in main
    assert ":focus-visible" in styles
    assert "@media (prefers-reduced-motion: reduce)" in styles


def test_new_project_enters_unified_studio_and_empty_storyboard_has_no_demo_facts() -> None:
    controller = (STUDIO / "src" / "studio-project-controller.js").read_text(encoding="utf-8")
    shell = (STUDIO / "src" / "product-shell.js").read_text(encoding="utf-8")
    context = (STUDIO / "src" / "product-shell-context.js").read_text(encoding="utf-8")
    styles = (STUDIO / "styles" / "product-shell.css").read_text(encoding="utf-8")

    assert 'project_type: "studio_creator_authoring"' in controller
    assert "window.location.assign" not in controller
    assert "created?.episode_bootstrap?.workspace_entry?.href" not in controller
    assert 'uniqueProjectName("未命名项目", existingProjects)' in controller
    assert "AFS 内测项目" not in controller
    assert "exampleProjectName" not in controller

    assert 'let section = "canvas";' in shell
    assert "FALLBACK_SCENES" not in shell
    for forbidden in ("巷口", "雨巷", "老宅"):
        assert forbidden not in shell
    assert "storyboard-empty-state" in shell
    assert "0 场景 · 0 镜头" in shell
    assert "这个项目还没有场景、镜头、进度、决策、参考或示例素材。" in shell
    assert "故事板当前只读取画布确认后的事实；空项目不会自动创建示例分镜。" in shell
    assert "buildAgentChatPanel" in shell
    assert 'stage.dataset.canvasTarget = currentShot().nodeId || "empty-project"' in shell
    assert "return [];" in shell
    assert "scene-list-empty" in styles
    assert "先核对主体目标、连续性影响和确认边界" in context
    assert "雨夜层次" not in context


def test_canvas_is_mounted_inside_the_persistent_project_shell() -> None:
    main = (STUDIO / "src" / "main.js").read_text(encoding="utf-8")
    bootstrap = (STUDIO / "src" / "studio-product-bootstrap.js").read_text(encoding="utf-8")
    shell = (STUDIO / "src" / "product-shell.js").read_text(encoding="utf-8")
    styles = (STUDIO / "styles" / "product-shell.css").read_text(encoding="utf-8")

    assert 'editorParking.id = "studio-canvas-parking"' in bootstrap
    assert "getCanvasShell: () => editorShell" in main
    assert 'section === "canvas"' in shell
    assert 'viewButton("canvas", "画布")' in shell
    assert 'viewButton("storyboard", "故事板")' in shell
    assert 'section === "review"' not in shell
    assert 'params.get("stage")' not in main
    assert 'url.searchParams.set("stage", "canvas")' not in shell
    assert 'stage.appendChild(editor)' in shell
    assert 'stage.appendChild(live)' in shell
    assert "画布编辑请在桌面打开" in shell
    assert "showCanvas()" in shell
    assert 'setSection(next)' in shell
    assert 'root.dataset.view = section' in shell
    assert 'const active = section === key' in shell
    assert 'options.onSelectCanvasNode?.(currentShot().nodeId || "")' in shell
    assert 'state.ui.inspectorOpen = false' in main
    assert '.canvas-workspace-stage #studio-editor-shell' in styles
    assert '<aside id="drawer">' not in bootstrap
    assert '<header id="topbar">' not in bootstrap
    assert '<aside id="inspector">' not in bootstrap
    assert '<div id="corner-controls">' not in bootstrap
    assert '<div id="starter-row"' not in bootstrap
    assert 'if (document.getElementById("drawer")) renderDrawer' in main
    assert 'if (document.getElementById("inspector")) renderInspectorPanel' in main
    assert '.canvas-workspace-stage #drawer,' in styles
    assert '.canvas-workspace-stage #sprite-root' in styles
    assert '.canvas-mode #product-shell-root' not in styles
    assert 'app?.classList.remove("product-mode")' not in shell


def test_canvas_projection_has_single_studio_chrome_and_minimal_empty_state() -> None:
    bootstrap = (STUDIO / "src" / "studio-product-bootstrap.js").read_text(encoding="utf-8")
    shell = (STUDIO / "src" / "product-shell.js").read_text(encoding="utf-8")
    styles = (STUDIO / "styles" / "product-shell.css").read_text(encoding="utf-8")
    dock = (STUDIO / "src" / "panels" / "dock.js").read_text(encoding="utf-8")
    node_body = (STUDIO / "src" / "canvas-node-body.js").read_text(encoding="utf-8")
    keyboard = (STUDIO / "src" / "studio-keyboard.js").read_text(encoding="utf-8")

    assert 'class="canvas-empty-title">从一个想法开始制作' in bootstrap
    assert 'data-empty-action="idea-text"' in bootstrap
    assert 'data-empty-action="import-script"' in bootstrap
    assert 'data-empty-action="blank-node"' in bootstrap
    assert 'id="prompt-bar-layer"' in bootstrap
    assert 'id="corner-controls"' in bootstrap
    for forbidden in ("制作团队", "9 个专业岗位", "历史资产", "计划预览（已阻断）"):
        assert forbidden not in bootstrap

    assert 'canvasActive ? "canvas-section" : "storyboard-section"' in shell
    assert 'emptyCanvas ? "canvas-empty-project" : ""' in shell
    assert 'if (section === "storyboard" && !emptyCanvas) shell.appendChild(buildSceneRail())' in shell

    assert ".studio-unified-workspace.canvas-empty-project" in styles
    assert '<div id="starter-row"' not in bootstrap
    assert ".canvas-workspace-stage #topbar { display: none; }" in styles

    assert '"添加节点", "primary"' in dock
    assert '"适应画布"' in dock
    assert '"快捷键"' in dock
    for forbidden in ("我的工具箱", "素材库", "历史资产", "计划预览（已阻断）", "帮助"):
        assert forbidden not in dock

    assert "if (isEditableContentNode(node) && store)" in node_body
    assert "输入想法、剧本文字或参考说明" in node_body
    assert "function persistEditorValue(textarea, node, store)" in node_body
    assert "bindStableTextInputLifecycle(textarea, () => persistEditorValue(textarea, node, store))" in node_body
    stable_input = (STUDIO / "src" / "stable-text-input.js").read_text(encoding="utf-8")
    assert 'textarea.addEventListener("compositionend"' in stable_input
    assert 'textarea.addEventListener("blur"' in stable_input
    assert 'textarea.addEventListener("keydown"' in stable_input
    assert 'textarea.addEventListener("beforeinput"' in stable_input
    assert 'if (!document.getElementById("drawer")) return false' in keyboard


def test_review_delivery_legacy_entry_redirects_without_reintroducing_a_third_shell_tab() -> None:
    main = (STUDIO / "src" / "main.js").read_text(encoding="utf-8")
    shell = (STUDIO / "src" / "product-shell.js").read_text(encoding="utf-8")
    review_main = (STUDIO / "src" / "review-delivery-main.js").read_text(encoding="utf-8")
    styles = (STUDIO / "styles" / "product-shell.css").read_text(encoding="utf-8")

    assert 'viewButton("review", "审核交付")' not in shell
    assert "buildReviewWorkspace()" not in shell
    assert "buildGraphProductionSummary()" in shell
    assert "graphLifecycleList(\"审核记录\"" in shell
    assert "stageProductionGraphCommand" in shell
    assert "stageM6ScriptPlanCandidateCommand" in shell
    assert "buildAgentChatPanel" in shell
    assert 'current_stage: "正在切换项目"' not in shell
    assert "handleUnifiedReviewAction" not in main
    assert "submitDedicatedReviewDecision(runtime" not in main
    assert "submitDedicatedQualityApproval(runtime" not in main
    assert "submitDedicatedProductionExport(runtime" not in main
    assert "if (!redirectLegacyReviewEntry()) bootstrap()" in review_main
    assert 'new URL("/studio/", window.location.origin)' in review_main
    assert 'if (projectId) target.searchParams.set("project", projectId)' in review_main
    assert 'target.searchParams.set("stage", "review")' in review_main
    assert "if (!projectId) return false" not in review_main
    assert "window.location.replace(target.toString())" in review_main
    assert ".studio-review-workspace" not in styles
    assert ".studio-review-action-grid" not in styles


def test_scene_and_shot_selection_use_one_context_sync_path() -> None:
    shell = (STUDIO / "src" / "product-shell.js").read_text(encoding="utf-8")
    bootstrap = (STUDIO / "src" / "studio-product-bootstrap.js").read_text(encoding="utf-8")
    main = (STUDIO / "src" / "main.js").read_text(encoding="utf-8")

    assert 'let selection = { sceneIndex: 0, shotIndex: 0 }' in shell
    assert "selectContext(index, 0)" in shell
    assert "selectContext(selection.sceneIndex, index)" in shell
    assert 'options.onSelectCanvasNode?.(currentShot().nodeId || "")' in shell
    assert "function syncCanvasSelection()" in shell
    assert "productShell?.syncSelectionFromCanvasNode" not in main
    assert "stage.dataset.canvasTarget" in shell
    assert "shell.dataset.contextKey" in shell
    assert 'window.dispatchEvent(new CustomEvent("afs:studio-select-node"' in bootstrap
    assert "state.selection = { nodeIds: [], edgeId: null }" in bootstrap


def test_director_review_panel_does_not_fabricate_versions_or_recovery_actions() -> None:
    shell = (STUDIO / "src" / "product-shell.js").read_text(encoding="utf-8")

    assert '"当前候选", "v3"' not in shell
    assert '"已确认版本", "v2"' not in shell
    assert "恢复上一确认版本" not in shell
    assert "版本记录只随画布事实读取；恢复命令需要在 Agent Chat 中预览和确认。" in shell
    assert "安排返工" in shell
    assert "确认后新增返工任务，不覆盖原候选。" in shell


def test_project_only_episode_workspace_redirects_to_unified_studio() -> None:
    app = (STUDIO / "episode-workspace" / "app.mjs").read_text(encoding="utf-8")

    assert 'if (projectId && (!episodeId || !episodeVersionId)) {' in app
    assert 'new URL("/studio/", window.location.origin)' in app
    assert 'target.searchParams.set("project", projectId)' in app
    assert "window.location.replace(target.toString())" in app
    assert "projectId && episodeId && episodeVersionId" in app


def test_director_context_and_next_action_helpers_partition_and_target_real_work() -> None:
    script = r'''
import {
  createDirectorContextStore,
  findNextProductionTarget,
  productContextKey,
} from "./apps/studio/src/product-shell-context.js";

const store = createDirectorContextStore();
const firstKey = productContextKey({ projectId: "p1", sceneIndex: 0, shotIndex: 0, shot: { nodeId: "n1", title: "开场" } });
const secondKey = productContextKey({ projectId: "p1", sceneIndex: 1, shotIndex: 0, shot: { nodeId: "n2", title: "雨巷" } });
store.get(firstKey).conversations.push({ role: "user", text: "只属于开场" });
store.get(firstKey).proposalApplied = true;
const second = store.get(secondKey);
const target = findNextProductionTarget([
  { name: "开场", shots: [{ state: "ready", nodeId: "n1" }] },
  { name: "雨巷", shots: [{ state: "blocked", nodeId: "n2" }, { state: "draft", nodeId: "n3" }] },
], { sceneIndex: 0, shotIndex: 0 });
process.stdout.write(JSON.stringify({
  keysDiffer: firstKey !== secondKey,
  secondConversations: second.conversations.length,
  secondApplied: second.proposalApplied,
  target: { sceneIndex: target.sceneIndex, shotIndex: target.shotIndex, nodeId: target.shot.nodeId },
}));
'''
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(completed.stdout)

    assert payload == {
        "keysDiffer": True,
        "secondConversations": 0,
        "secondApplied": False,
        "target": {"sceneIndex": 1, "shotIndex": 0, "nodeId": "n2"},
    }


def test_cockpit_next_action_save_semantics_and_sparse_density_are_not_decorative() -> None:
    shell = (STUDIO / "src" / "product-shell.js").read_text(encoding="utf-8")
    styles = (STUDIO / "styles" / "product-shell.css").read_text(encoding="utf-8")

    assert 'next.addEventListener("click", activateNextAction)' in shell
    assert "findNextProductionTarget(sceneModel(), selection)" in shell
    assert "${actionLabel} 已绑定当前镜头。请发送命令获取预览，确认前不会写入画布。" in shell
    assert "syncCanvasSelection()" in shell
    assert "requestAnimationFrame(focusCurrentContext)" in shell
    assert 'const retry = node("button", "studio-save-retry", "重试")' in shell
    assert 'status.setAttribute("role", "status")' in shell
    assert 'retry.type = "button"' in shell
    assert 'retry.setAttribute("role", "status")' not in shell
    assert 'grid.classList.toggle("is-sparse", sparse)' in shell
    assert ".storyboard-content.is-sparse" in styles
    assert ".storyboard-shot-grid.is-sparse" in styles
