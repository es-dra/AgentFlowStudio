from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentflow.harness.json_io import write_json
from apps.api.runtime_auth_security import hash_text, normalize_invite_code, now
from apps.api.runtime_store import safe_id


def create_invite_record(
    *,
    invites_path: Path,
    invites: dict[str, Any],
    code: str,
    source: str = "admin_cli",
    batch_id: str = "",
    note: str = "",
    expires_at: str = "",
) -> dict[str, Any]:
    normalized = normalize_invite_code(code)
    if not normalized:
        raise ValueError("invite code is empty")
    code_hash = hash_text(normalized)
    if code_hash in invites["invites"]:
        raise ValueError("invite code already exists")
    record = {
        "invite_id": f"inv_{code_hash[:12]}",
        "source": str(source or "admin_cli")[:80],
        "batch_id": safe_id(batch_id) if batch_id else "",
        "note": str(note or "")[:160],
        "created_at": now(),
        "expires_at": str(expires_at or ""),
        "revoked_at": "",
        "consumed_by_user_id": "",
        "consumed_at": "",
    }
    invites["invites"][code_hash] = record
    write_json(invites_path, invites)
    return public_invite(record)


def list_public_invites(invites: dict[str, Any]) -> list[dict[str, Any]]:
    return [public_invite(invite) for invite in invites["invites"].values()]


def revoke_invite_record(*, invites_path: Path, invites: dict[str, Any], invite_id: str) -> dict[str, Any]:
    needle = str(invite_id or "").strip()
    for invite in invites["invites"].values():
        if str(invite.get("invite_id") or "") != needle:
            continue
        if invite.get("consumed_by_user_id") and invite.get("consumed_by_user_id") != "pending":
            raise ValueError("invite code is already consumed")
        invite["revoked_at"] = invite.get("revoked_at") or now()
        write_json(invites_path, invites)
        return public_invite(invite)
    raise KeyError("invite code not found")


def public_invite(invite: dict[str, Any]) -> dict[str, Any]:
    consumed_by = str(invite.get("consumed_by_user_id") or "")
    status = "available"
    if invite.get("revoked_at"):
        status = "revoked"
    elif consumed_by and consumed_by != "pending":
        status = "consumed"
    elif invite_expired(invite):
        status = "expired"
    elif consumed_by == "pending":
        status = "reserved"
    return {
        "invite_id": str(invite.get("invite_id", "")),
        "status": status,
        "source": str(invite.get("source", "")),
        "batch_id": str(invite.get("batch_id", "")),
        "note": str(invite.get("note", "")),
        "created_at": str(invite.get("created_at", "")),
        "expires_at": str(invite.get("expires_at", "")),
        "revoked_at": str(invite.get("revoked_at", "")),
        "consumed_by_user_id": "" if consumed_by == "pending" else consumed_by,
        "consumed_at": str(invite.get("consumed_at", "")) if consumed_by != "pending" else "",
    }


def invite_expired(invite: dict[str, Any]) -> bool:
    expires_at = str(invite.get("expires_at") or "")
    if not expires_at:
        return False
    try:
        parsed = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) > parsed.astimezone(timezone.utc)


__all__ = (
    "create_invite_record",
    "invite_expired",
    "list_public_invites",
    "public_invite",
    "revoke_invite_record",
)
