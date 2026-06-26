from __future__ import annotations

import os
import tarfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import typer

from apps.api.runtime_store import safe_id


runtime_backup_app = typer.Typer(help="Admin-only Runtime data backup operations.")
BACKUP_PREFIX = "afs-runtime-backup"
DEFAULT_EXCLUDES = {"codex-home"}


@runtime_backup_app.command(name="create")
def create_runtime_backup_command(
    runtime_root: Path = typer.Option(
        Path("data/processed/runs/runtime_service"),
        "--runtime-root",
        envvar="AFS_RUNTIME_ROOT",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        help="Runtime root to back up.",
        show_default=False,
    ),
    output_dir: Path = typer.Option(
        Path("data/outputs/runtime_backups"),
        "--output-dir",
        help="Directory where the backup archive will be written.",
        show_default=False,
    ),
    label: str = typer.Option("", "--label", help="Optional safe label to include in the archive filename."),
    include_codex_home: bool = typer.Option(False, "--include-codex-home", help="Include codex-home; usually contains local auth material."),
    retention_days: int = typer.Option(14, "--retention-days", min=0, help="Delete local backup archives older than this many days."),
) -> None:
    """Create a tar.gz backup of Runtime data with sensitive helper dirs excluded by default."""
    output_dir.mkdir(parents=True, exist_ok=True)
    backup_path = output_dir / _backup_filename(label)
    excluded_roots = set() if include_codex_home else DEFAULT_EXCLUDES
    with tarfile.open(backup_path, "w:gz") as archive:
        for path in sorted(runtime_root.rglob("*")):
            if _excluded(path, runtime_root=runtime_root, excluded_roots=excluded_roots):
                continue
            archive.add(path, arcname=Path("runtime_root") / path.relative_to(runtime_root), recursive=False)
    _chmod_owner_only(backup_path)
    deleted = _apply_retention(output_dir, retention_days=retention_days)
    typer.echo(f"Runtime backup written: {backup_path}")
    typer.echo(f"Size bytes: {backup_path.stat().st_size}")
    typer.echo("Excluded by default: codex-home and transient lock/temp files.")
    if deleted:
        typer.echo(f"Deleted old backups: {deleted}")


def _backup_filename(label: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = f"-{safe_id(label)}" if label else ""
    return f"{BACKUP_PREFIX}-{stamp}{suffix}.tar.gz"


def _excluded(path: Path, *, runtime_root: Path, excluded_roots: set[str]) -> bool:
    rel = path.relative_to(runtime_root)
    if rel.parts and rel.parts[0] in excluded_roots:
        return True
    return path.name.endswith(".lock") or ".tmp" in path.name


def _chmod_owner_only(path: Path) -> None:
    if os.name == "nt":
        return
    path.chmod(0o600)


def _apply_retention(output_dir: Path, *, retention_days: int) -> int:
    if retention_days <= 0:
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    deleted = 0
    for path in output_dir.glob(f"{BACKUP_PREFIX}-*.tar.gz"):
        modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        if modified >= cutoff:
            continue
        path.unlink()
        deleted += 1
    return deleted


__all__ = ("runtime_backup_app",)
