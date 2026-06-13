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
    "memory-evidence-reuse-review",
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
    assert "memory_video_pipeline_command" not in source
    assert "register_production_memory_commands" in source
    assert "runtime-service" in source
    assert "runtime-service-openapi-export" in source
    assert "production-memory-loop-next-operator-start-packet" not in source
    assert "production-memory-loop-record-next-operator-start" not in source
    assert "production-memory-loop-record-next-operator-action-result" not in source
    assert "production-memory-loop-record-action-result-acceptance-feedback" not in source


def test_production_memory_registry_is_hidden_compatibility_only() -> None:
    source = PRODUCTION_MEMORY_REGISTRY.read_text(encoding="utf-8")

    assert "hidden compatibility only" in source
    assert "production-memory-loop-asset-profile-readiness" in source
    assert "production-memory-loop-run-asset-test-package" in source
    assert "production-memory-loop-record-asset-feedback" in source
    assert "production-memory-loop-run-real-asset-test-harness" in source
    assert "production-memory-loop-two-round-context-runtime-validation" in source
    assert "production-memory-loop-provider-validation-gate" in source
    assert "production-memory-loop-next-operator-start-packet" in source
    assert "production-memory-loop-record-next-operator-action-result" in source
    assert "production-memory-loop-record-action-result-acceptance-feedback" in source
    assert "_hidden(app" in source
    assert "hidden=True" in source
    assert "_visible(app" not in source


def test_default_help_excludes_production_memory_legacy_surface() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "asset-test-package-run" not in result.output
    assert "asset-test-run-harness" not in result.output
    assert "asset-two-round-validate" not in result.output
    assert "asset-provider-validation-gate" not in result.output
    assert "asset-feedback-record" not in result.output
    assert "asset-profile-update-review" not in result.output
    assert "production-memory-loop-run-asset-test-package" not in result.output
    assert "production-memory-loop-record-asset-feedback" not in result.output
    assert "production-memory-loop-record-next-operator-action-result" not in result.output
    assert "production-memory-loop-record-action-result-acceptance-feedback" not in result.output
    assert "production-memory-loop-next-operator-start-packet" not in result.output
    assert "web-bridge" not in result.output


def test_web_bridge_command_is_retired_not_hidden() -> None:
    result = CliRunner().invoke(app, ["web-bridge", "--help"])

    assert result.exit_code != 0
    assert "No such command" in result.output


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
    assert "/projects/import" not in schema["paths"]
    assert "/projects/{project_id}/source-assets" not in schema["paths"]
    assert "/projects/{project_id}/content-cards" not in schema["paths"]
    assert "/projects/{project_id}/canvas-draft" not in schema["paths"]
    assert "/projects/{project_id}/scene-inspector" not in schema["paths"]
    assert "/projects/{project_id}/review-decisions" not in schema["paths"]
    assert "/projects/{project_id}/export" not in schema["paths"]
    assert "/runs/asset-test" not in schema["paths"]
    assert "/runs/two-round-validate" not in schema["paths"]
    assert "/provider/validation-plan" not in schema["paths"]
    assert "/provider/script-draft-plan" in schema["paths"]
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
