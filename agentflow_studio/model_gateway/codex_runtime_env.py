from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path


AFS_CODEX_BOOTSTRAP_ENV = "AFS_CODEX_BOOTSTRAP"
AFS_CODEX_HOME_ENV = "AFS_CODEX_HOME"
AFS_RUNTIME_ROOT_ENV = "AFS_RUNTIME_ROOT"
CODEX_HOME_ENV = "CODEX_HOME"
FALSE_VALUES = {"0", "false", "no", "off"}
BOOTSTRAP_FILES = ("auth.json", "config.toml", "models_cache.json", "version.json", "installation_id")
PRUNE_FILE_PATTERNS = (
    "history.jsonl",
    "logs_*.sqlite*",
    "state_*.sqlite*",
    "goals_*.sqlite*",
    "memories_*.sqlite*",
)
PRUNE_DIR_NAMES = ("shell_snapshots", "log", ".tmp")


def codex_subprocess_env(env: dict[str, str] | None = None) -> dict[str, str]:
    resolved = dict(os.environ if env is None else env)
    codex_home = resolve_codex_home(resolved)
    codex_home.mkdir(parents=True, exist_ok=True)
    codex_home.chmod(0o700)
    if _bootstrap_enabled(resolved):
        bootstrap_codex_home(codex_home, source_home=Path.home() / ".codex")
    resolved[CODEX_HOME_ENV] = str(codex_home)
    return resolved


def resolve_codex_home(env: dict[str, str] | None = None) -> Path:
    resolved = os.environ if env is None else env
    configured = str(resolved.get(AFS_CODEX_HOME_ENV) or "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    runtime_root = str(resolved.get(AFS_RUNTIME_ROOT_ENV) or "").strip()
    if runtime_root:
        return (Path(runtime_root).expanduser().resolve() / "codex-home").resolve()
    return (Path.home() / ".afs-codex").resolve()


def bootstrap_codex_home(codex_home: Path, *, source_home: Path) -> None:
    codex_home = Path(codex_home).resolve()
    source_home = Path(source_home).expanduser().resolve()
    if source_home == codex_home or not source_home.is_dir():
        return
    for name in BOOTSTRAP_FILES:
        source = source_home / name
        if not source.is_file():
            continue
        target = codex_home / name
        fd, raw_tmp = tempfile.mkstemp(prefix=f".{name}.", dir=codex_home)
        os.close(fd)
        tmp = Path(raw_tmp)
        try:
            shutil.copy2(source, tmp)
            tmp.chmod(0o600)
            os.replace(tmp, target)
        finally:
            tmp.unlink(missing_ok=True)


def prune_codex_home(env: dict[str, str] | None = None) -> None:
    resolved = os.environ if env is None else env
    raw_home = str(resolved.get(CODEX_HOME_ENV) or "").strip()
    codex_home = Path(raw_home).expanduser().resolve() if raw_home else resolve_codex_home(resolved)
    if not codex_home.is_dir():
        return
    for pattern in PRUNE_FILE_PATTERNS:
        for path in codex_home.glob(pattern):
            if path.is_file():
                path.unlink(missing_ok=True)
    for name in PRUNE_DIR_NAMES:
        path = codex_home / name
        if path.is_dir():
            shutil.rmtree(path)


def _bootstrap_enabled(env: dict[str, str]) -> bool:
    return str(env.get(AFS_CODEX_BOOTSTRAP_ENV) or "true").strip().lower() not in FALSE_VALUES


__all__ = (
    "AFS_CODEX_HOME_ENV",
    "AFS_RUNTIME_ROOT_ENV",
    "CODEX_HOME_ENV",
    "bootstrap_codex_home",
    "codex_subprocess_env",
    "prune_codex_home",
    "resolve_codex_home",
)
