from __future__ import annotations

import json

from tools import kling_provider_preflight


def test_kling_preflight_reports_missing_service_without_secrets(tmp_path, monkeypatch, capsys) -> None:
    config_path = tmp_path / "providers.local.json"
    config_path.write_text(
        json.dumps(
            {
                "schema_version": "company_provider_secrets.local.v2",
                "accounts": {"minimax": {}},
                "services": {"minimax_image": {"provider": "minimax", "capability": "image"}},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("AFS_PROVIDER_CONFIG", str(config_path))
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VIDEO", raising=False)

    exit_code = kling_provider_preflight.main()

    assert exit_code == 1
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "blocked"
    assert report["checks"]["block_id"] == "provider_service_missing"
    assert report["checks"]["service_present"] is False
    assert report["checks"]["available_video_service_ids"] == []
    assert report["secrets_printed"] is False
    assert "fake" not in json.dumps(report).lower()


def test_kling_preflight_reports_missing_credentials_for_present_service(tmp_path, monkeypatch, capsys) -> None:
    config_path = tmp_path / "providers.local.json"
    config_path.write_text(json.dumps(_kling_config_with_env_credentials()), encoding="utf-8")
    monkeypatch.setenv("AFS_PROVIDER_CONFIG", str(config_path))
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    monkeypatch.delenv("KLING_ACCESS_KEY", raising=False)
    monkeypatch.delenv("KLING_SECRET_KEY", raising=False)

    exit_code = kling_provider_preflight.main()

    assert exit_code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "missing_credentials"
    assert report["checks"]["block_id"] == "provider_credentials_missing"
    assert report["checks"]["service_present"] is True
    assert report["checks"]["gate"]["enabled"] is True
    assert report["checks"]["credential_presence"]["access_key_present"] is False
    assert report["checks"]["credential_presence"]["secret_key_present"] is False
    assert report["checks"]["jwt_self_check"] == {"available": False, "reason": "missing_credentials"}
    assert report["secrets_printed"] is False


def _kling_config_with_env_credentials() -> dict:
    return {
        "schema_version": "company_provider_secrets.local.v2",
        "accounts": {
            "kling": {
                "auth_type": "jwt_hs256_from_ak_sk",
                "base_url": "https://api-beijing.klingai.com",
                "access_key_env": "KLING_ACCESS_KEY",
                "secret_key_env": "KLING_SECRET_KEY",
                "jwt": {"ttl_seconds": 1800, "nbf_skew_seconds": -5},
            }
        },
        "services": {
            "kling_i2v": {
                "provider": "kling",
                "account_ref": "kling",
                "capability": "video",
                "api_family": "i2v",
                "required_gate": "AFS_ALLOW_REMOTE_VIDEO",
                "descriptor": {
                    "schema_version": "provider_descriptor.v0.2",
                    "modality": "video",
                    "execution_mode": "async",
                    "capabilities": ["video"],
                    "reference_image_slots": 2,
                    "supported_aspect_ratios": ["9:16", "16:9"],
                    "prompt_char_limit": 2500,
                    "seed_supported": False,
                    "cost_hint": "test only",
                    "rate_limit_hint": "test only",
                    "required_gate": "AFS_ALLOW_REMOTE_VIDEO",
                    "frame_slots": {"first_frame": "required", "last_frame": "optional"},
                    "frame_modes": ["first_frame", "first_last_frame"],
                    "supported_durations_sec": [5, 10],
                    "supported_resolutions": ["720p", "1080p"],
                    "async_poll_interval_sec": 5,
                    "async_timeout_sec": 600,
                    "async_max_polls": 120,
                    "prompt_profile": "video_i2v_v1",
                },
            }
        },
    }
