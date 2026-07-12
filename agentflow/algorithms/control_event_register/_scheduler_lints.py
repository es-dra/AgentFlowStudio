from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Mapping


CONTROL_SCHEDULER_LINT_VERSION = "0.1.0"

COMPLETED_BU_NOT_PROCESSED = "completed_bu_not_processed"
JOIN_ALL_WITHOUT_REASON = "join_all_without_reason"
SINGLE_ACTIVE_LANE_WITHOUT_DEPENDENCY_REASON = "single_active_lane_without_dependency_reason"
LANE_PAST_STALE_AFTER_WITHOUT_RECOVERY_OUTCOME = "lane_past_stale_after_without_recovery_outcome"
POST_CLOSEOUT_NEXT_ACTION_WITHOUT_REAL_WAKEUP_MONITOR = "post_closeout_next_action_without_real_wakeup_monitor"

CONTROL_SCHEDULER_LINT_CODES = frozenset(
    (
        COMPLETED_BU_NOT_PROCESSED,
        JOIN_ALL_WITHOUT_REASON,
        SINGLE_ACTIVE_LANE_WITHOUT_DEPENDENCY_REASON,
        LANE_PAST_STALE_AFTER_WITHOUT_RECOVERY_OUTCOME,
        POST_CLOSEOUT_NEXT_ACTION_WITHOUT_REAL_WAKEUP_MONITOR,
    )
)

_EXECUTABLE_WAKEUP_MONITOR_MECHANISMS = frozenset(
    (
        "automation",
        "codex_thread_monitor",
        "codex_thread_wakeup",
        "control_scheduler_monitor",
        "control_scheduler_wakeup",
        "scheduled_automation",
        "thread_monitor",
        "thread_wakeup",
    )
)

_PSEUDO_WAKEUP_MONITOR_MECHANISMS = frozenset(
    (
        "codex_delegation_response",
        "current_codex_delegation_response",
        "manual",
        "n/a",
        "none",
        "tbd",
    )
)


def lint_control_scheduler_state(
    state: Mapping[str, Any],
    *,
    now: datetime | str | None = None,
) -> list[dict[str, Any]]:
    """Return lint findings for a bounded control scheduler snapshot."""
    current_time = _coerce_datetime(now) or datetime.now(UTC)
    lanes = _lane_records(state)
    findings: list[dict[str, Any]] = []

    _lint_join_all_without_reason(state, findings)
    _lint_single_active_lane_without_dependency_reason(state, lanes, findings)
    _lint_completed_bu_not_processed(state, lanes, findings)
    _lint_stale_lanes(lanes, current_time, findings)
    _lint_post_closeout_next_actions(state, lanes, findings)

    return findings


def _lint_join_all_without_reason(state: Mapping[str, Any], findings: list[dict[str, Any]]) -> None:
    policy = _scheduler_policy(state)
    join_mode = _first_text(policy, ("join_mode", "fan_in_mode", "closeout_mode", "mode"))
    if join_mode != "join_all":
        return
    if _has_reason(policy, ("join_all_reason", "reason", "dependency_reason")):
        return
    findings.append(
        _finding(JOIN_ALL_WITHOUT_REASON, "join_all scheduler mode requires an explicit reason.",
                 field="scheduler_policy.join_all_reason")
    )


def _lint_single_active_lane_without_dependency_reason(
    state: Mapping[str, Any],
    lanes: list[Mapping[str, Any]],
    findings: list[dict[str, Any]],
) -> None:
    active_lanes = [lane for lane in lanes if _lane_state(lane) == "active"]
    if len(active_lanes) != 1:
        return
    lane = active_lanes[0]
    policy = _scheduler_policy(state)
    if _has_reason(lane, ("dependency_reason", "single_active_lane_reason", "blocked_by_reason")):
        return
    if _has_reason(policy, ("dependency_reason", "single_active_lane_reason", "single_active_dependency_reason")):
        return
    findings.append(
        _finding(SINGLE_ACTIVE_LANE_WITHOUT_DEPENDENCY_REASON,
                 "single active lane requires an explicit dependency reason.",
                 lane_id=_lane_id(lane), field="dependency_reason")
    )


def _lint_completed_bu_not_processed(
    state: Mapping[str, Any],
    lanes: list[Mapping[str, Any]],
    findings: list[dict[str, Any]],
) -> None:
    for lane in lanes:
        if not _is_completed_lane(lane):
            continue
        bu_id = _first_text(lane, ("bottom_up_feedback_id", "bu_id", "bottom_up_id"))
        if not bu_id:
            continue
        if _bu_is_processed(state, lane, bu_id):
            continue
        findings.append(
            _finding(COMPLETED_BU_NOT_PROCESSED, "completed lane bottom-up feedback is not marked processed.",
                     lane_id=_lane_id(lane), field="bottom_up_feedback_id")
        )


def _lint_stale_lanes(
    lanes: list[Mapping[str, Any]],
    current_time: datetime,
    findings: list[dict[str, Any]],
) -> None:
    for lane in lanes:
        stale_after = _coerce_datetime(lane.get("stale_after"))
        if stale_after is None or current_time <= stale_after:
            continue
        if _has_recovery_outcome(lane):
            continue
        findings.append(
            _finding(LANE_PAST_STALE_AFTER_WITHOUT_RECOVERY_OUTCOME,
                     "lane is past stale_after without a recovery outcome.",
                     lane_id=_lane_id(lane), field="stale_after")
        )


def _lint_post_closeout_next_actions(
    state: Mapping[str, Any],
    lanes: list[Mapping[str, Any]],
    findings: list[dict[str, Any]],
) -> None:
    for action in _next_actions(state):
        if _has_real_wakeup_or_monitor(action):
            continue
        findings.append(
            _finding(POST_CLOSEOUT_NEXT_ACTION_WITHOUT_REAL_WAKEUP_MONITOR,
                     "post_closeout_next_action requires a real wakeup or monitor mechanism.",
                     field="post_closeout_next_action")
        )
    for lane in lanes:
        for action in _next_actions(lane):
            if _has_real_wakeup_or_monitor(action):
                continue
            findings.append(
                _finding(POST_CLOSEOUT_NEXT_ACTION_WITHOUT_REAL_WAKEUP_MONITOR,
                         "post_closeout_next_action requires a real wakeup or monitor mechanism.",
                         lane_id=_lane_id(lane), field="post_closeout_next_action")
            )


def _finding(code: str, message: str, *, lane_id: str | None = None, field: str | None = None) -> dict[str, Any]:
    finding: dict[str, Any] = {"code": code, "severity": "error", "message": message}
    if lane_id:
        finding["lane_id"] = lane_id
    if field:
        finding["field"] = field
    return finding


def _scheduler_policy(state: Mapping[str, Any]) -> Mapping[str, Any]:
    for field in ("scheduler_policy", "control_scheduler", "scheduler"):
        value = state.get(field)
        if isinstance(value, Mapping):
            return value
    return {}


def _lane_records(state: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    lanes = state.get("lanes")
    if isinstance(lanes, Mapping):
        return [lane for lane in lanes.values() if isinstance(lane, Mapping)]
    if isinstance(lanes, list):
        return [lane for lane in lanes if isinstance(lane, Mapping)]
    return []


def _next_actions(record: Mapping[str, Any]) -> list[Any]:
    actions: list[Any] = []
    action = record.get("post_closeout_next_action")
    if _has_action(action):
        actions.append(action)
    action_list = record.get("post_closeout_next_actions")
    if isinstance(action_list, list):
        actions.extend(action for action in action_list if _has_action(action))
    return actions


def _has_action(action: Any) -> bool:
    return bool(action) if isinstance(action, Mapping) else _has_text(action)


def _has_real_wakeup_or_monitor(action: Any) -> bool:
    if not isinstance(action, Mapping):
        return False
    for field in ("wakeup_id", "monitor_id", "automation_id", "thread_wakeup_id"):
        if _has_text(action.get(field)):
            return True
    for field in ("wakeup", "monitor", "automation"):
        mechanism = action.get(field)
        if isinstance(mechanism, Mapping) and _structured_mechanism_is_real(mechanism):
            return True
    mechanism_name = _first_text(action, ("wakeup_mechanism", "monitor_mechanism", "mechanism"))
    normalized = _normalize_mechanism_name(mechanism_name)
    if not _is_executable_wakeup_monitor_mechanism(normalized):
        return False
    return _has_reason(action, ("ref", "id", "wakeup_ref", "monitor_ref", "scheduled_at", "check_at", "monitor_at"))


def _structured_mechanism_is_real(mechanism: Mapping[str, Any]) -> bool:
    if mechanism.get("enabled") is False:
        return False
    mechanism_name = _first_text(mechanism, ("mechanism", "type"))
    if not _is_executable_wakeup_monitor_mechanism(_normalize_mechanism_name(mechanism_name)):
        return False
    return _has_reason(mechanism, ("id", "ref", "scheduled_at", "check_at", "monitor_at"))


def _normalize_mechanism_name(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _is_executable_wakeup_monitor_mechanism(value: str) -> bool:
    if not value or value in _PSEUDO_WAKEUP_MONITOR_MECHANISMS:
        return False
    return value in _EXECUTABLE_WAKEUP_MONITOR_MECHANISMS


def _bu_is_processed(state: Mapping[str, Any], lane: Mapping[str, Any], bu_id: str) -> bool:
    for field in ("bottom_up_processed", "bu_processed", "bottom_up_feedback_processed"):
        if _truthy(lane.get(field)):
            return True
    for field in ("bottom_up_processed_at", "bu_processed_at", "bottom_up_feedback_processed_at"):
        if _has_text(lane.get(field)):
            return True
    for collection in (lane.get("processed_bottom_up_feedback_ids"), state.get("processed_bottom_up_feedback_ids")):
        if isinstance(collection, list) and bu_id in {str(item) for item in collection}:
            return True
    return False


def _has_recovery_outcome(lane: Mapping[str, Any]) -> bool:
    for field in ("recovery_outcome", "recovery_result", "recovery_completed_at"):
        if _has_text(lane.get(field)):
            return True
    recovery = lane.get("recovery")
    if isinstance(recovery, Mapping) and _has_reason(recovery, ("outcome", "result", "completed_at")):
        return True
    return False


def _is_completed_lane(lane: Mapping[str, Any]) -> bool:
    state = _lane_state(lane)
    if state in {"complete", "completed", "closed", "done"}:
        return True
    close_state = _first_text(lane, ("close_state",)).lower()
    return close_state.endswith("_completed") or close_state == "completed"


def _lane_state(lane: Mapping[str, Any]) -> str:
    return _first_text(lane, ("state", "lane_state")).lower()


def _lane_id(lane: Mapping[str, Any]) -> str:
    return _first_text(lane, ("lane_id", "id")) or "unknown_lane"


def _has_reason(record: Mapping[str, Any], fields: tuple[str, ...]) -> bool:
    return bool(_first_text(record, fields))


def _first_text(record: Mapping[str, Any], fields: tuple[str, ...]) -> str:
    for field in fields:
        value = record.get(field)
        if _has_text(value):
            return str(value).strip()
    return ""


def _has_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _truthy(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "processed", "done", "confirmed"}
    return False


def _coerce_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


__all__ = (
    "COMPLETED_BU_NOT_PROCESSED", "CONTROL_SCHEDULER_LINT_CODES", "CONTROL_SCHEDULER_LINT_VERSION",
    "JOIN_ALL_WITHOUT_REASON", "LANE_PAST_STALE_AFTER_WITHOUT_RECOVERY_OUTCOME",
    "POST_CLOSEOUT_NEXT_ACTION_WITHOUT_REAL_WAKEUP_MONITOR", "SINGLE_ACTIVE_LANE_WITHOUT_DEPENDENCY_REASON",
    "lint_control_scheduler_state",
)
