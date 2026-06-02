from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from apps.cli.main import app


PRODUCT_REGISTRY = Path("apps/cli/command_registry.py")
PRODUCTION_MEMORY_REGISTRY = Path("apps/cli/production_memory_command_registry.py")
SUPPORT_REGISTRY = Path("apps/cli/support_command_registry.py")


def test_product_command_registry_has_no_direct_provider_or_demo_registrations() -> None:
    source = PRODUCT_REGISTRY.read_text(encoding="utf-8")

    assert "kling_video_command" not in source
    assert "minimax_image_command" not in source
    assert "memory_demo_commands" not in source
    assert "kling-i2v-smoke" not in source
    assert "minimax-image-smoke" not in source
    assert "memory-advantage-demo-012" not in source
    assert "memory-advantage-demo-015" not in source
    assert "memory-video-pipeline-package" in source
    assert "register_production_memory_commands" in source
    assert "production-memory-loop-next-operator-start-packet" not in source
    assert "production-memory-loop-record-next-operator-start" not in source
    assert "production-memory-loop-record-next-operator-action-result" not in source
    assert "production-memory-loop-record-action-result-acceptance-feedback" not in source


def test_production_memory_registry_layers_public_and_hidden_commands() -> None:
    source = PRODUCTION_MEMORY_REGISTRY.read_text(encoding="utf-8")

    assert "asset-profile-readiness" in source
    assert "asset-test-package-run" in source
    assert "asset-feedback-record" in source
    assert "asset-profile-update-draft" in source
    assert "asset-profile-update-review" in source
    assert "asset-context-project" in source
    assert "asset-consistency-review" in source
    assert "production-memory-loop-asset-profile-readiness" in source
    assert "production-memory-loop-run-asset-test-package" in source
    assert "production-memory-loop-record-asset-feedback" in source
    assert "production-memory-loop-next-operator-start-packet" in source
    assert "production-memory-loop-record-next-operator-action-result" in source
    assert "production-memory-loop-record-action-result-acceptance-feedback" in source
    assert "_visible(app" in source
    assert "_hidden(app" in source
    assert "hidden=True" in source


def test_default_help_keeps_production_memory_product_surface_thin() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "asset-test-package-run" in result.output
    assert "asset-feedback-record" in result.output
    assert "asset-profile-update-review" in result.output
    assert "production-memory-loop-run-asset-test-package" not in result.output
    assert "production-memory-loop-record-asset-feedback" not in result.output
    assert "production-memory-loop-record-next-operator-action-result" not in result.output
    assert "production-memory-loop-record-action-result-acceptance-feedback" not in result.output
    assert "production-memory-loop-next-operator-start-packet" not in result.output


def test_hidden_production_memory_support_commands_remain_callable() -> None:
    result = CliRunner().invoke(app, ["production-memory-loop-record-next-operator-action-result", "--help"])

    assert result.exit_code == 0
    assert "recorded-at" in result.output


def test_support_command_registry_keeps_hidden_provider_and_demo_surface() -> None:
    source = SUPPORT_REGISTRY.read_text(encoding="utf-8")

    assert "hidden=True" in source
    assert "kling-i2v-smoke" in source
    assert "minimax-image-smoke" in source
    assert "memory-advantage-demo-012" in source
    assert "memory-advantage-demo-015" in source
