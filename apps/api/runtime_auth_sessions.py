from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from fastapi import HTTPException, Request

from agentflow.harness.json_io import exclusive_file_lock, write_json
from apps.api.runtime_auth_files import read_or_default
from apps.api.runtime_auth_security import (
    bearer_token,
    hash_text,
    new_session_token,
    now,
    parse_datetime,
    session_expired,
)


AUTH_SESSION_TTL_HOURS_ENV = "AFS_AUTH_SESSION_TTL_HOURS"
AUTH_SESSION_TOUCH_SECONDS_ENV = "AFS_AUTH_SESSION_TOUCH_SECONDS"
DEFAULT_SESSION_TTL_HOURS = 168
DEFAULT_SESSION_TOUCH_SECONDS = 300


class RuntimeAuthSessionMixin:
    env: Mapping[str, str]
    lock_path: Path
    sessions_path: Path

    def session_ttl_hours(self) -> int:
        try:
            value = int(str(self.env.get(AUTH_SESSION_TTL_HOURS_ENV, "")).strip())
        except ValueError:
            value = DEFAULT_SESSION_TTL_HOURS
        return max(1, min(value, 24 * 30))

    def session_touch_seconds(self) -> int:
        try:
            value = int(str(self.env.get(AUTH_SESSION_TOUCH_SECONDS_ENV, "")).strip())
        except ValueError:
            value = DEFAULT_SESSION_TOUCH_SECONDS
        return max(30, min(value, 60 * 60))

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
            last_seen_at = parse_datetime(str(session.get("last_seen_at") or ""))
            touch_due = (
                last_seen_at is None
                or (datetime.now(timezone.utc) - last_seen_at).total_seconds()
                >= self.session_touch_seconds()
            )
            if touch_due:
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

    def _sessions(self) -> dict[str, Any]:
        return read_or_default(
            self.sessions_path,
            {"schema_version": "0.1.0", "sessions": {}},
        )

    def _users(self) -> dict[str, Any]:
        raise NotImplementedError


__all__ = (
    "AUTH_SESSION_TOUCH_SECONDS_ENV",
    "AUTH_SESSION_TTL_HOURS_ENV",
    "DEFAULT_SESSION_TOUCH_SECONDS",
    "DEFAULT_SESSION_TTL_HOURS",
    "RuntimeAuthSessionMixin",
)
