from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.runtime_service import create_runtime_app  # noqa: E402


UNSAFE_PATTERN = re.compile(
    r"api_key|bearer |signed_url|provider_config|data/processed/runs|[a-z]:\\",
    re.IGNORECASE,
)
REPORT_NAME = "prompt_optimizer_api_smoke.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run API-only prompt optimizer smoke checks.")
    parser.add_argument("--fixture-dir", required=True, help="Directory containing node prompt optimizer fixtures.")
    parser.add_argument("--output-dir", required=True, help="Directory for the smoke report and temporary runtime root.")
    args = parser.parse_args()

    fixture_dir = Path(args.fixture_dir)
    output_dir = Path(args.output_dir)
    report = run_smoke(fixture_dir=fixture_dir, output_dir=output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / REPORT_NAME).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = {
        "status": report["status"],
        "report_path": REPORT_NAME,
        "summary": report["summary"],
    }
    sys.stdout.write(json.dumps(summary, ensure_ascii=False) + "\n")
    return 0 if report["status"] == "passed" else 1


def run_smoke(*, fixture_dir: Path, output_dir: Path) -> dict[str, Any]:
    fixtures = sorted(fixture_dir.glob("*.zh.json"))
    runtime_root = output_dir / "runtime"
    client = TestClient(create_runtime_app(runtime_root=runtime_root))
    cases = [_run_case(client, path) for path in fixtures]
    failed = [case for case in cases if case["status"] != "passed"]
    provider_calls = sum(1 for case in cases if case["provider_calls_started"] is True)
    unsafe_matches = sum(len(case["unsafe_matches"]) for case in cases)
    return {
        "artifact_type": "agentflow_prompt_optimizer_api_smoke_report",
        "schema_version": "0.1.0",
        "status": "failed" if failed else "passed",
        "summary": {
            "total": len(cases),
            "passed": len(cases) - len(failed),
            "failed": len(failed),
            "provider_calls_started": provider_calls,
            "unsafe_matches": unsafe_matches,
        },
        "cases": cases,
        "non_claims": [
            "api smoke is not browser acceptance",
            "api smoke is not provider execution",
            "api smoke is not human validation",
        ],
    }


def _run_case(client: TestClient, fixture_path: Path) -> dict[str, Any]:
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    project = fixture["project"]
    request = fixture["request"]
    expected = fixture["expected"]
    project_id = project["project_id"]
    errors: list[str] = []

    project_response = client.post("/projects", json=project)
    if project_response.status_code not in (200, 422):
        errors.append(f"project_create_status={project_response.status_code}")

    result = client.post(f"/projects/{project_id}/prompt-optimizations", json=request)
    if result.status_code != 200:
        return _failed_case(fixture_path, request, errors + [f"optimization_status={result.status_code}"])

    payload = result.json()
    trace = _artifact_payload(client, payload, "prompt_assembly_trace", errors)
    manifest = _artifact_payload(client, payload, "prompt_optimization_safe_manifest", errors)
    brief = _artifact_payload(client, payload, "creative_brief", errors)
    domains = {rule.get("domain") for rule in trace.get("knowledge_rules", []) if isinstance(rule, dict)}
    sections = _prompt_sections(payload, brief)
    unsafe_matches = _unsafe_matches({"payload": payload, "trace": trace, "manifest": manifest, "brief": brief})

    if payload.get("ui_surface") != "node_prompt_optimizer":
        errors.append("ui_surface_mismatch")
    if not payload.get("optimized_prompt"):
        errors.append("optimized_prompt_empty")
    if payload.get("provider_calls_started") is not False:
        errors.append("payload_provider_calls_started")
    if manifest.get("provider_calls_started") is not False:
        errors.append("manifest_provider_calls_started")
    missing_domains = sorted(set(expected["expected_domains"]) - domains)
    if missing_domains:
        errors.append("missing_domains=" + ",".join(missing_domains))
    missing_sections = sorted(set(expected["expected_sections"]) - sections)
    if missing_sections:
        errors.append("missing_sections=" + ",".join(missing_sections))
    if unsafe_matches:
        errors.append("unsafe_payload")

    return {
        "fixture": fixture_path.name,
        "node_type": request["node_type"],
        "generation_target": request["generation_target"],
        "status": "failed" if errors else "passed",
        "errors": errors,
        "provider_calls_started": payload.get("provider_calls_started") is True or manifest.get("provider_calls_started") is True,
        "unsafe_matches": unsafe_matches,
        "knowledge_domains": sorted(domain for domain in domains if domain),
        "prompt_sections": sorted(section for section in sections if section),
    }


def _artifact_payload(client: TestClient, payload: dict[str, Any], role: str, errors: list[str]) -> dict[str, Any]:
    artifact_id = payload.get("artifacts", {}).get(role, {}).get("artifact_id")
    if not artifact_id:
        errors.append(f"missing_artifact_ref={role}")
        return {}
    response = client.get(f"/artifacts/{artifact_id}")
    if response.status_code != 200:
        errors.append(f"artifact_fetch_status={role}:{response.status_code}")
        return {}
    body = response.json()
    artifact_payload = body.get("payload")
    return artifact_payload if isinstance(artifact_payload, dict) else {}


def _prompt_sections(payload: dict[str, Any], brief: dict[str, Any]) -> set[str]:
    prompt_sections = brief.get("prompt_sections")
    if isinstance(prompt_sections, list):
        return {section.get("title") for section in prompt_sections if isinstance(section, dict)}
    sections: set[str] = set()
    for line in str(payload.get("optimized_prompt", "")).splitlines():
        if ":" not in line:
            continue
        title = line.split(":", 1)[0].strip()
        if title:
            sections.add(title)
    return sections


def _unsafe_matches(payload: dict[str, Any]) -> list[str]:
    serialized = json.dumps(payload, ensure_ascii=False)
    return sorted(set(match.group(0) for match in UNSAFE_PATTERN.finditer(serialized)))


def _failed_case(fixture_path: Path, request: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    return {
        "fixture": fixture_path.name,
        "node_type": request.get("node_type"),
        "generation_target": request.get("generation_target"),
        "status": "failed",
        "errors": errors,
        "provider_calls_started": False,
        "unsafe_matches": [],
        "knowledge_domains": [],
        "prompt_sections": [],
    }


if __name__ == "__main__":
    raise SystemExit(main())
