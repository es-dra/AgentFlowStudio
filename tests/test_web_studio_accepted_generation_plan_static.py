from __future__ import annotations

from studio_static_helpers import STUDIO_ROOT, _styles


def test_studio_accepted_generation_plan_panel_defaults_to_blocked_preview() -> None:
    panel_path = STUDIO_ROOT / "src" / "panels" / "accepted-generation-plan-panel.js"
    panel = panel_path.read_text(encoding="utf-8")
    dock = (STUDIO_ROOT / "src" / "panels" / "dock.js").read_text(encoding="utf-8")
    runtime_client = (STUDIO_ROOT / "src" / "runtime-client.js").read_text(encoding="utf-8")
    styles = _styles()

    assert panel_path.is_file()
    assert 'const DEFAULT_FIXTURE_MODE = "default_unconfirmed"' in panel
    assert 'const CONFIRMED_FIXTURE_MODE = "confirmed_local_fixture"' in panel
    assert "load(DEFAULT_FIXTURE_MODE)" in panel
    assert "previewAcceptedGenerationPlanPacket" in panel
    assert "accepted-plan-status" in panel
    assert "生成计划预览（已阻断）" in panel
    assert "本地演示夹具仍处于阻断状态，未被接受" in panel
    assert "当前未接受" in panel
    assert "计划步骤门证据已记录，等待复核" in panel
    assert "source_mode" in panel
    assert "residual_blockers" in panel
    assert "non_claim_boundaries" in panel
    assert "not_package_complete" in panel
    assert "not_provider_pass" in panel
    assert "not_human_acceptance" in panel
    assert "not_provider_smoke" in panel
    assert "not_generated_media_qa" in panel
    assert "not_product_readiness" in panel
    assert "generateKeyframe" not in panel
    assert "generateVideo" not in panel
    assert "AFS_ALLOW_REMOTE" not in panel
    assert "provider_service_id" not in panel

    assert "openAcceptedGenerationPlanPanel" in dock
    assert "计划预览（已阻断）" in dock
    assert "Generation plan review" not in dock
    assert "previewAcceptedGenerationPlanPacket(payload = {})" in runtime_client
    assert 'payload: { fixture_mode: "default_unconfirmed", ...payload }' in runtime_client
    assert "accepted-generation-plan-packets/preview" in runtime_client
    assert "preview_accepted_generation_plan_packet" in runtime_client
    assert "accepted-generation-plan-modal" in styles
    assert "accepted-plan-mode.active" in styles


def test_studio_accepted_generation_plan_panel_requires_explicit_confirmed_fixture_control() -> None:
    panel = (STUDIO_ROOT / "src" / "panels" / "accepted-generation-plan-panel.js").read_text(encoding="utf-8")

    assert 'modeButton("默认包（已阻断）", DEFAULT_FIXTURE_MODE)' in panel
    assert 'modeButton("演示夹具（已阻断）", CONFIRMED_FIXTURE_MODE)' in panel
    assert "confirmedBtn.addEventListener" in panel
    assert "load(CONFIRMED_FIXTURE_MODE)" in panel
    assert "Accepted local plan packet" not in panel
    assert "前置条件未满足，已阻断" in panel
