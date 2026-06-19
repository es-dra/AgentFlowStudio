from __future__ import annotations

import os
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, Request
from pydantic import BaseModel, Field

from agentflow.harness.json_io import write_json
from apps.api.runtime_auth_security import (
    bearer_token,
    enabled,
    hash_text,
    new_session_token,
    normalize_email,
    normalize_invite_code,
    now,
    password_hash,
    session_expired,
    verify_password,
)
from apps.api.runtime_store import RuntimeStore, read_json, safe_id


AUTH_ENABLED_ENV = "AFS_AUTH_ENABLED"
AUTH_INVITE_CODES_ENV = "AFS_INVITE_CODES"
AUTH_OPEN_SIGNUP_ENV = "AFS_AUTH_ALLOW_OPEN_SIGNUP"
AUTH_SESSION_TTL_HOURS_ENV = "AFS_AUTH_SESSION_TTL_HOURS"
DEFAULT_SESSION_TTL_HOURS = 168


class AuthRegisterRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=8)
    display_name: str = Field(default="", max_length=80)
    invite_code: str = Field(default="", max_length=160)


class AuthLoginRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=1)


class RuntimeAuthStore:
    def __init__(self, store: RuntimeStore, env: dict[str, str] | None = None) -> None:
        self.store = store
        self.env = env if env is not None else os.environ
        self.auth_dir = store.root / "auth"
        self.auth_dir.mkdir(parents=True, exist_ok=True)
        self.users_path = self.auth_dir / "users.json"
        self.invites_path = self.auth_dir / "invites.json"
        self.sessions_path = self.auth_dir / "sessions.json"
        self.project_owners_path = self.auth_dir / "project_owners.json"
        self.seed_invites_from_env()

    def enabled(self) -> bool:
        return enabled(self.env.get(AUTH_ENABLED_ENV))

    def open_signup_enabled(self) -> bool:
        return enabled(self.env.get(AUTH_OPEN_SIGNUP_ENV))

    def invite_registration_available(self) -> bool:
        return self.open_signup_enabled() or bool(self._invites().get("invites"))

    def session_ttl_hours(self) -> int:
        try:
            value = int(str(self.env.get(AUTH_SESSION_TTL_HOURS_ENV, "")).strip())
        except ValueError:
            value = DEFAULT_SESSION_TTL_HOURS
        return max(1, min(value, 24 * 30))

    def seed_invites_from_env(self) -> None:
        invites = self._invites()
        changed = False
        for raw in str(self.env.get(AUTH_INVITE_CODES_ENV, "")).split(","):
            code = raw.strip()
            if not code:
                continue
            code_hash = hash_text(normalize_invite_code(code))
            if code_hash in invites["invites"]:
                continue
            invites["invites"][code_hash] = {
                "invite_id": f"inv_{code_hash[:12]}",
                "source": "env",
                "created_at": now(),
                "consumed_by_user_id": "",
                "consumed_at": "",
            }
            changed = True
        if changed:
            write_json(self.invites_path, invites)

    def register(self, request: AuthRegisterRequest) -> dict[str, Any]:
        if not self.enabled():
            raise HTTPException(status_code=403, detail="auth is disabled")
        email = normalize_email(request.email)
        if not email:
            raise HTTPException(status_code=400, detail="email is invalid")
        users = self._users()
        if any(item.get("email") == email for item in users["users"].values()):
            raise HTTPException(status_code=409, detail="email already registered")
        invite_hash = self._reserve_invite(request.invite_code)
        user_id = f"usr_{uuid4().hex[:12]}"
        user = {
            "user_id": user_id,
            "email": email,
            "display_name": request.display_name.strip()[:80] or email.split("@", 1)[0],
            "password_hash": password_hash(request.password),
            "created_at": now(),
            "status": "active",
        }
        users["users"][user_id] = user
        write_json(self.users_path, users)
        self._mark_invite_consumed(invite_hash, user_id)
        session_token = self.create_session(user_id)
        return {"user": public_user(user), "session_token": session_token}

    def login(self, request: AuthLoginRequest) -> dict[str, Any]:
        if not self.enabled():
            raise HTTPException(status_code=403, detail="auth is disabled")
        user = self.find_user_by_email(request.email)
        if not user or not verify_password(request.password, str(user.get("password_hash", ""))):
            raise HTTPException(status_code=401, detail="invalid email or password")
        session_token = self.create_session(str(user["user_id"]))
        return {"user": public_user(user), "session_token": session_token}

    def find_user_by_email(self, email: str) -> dict[str, Any] | None:
        normalized = normalize_email(email)
        for user in self._users()["users"].values():
            if user.get("email") == normalized and user.get("status") == "active":
                return dict(user)
        return None

    def user_from_request(self, request: Request) -> dict[str, Any] | None:
        token = bearer_token(request.headers.get("authorization", ""))
        if not token:
            return None
        token_hash = hash_text(token)
        sessions = self._sessions()
        session = sessions["sessions"].get(token_hash)
        if not session:
            return None
        if session_expired(session, ttl_hours=self.session_ttl_hours()):
            sessions["sessions"].pop(token_hash, None)
            write_json(self.sessions_path, sessions)
            return None
        user = self._users()["users"].get(str(session.get("user_id", "")))
        if not user or user.get("status") != "active":
            return None
        session["last_seen_at"] = now()
        write_json(self.sessions_path, sessions)
        return dict(user)

    def require_user(self, request: Request) -> dict[str, Any]:
        user = self.user_from_request(request)
        if not user:
            raise HTTPException(status_code=401, detail="authentication required")
        request.state.afs_user = user
        return user

    def create_session(self, user_id: str) -> str:
        token = new_session_token()
        sessions = self._sessions()
        sessions["sessions"][hash_text(token)] = {
            "user_id": user_id,
            "created_at": now(),
            "last_seen_at": now(),
        }
        write_json(self.sessions_path, sessions)
        return token

    def revoke_request_session(self, request: Request) -> None:
        token = bearer_token(request.headers.get("authorization", ""))
        if not token:
            return
        sessions = self._sessions()
        if sessions["sessions"].pop(hash_text(token), None) is not None:
            write_json(self.sessions_path, sessions)

    def register_project_owner(self, project_id: str, user_id: str) -> None:
        owners = self._project_owners()
        owners["project_owners"].setdefault(safe_id(project_id), user_id)
        write_json(self.project_owners_path, owners)

    def project_owner(self, project_id: str) -> str:
        return str(self._project_owners()["project_owners"].get(safe_id(project_id), ""))

    def user_can_access_project(self, user_id: str, project_id: str) -> bool:
        return self.project_owner(project_id) == user_id

    def filter_project_summaries(self, user_id: str, summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [item for item in summaries if self.user_can_access_project(user_id, str(item.get("project_id", "")))]

    def _reserve_invite(self, invite_code: str) -> str:
        if self.open_signup_enabled():
            return ""
        code_hash = hash_text(normalize_invite_code(invite_code))
        invites = self._invites()
        invite = invites["invites"].get(code_hash)
        if not invite or invite.get("consumed_by_user_id"):
            raise HTTPException(status_code=400, detail="invite code is invalid or already used")
        invite["consumed_by_user_id"] = "pending"
        invite["consumed_at"] = now()
        write_json(self.invites_path, invites)
        return code_hash

    def _mark_invite_consumed(self, invite_hash: str, user_id: str) -> None:
        if not invite_hash:
            return
        invites = self._invites()
        invite = invites["invites"].get(invite_hash)
        if not invite:
            return
        invite["consumed_by_user_id"] = user_id
        invite["consumed_at"] = invite.get("consumed_at") or now()
        write_json(self.invites_path, invites)

    def _users(self) -> dict[str, Any]:
        return _read_or_default(self.users_path, {"schema_version": "0.1.0", "users": {}})

    def _invites(self) -> dict[str, Any]:
        return _read_or_default(self.invites_path, {"schema_version": "0.1.0", "invites": {}})

    def _sessions(self) -> dict[str, Any]:
        return _read_or_default(self.sessions_path, {"schema_version": "0.1.0", "sessions": {}})

    def _project_owners(self) -> dict[str, Any]:
        return _read_or_default(self.project_owners_path, {"schema_version": "0.1.0", "project_owners": {}})


def public_user(user: dict[str, Any] | None) -> dict[str, Any] | None:
    if not user:
        return None
    return {
        "user_id": str(user.get("user_id", "")),
        "email": str(user.get("email", "")),
        "display_name": str(user.get("display_name", "")),
    }


def _read_or_default(path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        write_json(path, default)
        return dict(default)
    try:
        payload = read_json(path)
    except (ValueError, OSError):
        payload = dict(default)
    for key, value in default.items():
        payload.setdefault(key, value)
    return payload


__all__ = (
    "AUTH_ENABLED_ENV",
    "AUTH_INVITE_CODES_ENV",
    "AUTH_SESSION_TTL_HOURS_ENV",
    "RuntimeAuthStore",
    "public_user",
)
