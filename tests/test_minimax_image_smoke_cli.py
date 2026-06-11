from __future__ import annotations

import json

from typer.testing import CliRunner

from apps.cli.main import app
from agentflow_studio.model_gateway.company_secrets import COMPANY_PROVIDER_CONFIG_ENV


def test_minimax_image_smoke_cli_exposes_command() -> None:
    result = CliRunner().invoke(app, ["minimax-image-smoke", "--help"])

    assert result.exit_code == 0, result.output
    assert "Run a gated MiniMax image smoke" in result.output
    assert "--provider-config" in result.output
    assert COMPANY_PROVIDER_CONFIG_ENV in result.output


def test_minimax_i2i_smoke_cli_exposes_reference_image_option() -> None:
    result = CliRunner().invoke(app, ["minimax-i2i-smoke", "--help"])

    assert result.exit_code == 0, result.output
    assert "Run a gated MiniMax image-to-image smoke" in result.output
    assert "--subject-reference-image" in result.output
    assert "--provider-config" in result.output
    assert COMPANY_PROVIDER_CONFIG_ENV in result.output


def test_minimax_image_smoke_cli_gate_failure_is_clean(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    config_path = tmp_path / "providers.local.json"
    config_path.write_text(json.dumps(_provider_config()), encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "minimax-image-smoke",
            "--prompt",
            "memory architecture demo keyframe",
            "--provider-config",
            str(config_path),
            "--output",
            str(tmp_path / "run"),
        ],
    )

    assert result.exit_code == 1
    assert "MiniMax image smoke failed" in result.output
    assert "AFS_ALLOW_REMOTE_IMAGE" in result.output
    assert "Traceback" not in result.output
    assert "fk-mm-key" not in result.output


def _provider_config() -> dict:
    return {
        "schema_version": "company_provider_secrets.local.v2",
        "accounts": {
            "minimax": {
                "auth_type": "api_key",
                "base_url": "https://api.minimax.io",
                "api_key": "fk-mm-key",
                "default_models": {"image": ""},
            }
        },
        "services": {
            "minimax_image": {
                "provider": "minimax",
                "account_ref": "minimax",
                "capability": "image",
                "api_family": "t2i",
                "required_gate": "AFS_ALLOW_REMOTE_IMAGE",
            },
        },
    }
