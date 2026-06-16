from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


TASK_PACKET_RELATIVE = (
    "10-Startup/80-Workflow/ai-native-company-workflow/task-startup-packets/"
    "2026-06-17-afs-provider-connected-validation.md"
)
DEFAULT_KB_ROOT = Path(r"D:\Learning materials\Learning_notes")
TRUE_VALUES = {"1", "true", "yes", "on"}
REQUIRED_ACTIONS = {
    "prompt_optimization",
    "asset_card_draft",
    "keyframe_generation",
    "video_generation",
    "record_feedback",
}
OPTIONAL_ACTIONS = {"video_asset_register"}
REQUIRED_LIVE_GATES = {"llm": "AFS_ALLOW_REMOTE_LLM", "image": "AFS_ALLOW_REMOTE_IMAGE"}
OPTIONAL_LIVE_GATES = {"video": "AFS_ALLOW_REMOTE_VIDEO", "vision": "AFS_ALLOW_REMOTE_VISION"}


def main() -> int:
    args = parse_args()
    report = build_readiness_report(repo_root=Path(args.repo_root), kb_root=Path(args.kb_root))
    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] in {"ready_for_authorization", "ready_for_provider_smoke"} else 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a no-cost AFS provider-connected validation readiness report.")
    parser.add_argument("--repo-root", default=str(ROOT))
    parser.add_argument("--kb-root", default=str(DEFAULT_KB_ROOT))
    parser.add_argument("--report", default="")
    return parser.parse_args()


def build_readiness_report(*, repo_root: Path, kb_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    kb_root = kb_root.resolve()
    runtime = _runtime_surface()
    provider_config = _provider_config_state(repo_root)
    gates = _gate_state(runtime.get("provider_gates") or {})
    packet = _task_packet_state(kb_root)
    missing_actions = sorted(REQUIRED_ACTIONS.difference(runtime.get("actions") or []))
    missing_optional_actions = sorted(OPTIONAL_ACTIONS.difference(runtime.get("actions") or []))
    readiness_blocks = _readiness_blocks(
        packet_present=packet["present"],
        missing_actions=missing_actions,
        provider_config=provider_config,
    )
    status = _status(readiness_blocks, provider_config, gates)
    return {
        "artifact_type": "afs_provider_connected_validation_readiness",
        "schema_version": "0.1.0",
        "status": status,
        "task_packet": packet,
        "runtime_surface": {
            "health_status": runtime.get("health_status"),
            "required_actions_present": not missing_actions,
            "missing_actions": missing_actions,
            "missing_optional_actions": missing_optional_actions,
            "provider_gates": gates,
        },
        "provider_config": provider_config,
        "required_authorizations": _required_authorizations(gates),
        "readiness_blocks": readiness_blocks,
        "next_actions": _next_actions(status, readiness_blocks, gates),
        "secrets_printed": False,
        "provider_calls_started": False,
        "non_claims": [
            "no-cost readiness only",
            "not live provider smoke",
            "not human acceptance",
            "not business validation",
            "not durable memory",
        ],
    }


def _runtime_surface() -> dict[str, Any]:
    with TemporaryDirectory(prefix="afs-provider-readiness-") as runtime_root:
        client = TestClient(create_runtime_app(runtime_root=Path(runtime_root)))
        health = client.get("/health").json()
        capabilities = client.get("/capabilities").json()
    return {
        "health_status": health.get("status"),
        "provider_gates": health.get("provider_gates") or {},
        "actions": set(capabilities.get("actions") or []),
    }


def _provider_config_state(repo_root: Path) -> dict[str, Any]:
    env_value = os.environ.get("AFS_PROVIDER_CONFIG", "").strip()
    if env_value:
        return {
            "source": "AFS_PROVIDER_CONFIG",
            "present": Path(env_value).is_file(),
            "path_disclosed": False,
            "example_only": False,
        }
    local_path = repo_root / "configs" / "providers.local.json"
    if local_path.is_file():
        return {
            "source": "configs/providers.local.json",
            "present": True,
            "path_disclosed": False,
            "example_only": False,
        }
    example_path = repo_root / "configs" / "providers.example.json"
    return {
        "source": "configs/providers.example.json",
        "present": example_path.is_file(),
        "path_disclosed": False,
        "example_only": True,
    }


def _gate_state(runtime_gates: dict[str, Any]) -> dict[str, dict[str, Any]]:
    gates: dict[str, dict[str, Any]] = {}
    for capability, env_name in {**REQUIRED_LIVE_GATES, **OPTIONAL_LIVE_GATES}.items():
        gates[capability] = {
            "env": env_name,
            "enabled": bool(runtime_gates.get(capability)) or _env_enabled(env_name),
        }
    return gates


def _task_packet_state(kb_root: Path) -> dict[str, Any]:
    packet = kb_root / TASK_PACKET_RELATIVE
    return {
        "present": packet.is_file(),
        "relative_path": TASK_PACKET_RELATIVE,
    }


def _readiness_blocks(
    *,
    packet_present: bool,
    missing_actions: list[str],
    provider_config: dict[str, Any],
) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    if not packet_present:
        blocks.append({"block_id": "gfr_provider_validation_packet_missing", "claim_boundary": "no_task_startup_packet"})
    if missing_actions:
        blocks.append({"block_id": "runtime_actions_missing", "missing_actions": missing_actions})
    if not provider_config["present"]:
        blocks.append({"block_id": "provider_config_missing", "source": provider_config["source"]})
    return blocks


def _status(readiness_blocks: list[dict[str, Any]], provider_config: dict[str, Any], gates: dict[str, dict[str, Any]]) -> str:
    if readiness_blocks:
        return "blocked"
    if provider_config["example_only"]:
        return "needs_local_provider_config"
    if any(not gates[name]["enabled"] for name in REQUIRED_LIVE_GATES):
        return "ready_for_authorization"
    return "ready_for_provider_smoke"


def _required_authorizations(gates: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "required_before_live_provider_smoke": [
            gate["env"] for name, gate in gates.items() if name in REQUIRED_LIVE_GATES and not gate["enabled"]
        ],
        "optional_for_video_or_asset_card": [
            gate["env"] for name, gate in gates.items() if name in OPTIONAL_LIVE_GATES and not gate["enabled"]
        ],
        "human_approval_required": True,
        "current_session_approval_inferred_from_env": False,
        "minimum_live_scope": "one LLM + image/keyframe provider smoke with candidate_count=1",
    }


def _next_actions(status: str, readiness_blocks: list[dict[str, Any]], gates: dict[str, dict[str, Any]]) -> list[str]:
    if readiness_blocks:
        return [f"Resolve readiness block: {block['block_id']}" for block in readiness_blocks]
    if status == "needs_local_provider_config":
        return ["Create ignored local provider config or set AFS_PROVIDER_CONFIG before live provider smoke."]
    if status == "ready_for_authorization":
        return [
            "Ask the human to authorize exactly the needed provider gates.",
            "For minimum image/keyframe smoke, open AFS_ALLOW_REMOTE_LLM and AFS_ALLOW_REMOTE_IMAGE only.",
            "Keep AFS_ALLOW_REMOTE_VIDEO and external download closed unless video smoke is explicitly in scope.",
        ]
    if status == "ready_for_provider_smoke":
        return [
            "Ask the human to authorize the exact live provider scope before spending provider calls.",
            "Run one provider-connected validation with candidate_count=1.",
            "Record runtime verification, provider smoke, human scoring, and business validation separately.",
        ]
    return []


def _env_enabled(env_name: str) -> bool:
    return os.environ.get(env_name, "").strip().lower() in TRUE_VALUES


if __name__ == "__main__":
    raise SystemExit(main())
