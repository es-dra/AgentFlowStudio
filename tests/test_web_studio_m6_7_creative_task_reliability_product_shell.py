from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_m6_7_split_label_and_node_running_feedback_contract() -> None:
    canvas = _read("apps/studio/src/canvas-view.js")
    prompt = _read("apps/studio/src/prompt-bar.js")
    lifecycle = _read("apps/studio/src/agent-chat-lifecycle.js")
    node_css = _read("apps/studio/styles/canvas-node-text.css")

    creator_sources = "\n".join([canvas, prompt, lifecycle])
    assert "自动拆分分镜" not in creator_sources
    assert "拆分分镜" in canvas
    assert "拆分分镜" in prompt
    assert 'title: "拆分分镜"' in lifecycle
    assert '"shot_breakdown"' in prompt
    assert '"dynamic_shot_breakdown"' in prompt

    assert "embedded-task-running" in canvas
    assert "dataset.embeddedTaskState" in canvas
    assert "dataset.embeddedTaskAction" in canvas
    assert "is-busy" in canvas
    assert "分镜任务生成中" in canvas

    assert ".node.embedded-task-running::after" in node_css
    assert "@keyframes embeddedTaskPerimeterRotate" in node_css
    assert "conic-gradient" in node_css
    assert "prefers-reduced-motion: reduce" in node_css


def test_m6_7_product_shell_project_account_menu_contract() -> None:
    shell = _read("apps/studio/src/product-shell.js")
    main = _read("apps/studio/src/main.js")
    css = _read("apps/studio/styles/product-shell.css")
    embedded = _read("apps/studio/src/embedded-creative-actions.js")

    assert 'src="./favicon.svg"' in shell
    assert "studio-brand-logo" in shell
    assert "studio-stage-button" not in shell
    assert "projectDrawerOpen = !projectDrawerOpen" not in shell

    assert "studio-project-switch-list" in shell
    assert "studio-project-search" in shell
    assert "studio-project-create" in shell
    assert "studio-project-settings" in shell
    assert "studio-project-delete" in shell
    assert "options.onDeleteProject?.(snapshot.project)" in shell
    assert "onDeleteProject" in main
    assert "projectController?.deleteProject(project)" in main
    assert "filterProjectMenu" in shell

    assert 'window.addEventListener("pointerdown"' in shell
    assert ".studio-project-context" in shell
    assert ".studio-account-context" in shell
    assert ".studio-help-context" in shell
    assert "accountMenuOpen = false" in shell
    assert "mobileAgentOpen || helpOpen || accountMenuOpen" in shell

    assert "studio-live-notice" not in shell
    assert "studio-header-notice" in shell
    assert "studio-header-notice" in css
    assert "studio-account-identity" in css
    assert "grid-template-columns: auto minmax(180px, 280px) 188px minmax(120px, 1fr) auto" in css
    assert "grid-template-columns: minmax(0, 1fr) auto" in css
    assert ".studio-header-actions .studio-account-context" in css
    assert ".studio-account-menu" in css and "position: fixed" in css

    open_task_handler = shell.split('window.addEventListener("afs:agent-chat-open-task"', 1)[1].split("});", 1)[0]
    assert "setAgentChatExpanded(true)" in open_task_handler
    assert "右侧任务区查看进度" in open_task_handler
    finished_task_handler = shell.split('window.addEventListener("afs:embedded-creative-task-finished"', 1)[1].split("});", 1)[0]
    assert "isNarrowAgentLayout()" in finished_task_handler
    assert "closeResponsiveAgentOverlay()" in finished_task_handler
    assert 'dispatchBrowserEvent("afs:embedded-creative-task-finished"' in embedded
    assert 'status: "cancelled"' in embedded
    assert 'status: "applied"' in embedded
