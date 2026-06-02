from __future__ import annotations

import json

from typer.testing import CliRunner

from apps.cli.main import app


IMAGE_ENV_VARS = [
    "AFS_ALLOW_REMOTE_IMAGE",
    "AFS_IMAGE_PROVIDER",
    "AFS_IMAGE_BASE_URL",
    "AFS_IMAGE_API_KEY",
    "AFS_IMAGE_MODEL",
]


def test_alpha_smoke_cli_reports_blocked_posterflow_without_provider_env(monkeypatch) -> None:
    for name in IMAGE_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    result = CliRunner().invoke(app, ["alpha-smoke"])

    assert result.exit_code == 0, result.output
    assert "Alpha smoke readiness: blocked" in result.output
    assert "agentflow_production_handoff" in result.output
    assert "pass    Deterministic handoff evidence is recorded" in result.output
    assert "agentflow_studio_package" in result.output
    assert "pass    Local package-chain evidence is recorded" in result.output
    assert "posterflow_live_smoke" in result.output
    assert "blocked Remote image provider is not enabled" in result.output
    assert "Remote image provider is not enabled" in result.output
    assert "docs/alpha_readiness_report.md" in result.output


def test_alpha_smoke_cli_json_output_is_machine_readable(monkeypatch) -> None:
    for name in IMAGE_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    result = CliRunner().invoke(app, ["alpha-smoke", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "blocked"
    assert payload["claim_boundary"] == "engineering_readiness_only"
    assert payload["remote_provider_policy"]["image"] == "disabled_by_default"
    assert [check["id"] for check in payload["checks"]] == [
        "agentflow_production_handoff",
        "agentflow_studio_package",
        "posterflow_live_smoke",
    ]
    assert payload["checks"][2]["status"] == "blocked"
    assert payload["checks"][2]["provider_env"]["AFS_ALLOW_REMOTE_IMAGE"] == "unset"
