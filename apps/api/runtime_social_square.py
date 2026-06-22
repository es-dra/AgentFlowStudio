from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from agentflow.harness.json_io import write_json
from apps.api.runtime_auth import RuntimeAuthStore
from apps.api.runtime_store import RuntimeStore, read_json, reject_unsafe_payload, safe_id


NeedType = Literal["script", "image", "video", "workflow", "other"]
Visibility = Literal["public", "logged_in"]


class SocialSquareCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=80)
    body: str = Field(min_length=4, max_length=1200)
    need_type: NeedType = "other"
    deliverable_hint: str = Field(default="", max_length=240)
    visibility: Visibility = "public"
    project_id: str | None = Field(default=None, max_length=120)


class SocialSquareSubmitRequest(BaseModel):
    text: str = Field(min_length=2, max_length=1200)
    project_id: str | None = Field(default=None, max_length=120)
    artifact_id: str | None = Field(default=None, max_length=160)


class SocialSquareReportRequest(BaseModel):
    reason: str = Field(min_length=2, max_length=400)


def register_runtime_social_square_routes(app: FastAPI, store: RuntimeStore, auth: RuntimeAuthStore) -> None:
    square = SocialSquareStore(store)

    @app.get("/community/requests")
    def list_social_requests() -> dict[str, Any]:
        records = [item for item in square.list_requests() if item.get("status") != "hidden"]
        return {"requests": [public_request(item) for item in records]}

    @app.get("/community/requests/{request_id}")
    def get_social_request(request_id: str) -> dict[str, Any]:
        return {"request": public_request(square.get_request(request_id))}

    @app.post("/community/requests")
    def create_social_request(request: Request, body: SocialSquareCreateRequest) -> dict[str, Any]:
        return {"request": public_request(square.create_request(body, _required_user(auth, request)))}

    @app.post("/community/requests/{request_id}/accept")
    def accept_social_request(request_id: str, request: Request) -> dict[str, Any]:
        return {"request": public_request(square.transition(request_id, _required_user(auth, request), action="accept"))}

    @app.post("/community/requests/{request_id}/submit")
    def submit_social_request(request_id: str, request: Request, body: SocialSquareSubmitRequest) -> dict[str, Any]:
        record = square.transition(request_id, _required_user(auth, request), action="submit", payload=body.model_dump())
        return {"request": public_request(record)}

    @app.post("/community/requests/{request_id}/complete")
    def complete_social_request(request_id: str, request: Request) -> dict[str, Any]:
        return {"request": public_request(square.transition(request_id, _required_user(auth, request), action="complete"))}

    @app.post("/community/requests/{request_id}/close")
    def close_social_request(request_id: str, request: Request) -> dict[str, Any]:
        return {"request": public_request(square.transition(request_id, _required_user(auth, request), action="close"))}

    @app.post("/community/requests/{request_id}/report")
    def report_social_request(request_id: str, request: Request, body: SocialSquareReportRequest) -> dict[str, Any]:
        record = square.transition(request_id, _required_user(auth, request), action="report", payload=body.model_dump())
        return {"request": public_request(record)}


class SocialSquareStore:
    def __init__(self, store: RuntimeStore) -> None:
        self.root = store.root / "community" / "social_square"
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "index.json"
        self.events_path = self.root / "events.jsonl"

    def list_requests(self) -> list[dict[str, Any]]:
        items = list(self._index()["requests"].values())
        return sorted(items, key=lambda item: str(item.get("updated_at", "")), reverse=True)

    def get_request(self, request_id: str) -> dict[str, Any]:
        record = self._index()["requests"].get(safe_id(request_id))
        if not record:
            raise HTTPException(status_code=404, detail="community request not found")
        return dict(record)

    def create_request(self, body: SocialSquareCreateRequest, user: dict[str, Any]) -> dict[str, Any]:
        now = _now()
        record = {
            "request_id": f"req_{uuid4().hex[:12]}",
            "title": _clean(body.title, 80),
            "body": _clean(body.body, 1200),
            "need_type": body.need_type,
            "deliverable_hint": _clean(body.deliverable_hint, 240),
            "visibility": body.visibility,
            "project_id": _clean(body.project_id or "", 120),
            "status": "open",
            "author_user_id": str(user["user_id"]),
            "author_display_name": _public_name(user),
            "accepted_by_user_id": "",
            "accepted_by_display_name": "",
            "submission": None,
            "safe_public_summary": _summary(body.body),
            "report_count": 0,
            "created_at": now,
            "updated_at": now,
        }
        return self._save(record, actor=user, event_type="created")

    def transition(
        self,
        request_id: str,
        user: dict[str, Any],
        *,
        action: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = self.get_request(request_id)
        actor_id = str(user["user_id"])
        if action == "accept":
            _require_status(record, {"open"})
            if record["author_user_id"] == actor_id:
                raise HTTPException(status_code=403, detail="author cannot accept own request")
            record["status"] = "accepted"
            record["accepted_by_user_id"] = actor_id
            record["accepted_by_display_name"] = _public_name(user)
        elif action == "submit":
            _require_status(record, {"accepted", "submitted"})
            if record.get("accepted_by_user_id") != actor_id:
                raise HTTPException(status_code=403, detail="only assignee can submit")
            data = payload or {}
            record["status"] = "submitted"
            record["submission"] = {
                "text": _clean(str(data.get("text") or ""), 1200),
                "project_id": _clean(str(data.get("project_id") or ""), 120),
                "artifact_id": _clean(str(data.get("artifact_id") or ""), 160),
                "created_at": _now(),
            }
        elif action == "complete":
            _require_author(record, actor_id)
            _require_status(record, {"accepted", "submitted"})
            record["status"] = "completed"
        elif action == "close":
            _require_author(record, actor_id)
            if record.get("status") in {"completed", "hidden"}:
                raise HTTPException(status_code=409, detail="request cannot be closed")
            record["status"] = "closed"
        elif action == "report":
            record["report_count"] = int(record.get("report_count") or 0) + 1
        else:
            raise HTTPException(status_code=422, detail="unsupported action")
        record["updated_at"] = _now()
        return self._save(record, actor=user, event_type=action, payload=payload or {})

    def _save(self, record: dict[str, Any], *, actor: dict[str, Any], event_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        reject_unsafe_payload(record)
        index = self._index()
        index["requests"][safe_id(str(record["request_id"]))] = record
        write_json(self.index_path, index)
        self._append_event(record, actor=actor, event_type=event_type, payload=payload or {})
        return dict(record)

    def _index(self) -> dict[str, Any]:
        default = {"schema_version": "0.1.0", "requests": {}}
        if not self.index_path.exists():
            write_json(self.index_path, default)
            return default
        payload = read_json(self.index_path)
        payload.setdefault("schema_version", "0.1.0")
        if not isinstance(payload.get("requests"), dict):
            payload["requests"] = {}
        return payload

    def _append_event(self, record: dict[str, Any], *, actor: dict[str, Any], event_type: str, payload: dict[str, Any]) -> None:
        event = {
            "event_id": f"evt_{uuid4().hex[:12]}",
            "event_type": event_type,
            "request_id": record["request_id"],
            "actor_user_id": str(actor["user_id"]),
            "created_at": _now(),
            "payload": {key: _clean(str(value), 400) for key, value in payload.items() if value is not None},
        }
        reject_unsafe_payload(event)
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def public_request(record: dict[str, Any]) -> dict[str, Any]:
    submission = record.get("submission") if isinstance(record.get("submission"), dict) else None
    return {
        "request_id": str(record.get("request_id") or ""),
        "title": str(record.get("title") or ""),
        "need_type": str(record.get("need_type") or "other"),
        "deliverable_hint": str(record.get("deliverable_hint") or ""),
        "visibility": str(record.get("visibility") or "public"),
        "status": str(record.get("status") or "open"),
        "author_display_name": str(record.get("author_display_name") or ""),
        "accepted_by_display_name": str(record.get("accepted_by_display_name") or ""),
        "safe_public_summary": str(record.get("safe_public_summary") or ""),
        "submission": _public_submission(submission),
        "report_count": int(record.get("report_count") or 0),
        "created_at": str(record.get("created_at") or ""),
        "updated_at": str(record.get("updated_at") or ""),
    }


def _public_submission(submission: dict[str, Any] | None) -> dict[str, Any] | None:
    if not submission:
        return None
    return {
        "text": str(submission.get("text") or ""),
        "project_id": str(submission.get("project_id") or ""),
        "artifact_id": str(submission.get("artifact_id") or ""),
        "created_at": str(submission.get("created_at") or ""),
    }


def _required_user(auth: RuntimeAuthStore, request: Request) -> dict[str, Any]:
    if auth.enabled():
        return auth.require_user(request)
    return {"user_id": "local_runtime_user", "display_name": "Local User", "email": ""}


def _require_author(record: dict[str, Any], actor_id: str) -> None:
    if record.get("author_user_id") != actor_id:
        raise HTTPException(status_code=403, detail="only author can change request")


def _require_status(record: dict[str, Any], allowed: set[str]) -> None:
    if record.get("status") not in allowed:
        raise HTTPException(status_code=409, detail="request status does not allow this action")


def _public_name(user: dict[str, Any]) -> str:
    return _clean(str(user.get("display_name") or user.get("user_id") or "user"), 80)


def _summary(value: str) -> str:
    return _clean(" ".join(str(value).split()), 180)


def _clean(value: str, max_length: int) -> str:
    return " ".join(str(value or "").replace("\x00", "").split())[:max_length]


def _now() -> str:
    return datetime.now(UTC).isoformat()


__all__ = ("SocialSquareStore", "public_request", "register_runtime_social_square_routes")
