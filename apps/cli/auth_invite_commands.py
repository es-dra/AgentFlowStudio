from __future__ import annotations

import csv
import secrets
from pathlib import Path
from typing import Any

import typer

from apps.api.runtime_auth import RuntimeAuthStore
from apps.api.runtime_store import RuntimeStore


auth_invites_app = typer.Typer(help="Admin-only invite-code operations for internal beta access.")


@auth_invites_app.command(name="issue")
def issue_invites_command(
    count: int = typer.Option(1, "--count", min=1, max=200, help="Number of one-time invite codes to issue."),
    runtime_root: Path = typer.Option(
        Path("data/processed/runs/runtime_service"),
        "--runtime-root",
        envvar="AFS_RUNTIME_ROOT",
        help="Runtime root containing the auth store.",
        show_default=False,
    ),
    batch_id: str = typer.Option("", "--batch", help="Admin batch label, for example beta-2026-06-wave1."),
    prefix: str = typer.Option("AFS", "--prefix", help="Readable prefix for generated codes."),
    note: str = typer.Option("", "--note", help="Short admin-only distribution note."),
    expires_at: str = typer.Option("", "--expires-at", help="Optional ISO timestamp after which the code is invalid."),
    output: Path | None = typer.Option(None, "--output", "-o", help="Optional CSV path for the plaintext distribution packet."),
) -> None:
    """Issue one-time invite codes and store only hashes in Runtime auth state."""
    auth = RuntimeAuthStore(RuntimeStore(runtime_root))
    rows: list[dict[str, str]] = []
    for _ in range(count):
        code = _new_invite_code(prefix)
        invite = auth.create_invite_code(code, batch_id=batch_id, note=note, expires_at=expires_at)
        rows.append({
            "code": code,
            "invite_id": invite["invite_id"],
            "status": invite["status"],
            "batch_id": invite["batch_id"],
            "note": invite["note"],
            "expires_at": invite["expires_at"],
        })
    if output:
        _write_csv(output, rows)
        typer.echo(f"Invite distribution packet written: {output}")
        for row in rows:
            typer.echo(f"{row['invite_id']}  {row['status']}  {row['batch_id']}")
    else:
        for row in rows:
            typer.echo(f"{row['code']}  {row['invite_id']}  {row['status']}  {row['batch_id']}")
    typer.echo("Only invite-code hashes were stored in Runtime auth state; keep plaintext output admin-local.")


@auth_invites_app.command(name="list")
def list_invites_command(
    runtime_root: Path = typer.Option(
        Path("data/processed/runs/runtime_service"),
        "--runtime-root",
        envvar="AFS_RUNTIME_ROOT",
        help="Runtime root containing the auth store.",
        show_default=False,
    ),
) -> None:
    """List invite-code status without revealing plaintext invite codes."""
    auth = RuntimeAuthStore(RuntimeStore(runtime_root))
    rows = sorted(auth.list_invites(), key=lambda item: (item.get("batch_id", ""), item.get("created_at", "")))
    if not rows:
        typer.echo("No invite codes found.")
        return
    for row in rows:
        typer.echo(
            "  ".join([
                str(row["invite_id"]),
                str(row["status"]),
                str(row.get("batch_id") or "-"),
                str(row.get("created_at") or "-"),
                str(row.get("consumed_by_user_id") or "-"),
            ])
        )


@auth_invites_app.command(name="revoke")
def revoke_invite_command(
    invite_id: str = typer.Argument(..., help="Invite id to revoke, for example inv_abcd1234."),
    runtime_root: Path = typer.Option(
        Path("data/processed/runs/runtime_service"),
        "--runtime-root",
        envvar="AFS_RUNTIME_ROOT",
        help="Runtime root containing the auth store.",
        show_default=False,
    ),
) -> None:
    """Revoke an unconsumed invite code by invite id."""
    auth = RuntimeAuthStore(RuntimeStore(runtime_root))
    try:
        invite = auth.revoke_invite(invite_id)
    except KeyError as exc:
        raise typer.BadParameter("invite id not found") from exc
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(f"Revoked {invite['invite_id']}: {invite['status']}")


def _new_invite_code(prefix: str) -> str:
    safe_prefix = "".join(ch for ch in str(prefix or "AFS").upper() if ch.isalnum())[:12] or "AFS"
    return f"{safe_prefix}-{secrets.token_urlsafe(12).replace('-', '').replace('_', '').upper()[:16]}"


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["code", "invite_id", "status", "batch_id", "note", "expires_at"])
        writer.writeheader()
        writer.writerows(rows)


__all__ = ("auth_invites_app",)
