from __future__ import annotations

import json
import tarfile
from pathlib import Path

from typer.testing import CliRunner

from apps.cli.main import app


PRODUCT_REGISTRY = Path("apps/cli/command_registry.py")
PRODUCTION_MEMORY_REGISTRY = Path("apps/cli/production_memory_command_registry.py")
SUPPORT_REGISTRY = Path("apps/cli/support_command_registry.py")
RUNTIME_SERVICE_COMMAND = Path("apps/cli/runtime_service_command.py")
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
    "runtime-backup",
    "auth-invites",
)


def test_product_command_registry_has_no_direct_provider_or_demo_registrations() -> None:
    source = PRODUCT_REGISTRY.read_text(encoding="utf-8")

    assert "minimax_image_command" not in source
    assert "memory_demo_commands" not in source
    assert "minimax-image-smoke" not in source
    assert "memory-advantage-demo-012" not in source
    assert "memory-advantage-demo-015" not in source
    assert "memory_video_pipeline_command" not in source
    assert "register_production_memory_commands" in source
    assert "runtime-service" in source
    assert "runtime-service-openapi-export" in source
    assert "runtime_backup_app" in source
    assert "auth_invites_app" in source
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


def test_runtime_service_command_uses_runtime_root_envvar() -> None:
    source = RUNTIME_SERVICE_COMMAND.read_text(encoding="utf-8")

    assert 'envvar="AFS_RUNTIME_ROOT"' in source
    assert "Ignored local runtime root" not in source


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


def test_auth_invites_cli_issues_lists_and_revokes_without_storing_plaintext(tmp_path) -> None:
    runtime_root = tmp_path / "runtime"
    output = tmp_path / "admin-local" / "wave1.csv"
    runner = CliRunner()

    issued = runner.invoke(
        app,
        [
            "auth-invites",
            "issue",
            "--runtime-root",
            str(runtime_root),
            "--count",
            "2",
            "--batch",
            "wave-1",
            "--note",
            "first internal beta",
            "--output",
            str(output),
        ],
    )

    assert issued.exit_code == 0, issued.output
    rows = output.read_text(encoding="utf-8").splitlines()
    assert len(rows) == 3
    first_code = rows[1].split(",", 1)[0]
    assert first_code.startswith("AFS-")
    assert first_code not in issued.output
    invites_text = (runtime_root / "auth" / "invites.json").read_text(encoding="utf-8")
    assert first_code not in invites_text

    listed = runner.invoke(app, ["auth-invites", "list", "--runtime-root", str(runtime_root)])
    assert listed.exit_code == 0, listed.output
    assert "wave-1" in listed.output
    assert first_code not in listed.output

    first_invite_id = rows[1].split(",")[1]
    revoked = runner.invoke(app, ["auth-invites", "revoke", first_invite_id, "--runtime-root", str(runtime_root)])
    assert revoked.exit_code == 0, revoked.output
    assert "revoked" in revoked.output


def test_runtime_backup_cli_excludes_codex_home_by_default(tmp_path) -> None:
    runtime_root = tmp_path / "runtime"
    (runtime_root / "auth").mkdir(parents=True)
    (runtime_root / "auth" / "users.json").write_text('{"users": {}}', encoding="utf-8")
    (runtime_root / "codex-home").mkdir()
    (runtime_root / "codex-home" / "auth.json").write_text('{"token": "secret"}', encoding="utf-8")
    output_dir = tmp_path / "backups"

    result = CliRunner().invoke(
        app,
        [
            "runtime-backup",
            "create",
            "--runtime-root",
            str(runtime_root),
            "--output-dir",
            str(output_dir),
            "--label",
            "wave1",
        ],
    )

    assert result.exit_code == 0, result.output
    [archive_path] = list(output_dir.glob("afs-runtime-backup-*.tar.gz"))
    with tarfile.open(archive_path, "r:gz") as archive:
        names = archive.getnames()
    assert "runtime_root/auth/users.json" in names
    assert "runtime_root/codex-home/auth.json" not in names


def test_hidden_production_memory_support_commands_remain_callable() -> None:
    result = CliRunner().invoke(app, ["production-memory-loop-record-next-operator-action-result", "--help"])

    assert result.exit_code == 0
    assert "recorded-at" in result.output


def test_support_command_registry_has_no_retired_provider_smoke_surface() -> None:
    source = SUPPORT_REGISTRY.read_text(encoding="utf-8")

    assert "hidden=True" not in source
    assert "smoke" not in source
    assert "minimax-image-smoke" not in source
    assert "memory-advantage-demo-012" not in source
    assert "memory-advantage-demo-015" not in source
