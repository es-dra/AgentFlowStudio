from __future__ import annotations

from studio_static_helpers import STUDIO_ROOT


def _read(path: str) -> str:
    return (STUDIO_ROOT / path).read_text(encoding="utf-8")


def test_overlay_modal_semantics_focus_trap_and_escape_gate_contract() -> None:
    overlay = _read("src/overlay.js")
    keyboard = _read("src/studio-keyboard.js")

    for marker in (
        'contentEl.setAttribute("role", "dialog")',
        'contentEl.setAttribute("aria-modal", "true")',
        "labelModal(contentEl, options)",
        "scheduleModalFocus(entry)",
        "trapModalFocus(event, entry)",
        'event.key === "Tab" && entry.options.isModal',
        'entry.close("escape")',
        'options.closeOnEscape === false',
        "afterEntryClosed(entry)",
        "previous?.isConnected",
    ):
        assert marker in overlay

    assert 'closeTop("escape")' in keyboard


def test_auth_status_failure_blocks_bootstrap_until_retry_confirms_status() -> None:
    auth_gate = _read("src/auth-gate.js")
    main = _read("src/main.js")

    assert "showAuthStatusBlocked(runtime, options, error)" in auth_gate
    assert "auth_status_unknown: true" in auth_gate
    assert "blocked: true" in auth_gate
    assert "已暂停项目加载、同步和 Runtime 写入" in auth_gate
    assert "重试账号状态检查" in auth_gate
    assert "closeOnOutside: false" in auth_gate
    assert "closeOnEscape: false" in auth_gate
    assert "return { auth_required: false, authenticated: false, user: null }" not in auth_gate

    blocked_guard = "if (authState?.auth_status_unknown || authState?.blocked) return;"
    assert blocked_guard in main
    assert main.index(blocked_guard) < main.index("await projectController.ensureAccessibleStartupProject()")


def test_product_shell_does_not_render_sign_out_for_anonymous_local_runtime() -> None:
    product_shell = _read("src/product-shell.js")

    assert "if (snapshot.authUser) {" in product_shell
    assert "actions.appendChild(language);" in product_shell
    assert "actions.appendChild(account);" in product_shell
    assert "actions.append(language, account);" not in product_shell


def test_accepted_plan_copy_keeps_non_claim_boundaries_explicit() -> None:
    panel = _read("src/panels/accepted-generation-plan-panel.js")

    for marker in (
        "not_package_complete",
        "not_provider_pass",
        "not_human_acceptance",
        "计划步骤门证据已记录，等待复核",
        "未声明包完成或人工接受",
        '["Provider 通过", "未声明"]',
        '["媒体 QA", "未声明"]',
        '["人工接受", "未声明"]',
        '["包完成", "未声明"]',
        '["产品就绪", "未声明"]',
        '["业务验证", "未声明"]',
    ):
        assert marker in panel

    assert "complete ·" not in panel
    assert '["Policy status", state.accepted ? "complete" : "needs_attention"]' not in panel
