from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "0.1.0"
PACK_TYPE = "agentflow_loulan_human_review_pack"
LOULAN_PACKAGE_TYPE = "agentflow_loulan_memory_package"
API_PLAN_TYPE = "agentflow_loulan_api_workbench_plan"
FEEDBACK_EVENT_TYPE = "agentflow_feedback_event"
UNSAFE_OUTPUT_FRAGMENTS = (
    "D:\\",
    "C:\\",
    "file://",
    "Bearer ",
    "signed_url",
    "token=",
    "api_key",
    "secret_key",
    ".mp4",
    ".mov",
)


def validate_package(package: dict[str, Any]) -> None:
    if package.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Loulan human review pack requires package schema_version 0.1.0")
    if package.get("artifact_type") != LOULAN_PACKAGE_TYPE:
        raise ValueError(f"Loulan human review pack requires source artifact_type {LOULAN_PACKAGE_TYPE}")
    if package.get("provider_calls_started") is not False:
        raise ValueError("source Loulan package must not have provider calls started")
    if package.get("writes_long_term_memory") is not False:
        raise ValueError("source Loulan package must not write long-term memory")
    if not package.get("package_id"):
        raise ValueError("source Loulan package missing package_id")


def validate_api_plan(api_plan: dict[str, Any], package: dict[str, Any]) -> None:
    if api_plan.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Loulan human review pack requires API plan schema_version 0.1.0")
    if api_plan.get("artifact_type") != API_PLAN_TYPE:
        raise ValueError(f"Loulan human review pack requires API plan artifact_type {API_PLAN_TYPE}")
    if api_plan.get("package_id") != package.get("package_id"):
        raise ValueError("Loulan API plan package_id must match the memory package")
    if api_plan.get("provider_calls_started") is not False:
        raise ValueError("Loulan API plan must not have provider calls started")
    if api_plan.get("writes_long_term_memory") is not False:
        raise ValueError("Loulan API plan must not write long-term memory")


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing required Loulan review file: {path.name}") from exc


def safe_ref(value: Any) -> str:
    text = str(value or "").replace("\\", "/")
    if text.startswith(("D:/", "C:/", "file://")):
        return ""
    return text


def reject_unsafe_output(pack: dict[str, Any]) -> None:
    serialized = json.dumps(pack, ensure_ascii=False)
    if any(fragment.lower() in serialized.lower() for fragment in UNSAFE_OUTPUT_FRAGMENTS):
        raise ValueError("Loulan human review pack contains unsafe path, media ref, provider secret, or signed URL")
