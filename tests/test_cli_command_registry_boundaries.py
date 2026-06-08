from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from apps.cli.main import app


PRODUCT_REGISTRY = Path("apps/cli/command_registry.py")
PRODUCTION_MEMORY_REGISTRY = Path("apps/cli/production_memory_command_registry.py")
SUPPORT_REGISTRY = Path("apps/cli/support_command_registry.py")
VISIBLE_PRODUCT_COMMANDS = (
    "version",
    "analyze-hooks",
    "generate-scripts",
    "run-workflow",
    "draft-plan",
    "generate-clip-plans",
    "mock-slice",
    "slice-real",
    "ffmpeg-check",
    "inspect-run",
    "review-run",
    "package-report",
    "delivery-readiness",
    "alpha-smoke",
    "memory-video-pipeline-plan",
    "memory-video-pipeline-review",
    "memory-video-pipeline-observe",
    "memory-video-pipeline-present",
    "memory-video-pipeline-package",
    "memory-evidence-reuse-review",
    "memory-loop-validate",
    "memory-loop-run-no-provider",
    "asset-profile-readiness",
    "asset-test-package-run",
    "asset-feedback-record",
    "asset-profile-update-draft",
    "asset-profile-update-review",
    "asset-context-project",
    "asset-consistency-review",
    "asset-test-run-harness",
    "asset-two-round-validate",
    "asset-provider-validation-gate",
    "runtime-service",
    "runtime-service-openapi-export",
)


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
    assert "runtime-service" in source
    assert "runtime-service-openapi-export" in source
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
    assert "asset-test-run-harness" in source
    assert "asset-two-round-validate" in source
    assert "asset-provider-validation-gate" in source
    assert "production-memory-loop-asset-profile-readiness" in source
    assert "production-memory-loop-run-asset-test-package" in source
    assert "production-memory-loop-record-asset-feedback" in source
    assert "production-memory-loop-run-real-asset-test-harness" in source
    assert "production-memory-loop-two-round-context-runtime-validation" in source
    assert "production-memory-loop-provider-validation-gate" in source
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
    assert "asset-test-run-harness" in result.output
    assert "asset-two-round-validate" in result.output
    assert "asset-provider-validation-gate" in result.output
    assert "asset-feedback-record" in result.output
    assert "asset-profile-update-review" in result.output
    assert "production-memory-loop-run-asset-test-package" not in result.output
    assert "production-memory-loop-record-asset-feedback" not in result.output
    assert "production-memory-loop-record-next-operator-action-result" not in result.output
    assert "production-memory-loop-record-action-result-acceptance-feedback" not in result.output
    assert "production-memory-loop-next-operator-start-packet" not in result.output
    assert "web-bridge" not in result.output


def test_visible_product_command_help_avoids_terminal_truncation_glyphs() -> None:
    runner = CliRunner()

    for command in VISIBLE_PRODUCT_COMMANDS:
        result = runner.invoke(app, [command, "--help"])
        assert result.exit_code == 0, command
        assert "\u2026" not in result.output, command
        assert "\ufffd" not in result.output, command


def test_runtime_service_openapi_export_command_writes_frontend_schema(tmp_path) -> None:
    output_path = tmp_path / "afs-runtime-service.openapi.json"

    result = CliRunner().invoke(
        app,
        [
            "runtime-service-openapi-export",
            "--output",
            str(output_path),
            "--runtime-root",
            str(tmp_path / "runtime"),
        ],
    )
    schema = json.loads(output_path.read_text(encoding="utf-8"))

    assert result.exit_code == 0
    assert schema["info"]["version"] == "0.2.0"
    assert "/projects" in schema["paths"]
    assert "/projects/import" in schema["paths"]
    assert "api_key" not in json.dumps(schema, ensure_ascii=False).lower()


def test_hidden_production_memory_support_commands_remain_callable() -> None:
    result = CliRunner().invoke(app, ["production-memory-loop-record-next-operator-action-result", "--help"])

    assert result.exit_code == 0
    assert "recorded-at" in result.output


def test_support_command_registry_keeps_hidden_provider_and_demo_surface() -> None:
    source = SUPPORT_REGISTRY.read_text(encoding="utf-8")

    assert "hidden=True" in source
    assert "kling-i2v-smoke" in source
    assert "minimax-image-smoke" in source
    assert "memory-advantage-demo-012" not in source
    assert "memory-advantage-demo-015" not in source
