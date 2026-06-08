from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_tool_catalog_contract(path: str | Path) -> dict[str, Any]:
    catalog_path = Path(path)
    payload = _load_yaml(catalog_path)
    if not isinstance(payload, dict):
        return {}

    if isinstance(payload.get("tools"), list):
        return payload

    parts = payload.get("tool_catalog_parts")
    if not isinstance(parts, list):
        return payload

    tools: list[dict[str, Any]] = []
    for relative_part in parts:
        if not isinstance(relative_part, str):
            continue
        part_payload = _load_yaml(catalog_path.parent / relative_part)
        part_tools = part_payload.get("tools") if isinstance(part_payload, dict) else None
        if isinstance(part_tools, list):
            tools.extend(tool for tool in part_tools if isinstance(tool, dict))

    return {
        **payload,
        "tools": tools,
    }


def load_workflow_tool_catalog(path: str | Path | None) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    payload = load_tool_catalog_contract(path)
    tools = payload.get("tools")
    if not isinstance(tools, list):
        return {}

    catalog: dict[str, dict[str, Any]] = {}
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        node_name = _workflow_node_name(tool)
        if node_name:
            catalog[node_name] = tool
    return catalog


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _workflow_node_name(tool: dict[str, Any]) -> str | None:
    entrypoints = tool.get("entrypoints")
    if isinstance(entrypoints, dict) and entrypoints.get("workflow_node"):
        return str(entrypoints["workflow_node"])
    if tool.get("name"):
        return str(tool["name"])
    return None
