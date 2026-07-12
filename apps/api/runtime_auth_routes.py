from __future__ import annotations

from typing import Any
from urllib.parse import unquote

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from apps.api.runtime_auth import AuthLoginRequest, AuthRegisterRequest, RuntimeAuthStore, public_user
from apps.api.runtime_errors import safe_error_detail
from apps.api.runtime_logging import (
    client_ip_from_request,
    client_request_id_from_request,
    log_business_event,
    request_id_from_request,
    studio_node_id_from_request,
    studio_node_type_from_request,
    user_action_from_request,
)
from apps.api.runtime_store import safe_id


PUBLIC_PREFIXES = ("/auth", "/health", "/capabilities", "/community", "/site", "/studio")
PUBLIC_PATHS = {"/studio/client-events"}


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
            detail = _auth_error_detail(request, "authentication_required", "需要登录后才能继续操作。", "请重新登录后再试。", stage="auth")
            _log_auth_rejected(request, detail, status_code=401)
            return JSONResponse(status_code=401, content={"detail": detail})
        request.state.afs_user = user
        project_id = _project_id_from_path(request.url.path)
        if project_id and not auth.user_can_access_project(str(user["user_id"]), project_id):
            detail = _auth_error_detail(request, "project_access_denied", "当前账号没有访问该项目的权限。", "请切换到有权限的账号，或重新选择自己的项目。", project_id=project_id, stage="auth")
            _log_auth_rejected(request, detail, status_code=403)
            return JSONResponse(status_code=403, content={"detail": detail})
        return await call_next(request)


def _is_public_request(request: Request) -> bool:
    path = request.url.path
    if request.method == "OPTIONS":
        return True
    return path in PUBLIC_PATHS or path == "/" or path == "/favicon.ico" or path.startswith(PUBLIC_PREFIXES)


def _project_id_from_path(path: str) -> str:
    parts = [part for part in path.split("/") if part]
    if len(parts) >= 2 and parts[0] == "projects":
        return safe_id(unquote(parts[1]))
    return ""


def _auth_error_detail(
    request: Request,
    error: str,
    message: str,
    user_action: str,
    *,
    project_id: str = "",
    stage: str = "auth",
) -> dict[str, Any]:
    return safe_error_detail(
        error,
        message=message,
        user_action=user_action,
        request_id=request_id_from_request(request),
        client_request_id=client_request_id_from_request(request),
        project_id=project_id,
        node_id=studio_node_id_from_request(request),
        action="auth",
        stage=stage,
    )


def _log_auth_rejected(request: Request, detail: dict[str, Any], *, status_code: int) -> None:
    log_business_event(
        "runtime_request_rejected",
        request_id=detail.get("request_id"),
        client_request_id=detail.get("client_request_id"),
        user_action=user_action_from_request(request),
        studio_node_id=detail.get("node_id") or studio_node_id_from_request(request),
        studio_node_type=studio_node_type_from_request(request),
        method=request.method,
        path=request.url.path,
        project_id=detail.get("project_id"),
        action=detail.get("action"),
        stage=detail.get("stage"),
        error=detail.get("error"),
        status_code=status_code,
        retryable=detail.get("retryable"),
    )


__all__ = ("configure_runtime_auth_middleware", "register_runtime_auth_routes")
