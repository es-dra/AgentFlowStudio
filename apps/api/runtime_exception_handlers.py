from __future__ import annotations

import logging
from typing import Any
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from apps.api.runtime_errors import safe_error_detail, safe_public_details, safe_public_text
from apps.api.runtime_logging import (
    REQUEST_LOGGER_NAME,
    client_request_id_from_request,
    log_business_event,
    request_id_from_request,
    studio_node_id_from_request,
    studio_node_type_from_request,
    user_action_from_request,
)
from apps.api.runtime_store import safe_id


def configure_runtime_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def runtime_http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        detail = normalize_http_error_detail(request, exc)
        log_runtime_rejection(request, detail, status_code=exc.status_code)
        return JSONResponse(status_code=exc.status_code, content={"detail": detail})

    @app.exception_handler(RequestValidationError)
    async def runtime_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        detail = validation_error_detail(request, exc)
        log_runtime_rejection(request, detail, status_code=422)
        return JSONResponse(status_code=422, content={"detail": detail})

    @app.exception_handler(Exception)
    async def runtime_unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        detail = unhandled_exception_detail(request)
        logging.getLogger(REQUEST_LOGGER_NAME).exception(
            "runtime_unhandled_exception %s",
            {
                "request_id": detail.get("request_id"),
                "client_request_id": detail.get("client_request_id"),
                "method": request.method,
                "path": request.url.path,
                "action": detail.get("action"),
                "stage": detail.get("stage"),
                "error": detail.get("error"),
            },
        )
        log_runtime_rejection(request, detail, status_code=500)
        return JSONResponse(status_code=500, content={"detail": detail})


def normalize_http_error_detail(request: Request, exc: HTTPException) -> dict[str, Any]:
    raw = exc.detail
    if isinstance(raw, dict):
        base = dict(raw)
        error = str(base.get("error") or base.get("detail_code") or error_code_for_status(exc.status_code, request.url.path))
        message = str(base.get("message") or message_for_error(error, exc.status_code) or "")
        user_action = str(base.get("user_action") or user_action_for_error(error) or "")
        details = base.get("details") if isinstance(base.get("details"), dict) else {}
    else:
        error = error_code_for_detail(str(raw or ""), exc.status_code, request.url.path)
        message = message_for_error(error, exc.status_code, fallback=str(raw or ""))
        user_action = user_action_for_error(error)
        details = {"raw_detail": str(raw or "")[:160]} if raw else {}
    context = request_context(request)
    path_project_id = project_id_from_path(request.url.path)
    return safe_error_detail(
        error,
        message=message,
        user_action=user_action,
        request_id=context["request_id"],
        client_request_id=context["client_request_id"],
        project_id=str((raw if isinstance(raw, dict) else {}).get("project_id") or path_project_id),
        node_id=str((raw if isinstance(raw, dict) else {}).get("node_id") or context["node_id"]),
        action=str((raw if isinstance(raw, dict) else {}).get("action") or action_from_path(request.url.path)),
        stage=str((raw if isinstance(raw, dict) else {}).get("stage") or stage_for_status(exc.status_code)),
        status="failed",
        retryable=bool((raw if isinstance(raw, dict) else {}).get("retryable", exc.status_code in {408, 409, 429, 500, 502, 503, 504})),
        details=safe_public_details(details),
    )


def validation_error_detail(request: Request, exc: RequestValidationError) -> dict[str, Any]:
    errors = exc.errors()
    fields = []
    for item in errors[:8]:
        loc = item.get("loc") if isinstance(item, dict) else None
        msg = item.get("msg") if isinstance(item, dict) else ""
        fields.append({
            "field": ".".join(str(part) for part in loc or []),
            "message": safe_public_text(msg, fallback="invalid field"),
            "type": safe_public_text(item.get("type") if isinstance(item, dict) else "", fallback=""),
        })
    context = request_context(request)
    return safe_error_detail(
        "request_validation_failed",
        message="请求参数校验失败。",
        user_action="请检查页面填写内容是否完整，或刷新页面后重试。",
        request_id=context["request_id"],
        client_request_id=context["client_request_id"],
        project_id=project_id_from_path(request.url.path),
        node_id=context["node_id"],
        action=action_from_path(request.url.path),
        stage="request_validation",
        details={"fields": fields, "error_count": len(errors)},
    )


def unhandled_exception_detail(request: Request) -> dict[str, Any]:
    context = request_context(request)
    return safe_error_detail(
        "runtime_internal_error",
        message="运行服务内部错误。",
        user_action="请复制请求编号给测试或开发人员排查。",
        request_id=context["request_id"],
        client_request_id=context["client_request_id"],
        project_id=project_id_from_path(request.url.path),
        node_id=context["node_id"],
        action=action_from_path(request.url.path),
        stage="runtime",
        retryable=True,
    )


def log_runtime_rejection(request: Request, detail: dict[str, Any], *, status_code: int) -> None:
    details = detail.get("details") if isinstance(detail.get("details"), dict) else {}
    log_business_event(
        "runtime_request_rejected",
        request_id=detail.get("request_id") or request_id_from_request(request),
        client_request_id=detail.get("client_request_id") or client_request_id_from_request(request),
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
        **details,
    )


def request_context(request: Request) -> dict[str, str]:
    return {
        "request_id": request_id_from_request(request),
        "client_request_id": client_request_id_from_request(request),
        "node_id": studio_node_id_from_request(request),
    }


def error_code_for_status(status_code: int, path: str) -> str:
    if status_code == 400:
        return "bad_request"
    if status_code == 401:
        return "authentication_required"
    if status_code == 403:
        return "permission_denied"
    if status_code == 404:
        if "image-assets" in path:
            return "image_asset_not_found"
        if "visual-assets" in path:
            return "visual_asset_not_found"
        if "candidates" in path:
            return "candidate_not_found"
        if "jobs" in path or "/runs/" in path or "generations" in path:
            return "job_not_found"
        return "not_found"
    if status_code == 409:
        return "conflict"
    if status_code == 422:
        return "invalid_request"
    if status_code == 429:
        return "rate_limited"
    return "runtime_error" if status_code >= 500 else "request_failed"


def error_code_for_detail(detail: str, status_code: int, path: str) -> str:
    text = detail.lower().strip()
    mapping = {
        "authentication required": "authentication_required",
        "project access denied": "project_access_denied",
        "image asset not found": "image_asset_not_found",
        "visual asset not found": "visual_asset_not_found",
        "candidate not found": "candidate_not_found",
        "job not found": "job_not_found",
        "artifact not found": "artifact_not_found",
        "studio state version conflict": "studio_state_conflict",
        "too many authentication attempts; retry later": "auth_rate_limited",
        "email already registered": "email_already_registered",
        "invalid email or password": "invalid_email_or_password",
        "invite code is invalid or already used": "invalid_invite_code",
    }
    return mapping.get(text) or error_code_for_status(status_code, path)


def message_for_error(error: str, status_code: int, fallback: str = "") -> str:
    messages = {
        "authentication_required": "需要登录后才能继续操作。",
        "project_access_denied": "当前账号没有访问该项目的权限。",
        "permission_denied": "当前账号没有权限执行该操作。",
        "image_asset_not_found": "图片素材不存在或已失效。",
        "visual_asset_not_found": "固定视觉资产不存在或已失效。",
        "candidate_not_found": "生成候选结果不存在或已失效。",
        "job_not_found": "生成任务不存在或已失效。",
        "artifact_not_found": "产物记录不存在或已失效。",
        "studio_state_conflict": "画布状态版本冲突。",
        "auth_rate_limited": "登录或注册尝试过于频繁。",
        "email_already_registered": "该邮箱已经注册。",
        "invalid_email_or_password": "邮箱或密码不正确。",
        "invalid_invite_code": "邀请码无效或已被使用。",
        "bad_request": "请求内容不正确。",
        "invalid_request": "请求参数无效。",
        "not_found": "请求的资源不存在。",
        "conflict": "当前操作与最新状态冲突。",
        "rate_limited": "请求过于频繁。",
        "runtime_error": "运行服务内部错误。",
    }
    return messages.get(error) or safe_public_text(fallback, fallback="") or default_message_for_status(status_code)


def user_action_for_error(error: str) -> str:
    actions = {
        "authentication_required": "请重新登录后再试。",
        "project_access_denied": "请切换到有权限的账号，或重新选择自己的项目。",
        "image_asset_not_found": "请重新上传图片素材，并重新选择引用。",
        "visual_asset_not_found": "请刷新素材库，确认资产仍存在。",
        "candidate_not_found": "请重新生成或刷新任务状态。",
        "job_not_found": "请确认任务是否属于当前项目，必要时重新生成。",
        "artifact_not_found": "请刷新页面后重试，或重新生成相关结果。",
        "studio_state_conflict": "请刷新页面获取最新画布状态后再修改。",
        "auth_rate_limited": "请稍后再试。",
        "email_already_registered": "请直接登录，或换一个邮箱注册。",
        "invalid_email_or_password": "请检查邮箱和密码后重试。",
        "invalid_invite_code": "请确认邀请码是否正确，或联系管理员获取新邀请码。",
        "rate_limited": "请稍后再试。",
    }
    return actions.get(error, "")


def default_message_for_status(status_code: int) -> str:
    if status_code == 400:
        return "请求内容不正确。"
    if status_code == 401:
        return "需要登录后才能继续操作。"
    if status_code == 403:
        return "当前账号没有权限执行该操作。"
    if status_code == 404:
        return "请求的资源不存在。"
    if status_code == 409:
        return "当前操作与最新状态冲突。"
    if status_code == 422:
        return "请求参数无效。"
    if status_code == 429:
        return "请求过于频繁。"
    if status_code >= 500:
        return "运行服务内部错误。"
    return "请求失败。"


def stage_for_status(status_code: int) -> str:
    if status_code in {400, 422}:
        return "request_validation"
    if status_code in {401, 403}:
        return "auth"
    if status_code == 404:
        return "resource_lookup"
    if status_code == 409:
        return "state_conflict"
    if status_code == 429:
        return "rate_limit"
    if status_code >= 500:
        return "runtime"
    return "request"


def action_from_path(path: str) -> str:
    if "/video-generations" in path:
        return "video_generation"
    if "/keyframe-generations" in path:
        return "keyframe_generation"
    if "/video-revisions" in path:
        return "video_revision"
    if "/prompt-optimizations" in path:
        return "prompt_optimization"
    if "/storyboard-breakdowns" in path:
        return "storyboard_breakdown"
    if "/shot-asset-plans" in path:
        return "shot_asset_plan"
    if "/image-assets" in path:
        return "image_asset"
    if "/asset-card-drafts" in path:
        return "asset_card_draft"
    if "/visual-assets" in path:
        return "visual_asset"
    if "/studio-state" in path:
        return "studio_state"
    if "/sprite/" in path:
        return "sprite"
    if "/community/" in path:
        return "community"
    if path.startswith("/auth/"):
        return "auth"
    return ""


def project_id_from_path(path: str) -> str:
    parts = [part for part in path.split("/") if part]
    if len(parts) >= 2 and parts[0] == "projects":
        return safe_id(unquote(parts[1]))
    return ""


__all__ = (
    "configure_runtime_exception_handlers",
    "normalize_http_error_detail",
    "validation_error_detail",
)
