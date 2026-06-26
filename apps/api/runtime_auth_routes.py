from __future__ import annotations

from typing import Any
from urllib.parse import unquote

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from apps.api.runtime_auth import AuthLoginRequest, AuthRegisterRequest, RuntimeAuthStore, public_user
from apps.api.runtime_logging import client_ip_from_request, request_id_from_request
from apps.api.runtime_store import safe_id


PUBLIC_PREFIXES = ("/auth", "/health", "/capabilities", "/community", "/site", "/studio")


def register_runtime_auth_routes(app: FastAPI, auth: RuntimeAuthStore) -> None:
    @app.get("/auth/status")
    def auth_status(request: Request) -> dict[str, Any]:
        user = auth.user_from_request(request) if auth.enabled() else None
        return {
            "auth_required": auth.enabled(),
            "authenticated": bool(user),
            "user": public_user(user) if user else None,
            "invite_registration_available": auth.invite_registration_available(),
            "session_ttl_hours": auth.session_ttl_hours(),
        }

    @app.get("/auth/me")
    def auth_me(request: Request) -> dict[str, Any]:
        return {"user": public_user(auth.require_user(request))}

    @app.post("/auth/register")
    def auth_register(body: AuthRegisterRequest, request: Request) -> dict[str, Any]:
        return auth.register(body, client_ip=client_ip_from_request(request), request_id=request_id_from_request(request))

    @app.post("/auth/login")
    def auth_login(body: AuthLoginRequest, request: Request) -> dict[str, Any]:
        return auth.login(body, client_ip=client_ip_from_request(request), request_id=request_id_from_request(request))

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


__all__ = ("configure_runtime_auth_middleware", "register_runtime_auth_routes")
