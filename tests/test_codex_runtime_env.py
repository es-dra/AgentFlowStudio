from __future__ import annotations

from pathlib import Path

from agentflow_studio.model_gateway.codex_runtime_env import (
    bootstrap_codex_home,
    codex_subprocess_env,
    prune_codex_home,
    resolve_codex_home,
)


def test_codex_subprocess_env_defaults_to_runtime_scoped_home(tmp_path, monkeypatch) -> None:
    runtime_root = tmp_path / "runtime"
    monkeypatch.setenv("AFS_RUNTIME_ROOT", str(runtime_root))
    monkeypatch.setenv("AFS_CODEX_BOOTSTRAP", "false")
    monkeypatch.delenv("AFS_CODEX_HOME", raising=False)

    env = codex_subprocess_env()

    assert Path(env["CODEX_HOME"]) == runtime_root / "codex-home"
    assert Path(env["CODEX_HOME"]).is_dir()
    assert resolve_codex_home(env) == runtime_root / "codex-home"
    assert not (runtime_root / "codex-home" / "history.jsonl").exists()
    assert not (runtime_root / "codex-home" / "logs_2.sqlite").exists()


def test_codex_subprocess_env_honors_explicit_afs_codex_home(tmp_path, monkeypatch) -> None:
    codex_home = tmp_path / "afs-codex-home"
    monkeypatch.setenv("AFS_CODEX_HOME", str(codex_home))
    monkeypatch.setenv("AFS_CODEX_BOOTSTRAP", "false")

    env = codex_subprocess_env()

    assert Path(env["CODEX_HOME"]) == codex_home
    assert codex_home.is_dir()


def test_codex_subprocess_env_honors_existing_codex_home(tmp_path, monkeypatch) -> None:
    codex_home = tmp_path / "existing-codex-home"
    monkeypatch.delenv("AFS_CODEX_HOME", raising=False)
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setenv("AFS_CODEX_BOOTSTRAP", "false")

    env = codex_subprocess_env()

    assert Path(env["CODEX_HOME"]) == codex_home
    assert codex_home.is_dir()


def test_bootstrap_codex_home_copies_only_minimal_runtime_files(tmp_path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    (source / "auth.json").write_text("{}", encoding="utf-8")
    (source / "config.toml").write_text("model = 'test'\n", encoding="utf-8")
    (source / "history.jsonl").write_text("sensitive prompt history\n", encoding="utf-8")
    (source / "logs_2.sqlite").write_bytes(b"logs")
    target.mkdir()

    bootstrap_codex_home(target, source_home=source)

    assert (target / "auth.json").is_file()
    assert (target / "config.toml").is_file()
    assert not (target / "history.jsonl").exists()
    assert not (target / "logs_2.sqlite").exists()


def test_prune_codex_home_removes_runtime_history_logs_and_state(tmp_path) -> None:
    codex_home = tmp_path / "codex-home"
    codex_home.mkdir()
    (codex_home / "auth.json").write_text("{}", encoding="utf-8")
    (codex_home / "config.toml").write_text("model = 'test'\n", encoding="utf-8")
    for name in (
        "history.jsonl",
        "logs_2.sqlite",
        "logs_2.sqlite-wal",
        "state_5.sqlite",
        "goals_1.sqlite",
        "memories_1.sqlite",
    ):
        (codex_home / name).write_text("runtime state\n", encoding="utf-8")
    (codex_home / "shell_snapshots").mkdir()
    (codex_home / "shell_snapshots" / "snapshot.sh").write_text("prompt\n", encoding="utf-8")
    (codex_home / "log").mkdir()
    (codex_home / "log" / "codex.log").write_text("log\n", encoding="utf-8")

    prune_codex_home({"CODEX_HOME": str(codex_home)})

    assert (codex_home / "auth.json").is_file()
    assert (codex_home / "config.toml").is_file()
    assert not (codex_home / "history.jsonl").exists()
    assert not (codex_home / "logs_2.sqlite").exists()
    assert not (codex_home / "state_5.sqlite").exists()
    assert not (codex_home / "shell_snapshots").exists()
    assert not (codex_home / "log").exists()
