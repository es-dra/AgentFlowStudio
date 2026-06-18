from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timezone
from typing import Any
from urllib.parse import unquote
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from agentflow.harness.json_io import write_json
from apps.api.runtime_store import RuntimeStore, read_json, safe_id


AUTH_ENABLED_ENV = "AFS_AUTH_ENABLED"
AUTH_INVITE_CODES_ENV = "AFS_INVITE_CODES"
AUTH_OPEN_SIGNUP_ENV = "AFS_AUTH_ALLOW_OPEN_SIGNUP"
TRUE_VALUES = {"1", "true", "yes", "on"}
PUBLIC_PREFIXES = ("/auth", "/health", "/capabilities", "/site", "/studio")


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
        return _enabled(self.env.get(AUTH_ENABLED_ENV))

    def open_signup_enabled(self) -> bool:
        return _enabled(self.env.get(AUTH_OPEN_SIGNUP_ENV))

    def invite_registration_available(self) -> bool:
        return self.open_signup_enabled() or bool(self._invites().get("invites"))

    def seed_invites_from_env(self) -> None:
        invites = self._invites()
        changed = False
        for raw in str(self.env.get(AUTH_INVITE_CODES_ENV, "")).split(","):
            code = raw.strip()
            if not code:
                continue
            code_hash = _hash_text(_normalize_invite_code(code))
            if code_hash in invites["invites"]:
                continue
            invites["invites"][code_hash] = {
                "invite_id": f"inv_{code_hash[:12]}",
                "source": "env",
                "created_at": _now(),
                "consumed_by_user_id": "",
                "consumed_at": "",
            }
            changed = True
        if changed:
            write_json(self.invites_path, invites)

    def register(self, request: AuthRegisterRequest) -> dict[str, Any]:
        if not self.enabled():
            raise HTTPException(status_code=403, detail="auth is disabled")
        email = _normalize_email(request.email)
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
            "password_hash": _password_hash(request.password),
            "created_at": _now(),
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
        if not user or not _verify_password(request.password, str(user.get("password_hash", ""))):
            raise HTTPException(status_code=401, detail="invalid email or password")
        session_token = self.create_session(str(user["user_id"]))
        return {"user": public_user(user), "session_token": session_token}

    def find_user_by_email(self, email: str) -> dict[str, Any] | None:
        normalized = _normalize_email(email)
        for user in self._users()["users"].values():
            if user.get("email") == normalized and user.get("status") == "active":
                return dict(user)
        return None

    def user_from_request(self, request: Request) -> dict[str, Any] | None:
        token = _bearer_token(request.headers.get("authorization", ""))
        if not token:
            return None
        session = self._sessions()["sessions"].get(_hash_text(token))
        if not session:
            return None
        user = self._users()["users"].get(str(session.get("user_id", "")))
        if not user or user.get("status") != "active":
            return None
        return dict(user)

    def require_user(self, request: Request) -> dict[str, Any]:
        user = self.user_from_request(request)
        if not user:
            raise HTTPException(status_code=401, detail="authentication required")
        request.state.afs_user = user
        return user

    def create_session(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        sessions = self._sessions()
        sessions["sessions"][_hash_text(token)] = {
            "user_id": user_id,
            "created_at": _now(),
            "last_seen_at": _now(),
        }
        write_json(self.sessions_path, sessions)
        return token

    def revoke_request_session(self, request: Request) -> None:
        token = _bearer_token(request.headers.get("authorization", ""))
        if not token:
            return
        sessions = self._sessions()
        if sessions["sessions"].pop(_hash_text(token), None) is not None:
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
        code_hash = _hash_text(_normalize_invite_code(invite_code))
        invites = self._invites()
        invite = invites["invites"].get(code_hash)
        if not invite or invite.get("consumed_by_user_id"):
            raise HTTPException(status_code=400, detail="invite code is invalid or already used")
        invite["consumed_by_user_id"] = "pending"
        invite["consumed_at"] = _now()
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
        invite["consumed_at"] = invite.get("consumed_at") or _now()
        write_json(self.invites_path, invites)

    def _users(self) -> dict[str, Any]:
        return _read_or_default(self.users_path, {"schema_version": "0.1.0", "users": {}})

    def _invites(self) -> dict[str, Any]:
        return _read_or_default(self.invites_path, {"schema_version": "0.1.0", "invites": {}})

    def _sessions(self) -> dict[str, Any]:
        return _read_or_default(self.sessions_path, {"schema_version": "0.1.0", "sessions": {}})

    def _project_owners(self) -> dict[str, Any]:
        return _read_or_default(self.project_owners_path, {"schema_version": "0.1.0", "project_owners": {}})


def register_runtime_auth_routes(app: FastAPI, auth: RuntimeAuthStore) -> None:
    @app.get("/auth/status")
    def auth_status(request: Request) -> dict[str, Any]:
        user = auth.user_from_request(request) if auth.enabled() else None
        return {
            "auth_required": auth.enabled(),
            "authenticated": bool(user),
            "user": public_user(user) if user else None,
            "invite_registration_available": auth.invite_registration_available(),
        }

    @app.get("/auth/me")
    def auth_me(request: Request) -> dict[str, Any]:
        return {"user": public_user(auth.require_user(request))}

    @app.post("/auth/register")
    def auth_register(request: AuthRegisterRequest) -> dict[str, Any]:
        return auth.register(request)

    @app.post("/auth/login")
    def auth_login(request: AuthLoginRequest) -> dict[str, Any]:
        return auth.login(request)

    @app.post("/auth/logout")
    def auth_logout(request: Request) -> dict[str, Any]:
        auth.revoke_request_session(request)
        return {"signed_out": True}


def configure_runtime_auth_middleware(app: FastAPI, auth: RuntimeAuthStore) -> None:
    @app.middleware("http")
    async def runtime_auth_middleware(request: Request, call_next):
        if not auth.enabled() or _is_public_request(request):
            return await call_next(request)
        user = auth.user_from_request(request)
        if not user:
            return JSONResponse(status_code=401, content={"detail": "authentication required"})
        request.state.afs_user = user
        project_id = _project_id_from_path(request.url.path)
        if project_id and not auth.user_can_access_project(str(user["user_id"]), project_id):
            return JSONResponse(status_code=403, content={"detail": "project access denied"})
        return await call_next(request)


def public_user(user: dict[str, Any] | None) -> dict[str, Any] | None:
    if not user:
        return None
    return {
        "user_id": str(user.get("user_id", "")),
        "email": str(user.get("email", "")),
        "display_name": str(user.get("display_name", "")),
    }


def _is_public_request(request: Request) -> bool:
    path = request.url.path
    if request.method == "OPTIONS":
        return True
    return path == "/" or path == "/favicon.ico" or path.startswith(PUBLIC_PREFIXES)


def _project_id_from_path(path: str) -> str:
    parts = [part for part in path.split("/") if part]
    if len(parts) >= 2 and parts[0] == "projects":
        return safe_id(unquote(parts[1]))
    return ""


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


def _password_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    iterations = 200_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), iterations).hex()
    return f"pbkdf2_sha256${iterations}${salt}${digest}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, digest = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), int(iterations)).hex()
        return hmac.compare_digest(candidate, digest)
    except (ValueError, TypeError):
        return False


def _normalize_email(value: str) -> str:
    text = str(value or "").strip().lower()
    return text if "@" in text and "." in text.rsplit("@", 1)[-1] else ""


def _normalize_invite_code(value: str) -> str:
    return str(value or "").strip()


def _hash_text(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _bearer_token(header: str) -> str:
    if not header.lower().startswith("bearer "):
        return ""
    return header.split(" ", 1)[1].strip()


def _enabled(value: str | None) -> bool:
    return str(value or "").strip().lower() in TRUE_VALUES


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = (
    "AUTH_ENABLED_ENV",
    "AUTH_INVITE_CODES_ENV",
    "RuntimeAuthStore",
    "configure_runtime_auth_middleware",
    "public_user",
    "register_runtime_auth_routes",
)
