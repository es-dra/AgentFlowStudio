from __future__ import annotations

import json
from pathlib import Path

from tools.afs_provider_connected_validation_readiness import build_readiness_report


def test_provider_connected_readiness_blocks_missing_gfr_packet(tmp_path: Path, monkeypatch) -> None:
    repo_root = _repo_root(tmp_path, local_config=True)
    monkeypatch.delenv("AFS_PROVIDER_CONFIG", raising=False)

    report = build_readiness_report(repo_root=repo_root, kb_root=tmp_path / "missing-kb")

    assert report["status"] == "blocked"
    assert {item["block_id"] for item in report["readiness_blocks"]} == {"gfr_provider_validation_packet_missing"}
    assert report["provider_calls_started"] is False
    assert report["secrets_printed"] is False


def test_provider_connected_readiness_needs_local_config_when_only_example_exists(tmp_path: Path, monkeypatch) -> None:
    repo_root = _repo_root(tmp_path, local_config=False)
    kb_root = _kb_root(tmp_path)
    monkeypatch.delenv("AFS_PROVIDER_CONFIG", raising=False)
    monkeypatch.delenv("AFS_ALLOW_REMOTE_LLM", raising=False)
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)

    report = build_readiness_report(repo_root=repo_root, kb_root=kb_root)

    assert report["status"] == "needs_local_provider_config"
    assert report["runtime_surface"]["required_actions_present"] is True
    assert report["provider_config"] == {
        "source": "configs/providers.example.json",
        "present": True,
        "path_disclosed": False,
        "example_only": True,
    }
    assert "AFS_ALLOW_REMOTE_LLM" in report["required_authorizations"]["required_before_live_provider_smoke"]
    assert "AFS_ALLOW_REMOTE_IMAGE" in report["required_authorizations"]["required_before_live_provider_smoke"]


def test_provider_connected_readiness_ready_for_authorization_without_gate_open(tmp_path: Path, monkeypatch) -> None:
    repo_root = _repo_root(tmp_path, local_config=True)
    kb_root = _kb_root(tmp_path)
    monkeypatch.delenv("AFS_PROVIDER_CONFIG", raising=False)
    monkeypatch.delenv("AFS_ALLOW_REMOTE_LLM", raising=False)
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)

    report = build_readiness_report(repo_root=repo_root, kb_root=kb_root)

    assert report["status"] == "ready_for_authorization"
    assert report["provider_config"]["source"] == "configs/providers.local.json"
    assert report["provider_config"]["path_disclosed"] is False
    assert report["required_authorizations"]["required_before_live_provider_smoke"] == [
        "AFS_ALLOW_REMOTE_LLM",
        "AFS_ALLOW_REMOTE_IMAGE",
    ]
    assert report["required_authorizations"]["human_approval_required"] is True
    assert report["required_authorizations"]["human_provider_smoke_authorization_required"] is True
    assert report["required_authorizations"]["current_session_approval_inferred_from_env"] is False


def test_provider_connected_readiness_env_gates_still_need_human_authorization(tmp_path: Path, monkeypatch) -> None:
    repo_root = _repo_root(tmp_path, local_config=False)
    kb_root = _kb_root(tmp_path)
    config_path = tmp_path / "private" / "providers.local.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(json.dumps({"secret": "fake-secret"}), encoding="utf-8")
    monkeypatch.setenv("AFS_PROVIDER_CONFIG", str(config_path))
    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")

    report = build_readiness_report(repo_root=repo_root, kb_root=kb_root)
    serialized = json.dumps(report, ensure_ascii=False).lower()

    assert report["status"] == "ready_for_human_authorization"
    assert report["provider_config"]["source"] == "AFS_PROVIDER_CONFIG"
    assert report["provider_config"]["present"] is True
    assert report["provider_config"]["path_disclosed"] is False
    assert str(config_path).lower() not in serialized
    assert "fake-secret" not in serialized
    assert report["provider_calls_started"] is False
    assert report["authorization_state"] == {
        "human_live_provider_smoke_authorized": False,
        "current_session_approval_inferred_from_env": False,
        "env_gates_are_not_authorization": True,
        "provider_calls_allowed_by_this_tool": False,
    }
    assert report["required_authorizations"]["human_approval_required"] is True
    assert report["required_authorizations"]["human_provider_smoke_authorization_required"] is True
    assert report["required_authorizations"]["current_session_approval_inferred_from_env"] is False


def test_provider_connected_readiness_ready_for_provider_smoke_requires_explicit_readiness_authorization(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = _repo_root(tmp_path, local_config=False)
    kb_root = _kb_root(tmp_path)
    config_path = tmp_path / "private" / "providers.local.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(json.dumps({"secret": "fake-secret"}), encoding="utf-8")
    monkeypatch.setenv("AFS_PROVIDER_CONFIG", str(config_path))
    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")

    report = build_readiness_report(
        repo_root=repo_root,
        kb_root=kb_root,
        live_smoke_authorized=True,
    )
    serialized = json.dumps(report, ensure_ascii=False).lower()

    assert report["status"] == "ready_for_provider_smoke"
    assert report["authorization_state"]["human_live_provider_smoke_authorized"] is True
    assert report["authorization_state"]["provider_calls_allowed_by_this_tool"] is False
    assert report["required_authorizations"]["human_provider_smoke_authorization_required"] is False
    assert str(config_path).lower() not in serialized
    assert "fake-secret" not in serialized
    assert report["provider_calls_started"] is False


def _repo_root(tmp_path: Path, *, local_config: bool) -> Path:
    repo_root = tmp_path / "repo"
    configs = repo_root / "configs"
    configs.mkdir(parents=True)
    (configs / "providers.example.json").write_text("{}", encoding="utf-8")
    if local_config:
        (configs / "providers.local.json").write_text("{}", encoding="utf-8")
    return repo_root


def _kb_root(tmp_path: Path) -> Path:
    packet = (
        tmp_path
        / "kb"
        / "10-Startup"
        / "80-Workflow"
        / "ai-native-company-workflow"
        / "task-startup-packets"
        / "2026-06-17-afs-provider-connected-validation.md"
    )
    packet.parent.mkdir(parents=True)
    packet.write_text("# packet", encoding="utf-8")
    return tmp_path / "kb"
