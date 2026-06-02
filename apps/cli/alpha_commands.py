from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import typer


ALPHA_READINESS_DOC = Path("docs/alpha_readiness_report.md")
DOCS_INDEX = Path("docs/README.md")
IMAGE_ENV_VARS = [
    "AFS_ALLOW_REMOTE_IMAGE",
    "AFS_IMAGE_PROVIDER",
    "AFS_IMAGE_BASE_URL",
    "AFS_IMAGE_API_KEY",
    "AFS_IMAGE_MODEL",
]


def alpha_smoke_command(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print the alpha smoke readiness summary as JSON.",
    ),
) -> None:
    """Print a read-only Alpha smoke readiness summary without provider calls."""
    summary = build_alpha_smoke_readiness()
    if json_output:
        typer.echo(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        for line in format_alpha_smoke_readiness(summary):
            typer.echo(line)
    if summary["status"] == "fail":
        raise typer.Exit(code=1)


def build_alpha_smoke_readiness() -> dict[str, Any]:
    checks = [
        _agentflow_production_handoff_check(),
        _agentflow_studio_package_check(),
        _posterflow_live_smoke_check(),
    ]
    return {
        "schema_version": "alpha_smoke_readiness.v1",
        "status": _overall_status(checks),
        "claim_boundary": "engineering_readiness_only",
        "remote_provider_policy": {
            "llm": "not_used",
            "asr": "not_used",
            "image": "disabled_by_default",
            "video": "not_used",
        },
        "writes_runtime_artifacts": False,
        "evidence_refs": [_display_ref(ALPHA_READINESS_DOC), _display_ref(DOCS_INDEX)],
        "checks": checks,
    }


def format_alpha_smoke_readiness(summary: dict[str, Any]) -> list[str]:
    lines = [
        f"Alpha smoke readiness: {summary['status']}",
        f"Claim boundary: {summary['claim_boundary']}",
        "Remote providers: not called by this command",
        "",
        "Checks:",
    ]
    for check in summary["checks"]:
        lines.append(f"  {check['id']:<26} {check['status']:<7} {check['summary']}")
        for gap in check.get("gaps", []):
            lines.append(f"    gap: {gap}")
    lines.extend(["", "Evidence:"])
    for ref in summary["evidence_refs"]:
        lines.append(f"  {ref}")
    return lines


def _agentflow_production_handoff_check() -> dict[str, Any]:
    required = [
        ALPHA_READINESS_DOC,
        Path("workflows/agentflow_production_handoff.yaml"),
        Path("examples/agentflow_production/creative_brief.example.json"),
    ]
    return _static_evidence_check(
        check_id="agentflow_production_handoff",
        label="AgentFlow Production production handoff",
        required_paths=required,
        summary="Deterministic handoff evidence is recorded",
        gaps=[
            "Does not prove mature creative quality or provider cost-quality optimization",
        ],
    )


def _agentflow_studio_package_check() -> dict[str, Any]:
    required = [
        ALPHA_READINESS_DOC,
        Path("workflows/video_to_finished_package_local_asr.yaml"),
        Path("examples/demo_asr/video_to_finished_package_local_asr_input.example.json"),
        Path("examples/demo_bgm/bgm.metadata.example.json"),
    ]
    return _static_evidence_check(
        check_id="agentflow_studio_package",
        label="AgentFlow Studio finished package",
        required_paths=required,
        summary="Local package-chain evidence is recorded",
        gaps=[
            "Rerun still depends on local ignored media and FFmpeg availability",
            "Does not validate viral/editorial judgment",
        ],
    )


def _posterflow_live_smoke_check() -> dict[str, Any]:
    env_status = _env_status()
    provider = os.environ.get("AFS_IMAGE_PROVIDER", "openai_compatible").strip().lower()
    allow_remote = os.environ.get("AFS_ALLOW_REMOTE_IMAGE", "").strip().lower() == "true"
    required_paths = [
        ALPHA_READINESS_DOC,
        Path("workflows/posterflow_memory_demo.yaml"),
        Path("examples/posterflow/poster_brief.example.json"),
    ]
    missing_paths = [_display_ref(path) for path in required_paths if not path.exists()]
    if missing_paths:
        status = "fail"
        summary = "PosterFlow smoke inputs are missing"
        gaps = [f"Missing required path: {path}" for path in missing_paths]
    elif not allow_remote:
        status = "blocked"
        summary = "Remote image provider is not enabled"
        gaps = ["Set AFS_ALLOW_REMOTE_IMAGE=true only for an intentional live image smoke"]
    elif provider not in {"", "openai_compatible", "minimax"}:
        status = "fail"
        summary = "Unsupported image provider is configured"
        gaps = ["Use AFS_IMAGE_PROVIDER=openai_compatible or minimax"]
    else:
        gaps = _image_provider_config_gaps(provider)
        status = "blocked" if gaps else "pass"
        summary = "Provider env is ready; live image smoke was not executed" if not gaps else "Provider env is incomplete"
    return {
        "id": "posterflow_live_smoke",
        "label": "PosterFlow provider readiness",
        "status": status,
        "summary": summary,
        "evidence_refs": [_display_ref(ALPHA_READINESS_DOC)],
        "provider_env": env_status,
        "gaps": gaps,
    }


def _static_evidence_check(
    *,
    check_id: str,
    label: str,
    required_paths: list[Path],
    summary: str,
    gaps: list[str],
) -> dict[str, Any]:
    missing = [_display_ref(path) for path in required_paths if not path.exists()]
    status = "fail" if missing else "pass"
    return {
        "id": check_id,
        "label": label,
        "status": status,
        "summary": summary if not missing else "Required local evidence references are missing",
        "evidence_refs": [_display_ref(path) for path in required_paths],
        "gaps": [f"Missing required path: {path}" for path in missing] if missing else gaps,
    }


def _image_provider_config_gaps(provider: str) -> list[str]:
    gaps: list[str] = []
    if not os.environ.get("AFS_IMAGE_API_KEY"):
        gaps.append("AFS_IMAGE_API_KEY is not set")
    if provider in {"", "openai_compatible"}:
        if not os.environ.get("AFS_IMAGE_BASE_URL"):
            gaps.append("AFS_IMAGE_BASE_URL is not set for openai_compatible")
        if not os.environ.get("AFS_IMAGE_MODEL"):
            gaps.append("AFS_IMAGE_MODEL is not set for openai_compatible")
    return gaps


def _overall_status(checks: list[dict[str, Any]]) -> str:
    statuses = {check["status"] for check in checks}
    if "fail" in statuses:
        return "fail"
    if "blocked" in statuses:
        return "blocked"
    return "pass"


def _env_status() -> dict[str, str]:
    return {name: "set" if os.environ.get(name) else "unset" for name in IMAGE_ENV_VARS}


def _display_ref(path: Path) -> str:
    return str(path).replace("\\", "/")
