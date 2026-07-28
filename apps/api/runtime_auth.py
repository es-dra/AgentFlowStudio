from __future__ import annotations

import os
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, Request
from pydantic import BaseModel, Field

from agentflow.harness.json_io import exclusive_file_lock, write_json
from apps.api.runtime_auth_invites import (
    create_invite_record,
    invite_expired,
    list_public_invites,
    revoke_invite_record,
    seed_invites_from_env_records,
)
from apps.api.runtime_auth_files import public_user, read_or_default
from apps.api.runtime_auth_rate_limit import clear_auth_failures, enforce_auth_rate_limit, record_auth_failure
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
from apps.api.runtime_logging import audit_event
from apps.api.runtime_store import RuntimeStore, safe_id


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
        self.rate_limits_path = self.auth_dir / "rate_limits.json"
        self.lock_path = self.auth_dir / "auth.lock"
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
        with exclusive_file_lock(self.lock_path):
            invites, changed, skipped = seed_invites_from_env_records(self._invites(), str(self.env.get(AUTH_INVITE_CODES_ENV, "")))
            if skipped:
                audit_event("auth.invite.env_skipped", reason="unsafe_static_invite_code", count=skipped)
            if changed:
                write_json(self.invites_path, invites)

    def create_invite_code(
        self,
        code: str,
        *,
        source: str = "admin_cli",
        batch_id: str = "",
        note: str = "",
        expires_at: str = "",
    ) -> dict[str, Any]:
        with exclusive_file_lock(self.lock_path):
            return create_invite_record(
                invites_path=self.invites_path,
                invites=self._invites(),
                code=code,
                source=source,
                batch_id=batch_id,
                note=note,
                expires_at=expires_at,
            )

    def list_invites(self) -> list[dict[str, Any]]:
        with exclusive_file_lock(self.lock_path):
            return list_public_invites(self._invites())

    def revoke_invite(self, invite_id: str) -> dict[str, Any]:
        with exclusive_file_lock(self.lock_path):
            return revoke_invite_record(invites_path=self.invites_path, invites=self._invites(), invite_id=invite_id)

    def register(self, request: AuthRegisterRequest, *, client_ip: str = "", request_id: str = "") -> dict[str, Any]:
        if not self.enabled():
            raise HTTPException(status_code=403, detail="auth is disabled")
        email = normalize_email(request.email)
        if not email:
            raise HTTPException(status_code=400, detail="email is invalid")
        with exclusive_file_lock(self.lock_path):
            self._enforce_auth_limit("register", client_ip, email)
            users = self._users()
            if any(item.get("email") == email for item in users["users"].values()):
                self._record_auth_failure("register", client_ip, email, reason="email_exists", request_id=request_id)
                raise HTTPException(status_code=409, detail="email already registered")
            try:
                invite_hash = self._reserve_invite(request.invite_code)
            except HTTPException:
                self._record_auth_failure("register", client_ip, email, reason="invalid_invite", request_id=request_id)
                raise
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
            session_token = self._create_session_unlocked(user_id)
            clear_auth_failures(self.rate_limits_path, scope="register", client_ip=client_ip, identifier=email)
            audit_event("auth.register.succeeded", request_id=request_id, user_id=user_id, email_hash=_email_hash(email), client_ip=client_ip)
            return {"user": public_user(user), "session_token": session_token}

    def login(self, request: AuthLoginRequest, *, client_ip: str = "", request_id: str = "") -> dict[str, Any]:
        if not self.enabled():
            raise HTTPException(status_code=403, detail="auth is disabled")
        email = normalize_email(request.email)
        with exclusive_file_lock(self.lock_path):
            self._enforce_auth_limit("login", client_ip, email)
            user = self.find_user_by_email(email)
            if not user or not verify_password(request.password, str(user.get("password_hash", ""))):
                self._record_auth_failure("login", client_ip, email, reason="invalid_credentials", request_id=request_id)
                raise HTTPException(status_code=401, detail="invalid email or password")
            clear_auth_failures(self.rate_limits_path, scope="login", client_ip=client_ip, identifier=email)
            session_token = self._create_session_unlocked(str(user["user_id"]))
            audit_event("auth.login.succeeded", request_id=request_id, user_id=str(user["user_id"]), email_hash=_email_hash(email), client_ip=client_ip)
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
        with exclusive_file_lock(self.lock_path):
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
        cached = getattr(request.state, "afs_user", None)
        if isinstance(cached, dict) and cached.get("user_id"):
            return dict(cached)
        user = self.user_from_request(request)
        if not user:
            raise HTTPException(status_code=401, detail="authentication required")
        request.state.afs_user = user
        return user

    def create_session(self, user_id: str) -> str:
        with exclusive_file_lock(self.lock_path):
            return self._create_session_unlocked(user_id)

    def _create_session_unlocked(self, user_id: str) -> str:
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
        with exclusive_file_lock(self.lock_path):
            sessions = self._sessions()
            if sessions["sessions"].pop(hash_text(token), None) is not None:
                write_json(self.sessions_path, sessions)

    def register_project_owner(self, project_id: str, user_id: str) -> None:
        with exclusive_file_lock(self.lock_path):
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
        if not invite or invite.get("consumed_by_user_id") or invite.get("revoked_at") or invite_expired(invite):
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

    def _enforce_auth_limit(self, scope: str, client_ip: str, identifier: str) -> None:
        try:
            enforce_auth_rate_limit(self.rate_limits_path, scope=scope, client_ip=client_ip, identifier=identifier, env=self.env)
        except HTTPException:
            audit_event("auth.rate_limited", scope=scope, email_hash=_email_hash(identifier), client_ip=client_ip)
            raise

    def _record_auth_failure(self, scope: str, client_ip: str, identifier: str, *, reason: str, request_id: str) -> None:
        result = record_auth_failure(self.rate_limits_path, scope=scope, client_ip=client_ip, identifier=identifier, env=self.env)
        audit_event(
            f"auth.{scope}.failed",
            request_id=request_id,
            reason=reason,
            email_hash=_email_hash(identifier),
            client_ip=client_ip,
            failure_count=result.get("failure_count", 0),
            locked_until=result.get("locked_until", ""),
        )

    def _users(self) -> dict[str, Any]:
        return read_or_default(self.users_path, {"schema_version": "0.1.0", "users": {}})

    def _invites(self) -> dict[str, Any]:
        return read_or_default(self.invites_path, {"schema_version": "0.1.0", "invites": {}})

    def _sessions(self) -> dict[str, Any]:
        return read_or_default(self.sessions_path, {"schema_version": "0.1.0", "sessions": {}})

    def _project_owners(self) -> dict[str, Any]:
        return read_or_default(self.project_owners_path, {"schema_version": "0.1.0", "project_owners": {}})

def _email_hash(email: str) -> str:
    return hash_text(normalize_email(email))[:16] if email else ""
