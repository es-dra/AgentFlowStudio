from __future__ import annotations

import json
from pathlib import Path

import typer
from pydantic import ValidationError

from agentflow_studio.schemas import ClipPlan, Hook, ShortVideoScript


def load_hooks(hooks_path: Path) -> list[Hook]:
    try:
        payload = json.loads(hooks_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"Hooks file is not valid JSON: {exc.msg}") from exc
    if not isinstance(payload, list):
        raise typer.BadParameter("Hooks file must contain a JSON array.")
    try:
        return [Hook.model_validate(item) for item in payload]
    except ValidationError as exc:
        raise typer.BadParameter(f"Hooks file failed Hook schema validation: {exc}") from exc


def load_scripts(scripts_path: Path) -> list[ShortVideoScript]:
    payload = _load_json_array(scripts_path, "Scripts")
    try:
        return [ShortVideoScript.model_validate(item) for item in payload]
    except ValidationError as exc:
        raise typer.BadParameter(f"Scripts file failed ShortVideoScript schema validation: {exc}") from exc


def load_clip_plans(clip_plans_path: Path) -> list[ClipPlan]:
    payload = _load_json_array(clip_plans_path, "Clip plans")
    try:
        return [ClipPlan.model_validate(item) for item in payload]
    except ValidationError as exc:
        raise typer.BadParameter(f"Clip plans file failed ClipPlan schema validation: {exc}") from exc


def _load_json_array(path: Path, label: str) -> list[object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"{label} file is not valid JSON: {exc.msg}") from exc
    if not isinstance(payload, list):
        raise typer.BadParameter(f"{label} file must contain a JSON array.")
    return payload
