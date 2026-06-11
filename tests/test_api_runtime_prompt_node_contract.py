from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.runtime_models import PromptOptimizationRequest
from apps.api.runtime_service import create_runtime_app


FIXTURE_DIR = Path("examples/frontend_runtime_service/prompt_optimizer_nodes")
CONTRACT_PATH = Path("docs/architecture/AFS_NODE_PROMPT_OPTIMIZER_CONTRACT.zh-CN.md")
DEMO_PROJECT_PATH = Path("examples/frontend_runtime_service/prompt_optimizer_demo_project.example.json")
SMOKE_TOOL = Path("tools/prompt_optimizer_api_smoke.py")
NODE_FIXTURES = {
    "text": "text_node.zh.json",
    "image": "image_node.zh.json",
    "video": "video_node.zh.json",
    "audio": "audio_node.zh.json",
    "script": "script_node.zh.json",
    "director": "director_node.zh.json",
}
FORBIDDEN_PAYLOAD = re.compile(
    r"api_key|bearer |signed_url|provider_config|data/processed/runs|[a-z]:\\",
    re.IGNORECASE,
)


def _load_fixture(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _prompt_sections(payload: dict, brief: dict) -> set[str]:
    if isinstance(brief.get("prompt_sections"), list):
        return {section["title"] for section in brief["prompt_sections"]}
    sections = set()
    for line in str(payload.get("optimized_prompt", "")).splitlines():
        if ":" not in line:
            continue
        title = line.split(":", 1)[0].strip()
        if title:
            sections.add(title)
    return sections


def test_node_prompt_optimizer_contract_and_fixtures_are_complete() -> None:
    assert CONTRACT_PATH.exists()
    contract = CONTRACT_PATH.read_text(encoding="utf-8")
    assert "video_merge" in contract
    assert "no prompt by default" in contract
    for node_type in NODE_FIXTURES:
        assert f"`{node_type}`" in contract

    assert FIXTURE_DIR.exists()
    seen_node_types = set()
    for node_type, filename in NODE_FIXTURES.items():
        fixture_path = FIXTURE_DIR / filename
        assert fixture_path.exists(), f"missing fixture: {fixture_path}"
        fixture = _load_fixture(fixture_path)
        request = fixture["request"]
        expected = fixture["expected"]
        PromptOptimizationRequest(**request)
        seen_node_types.add(request["node_type"])
        assert request["node_type"] == node_type
        assert request["node_type"] != "video_merge"
        assert expected["provider_calls_started"] is False
        assert expected["expected_sections"]
        assert expected["expected_domains"]
        assert expected["forbidden_ui_terms"]
        serialized = json.dumps(fixture, ensure_ascii=False)
        assert not FORBIDDEN_PAYLOAD.search(serialized)

    assert seen_node_types == set(NODE_FIXTURES)


def test_prompt_optimizer_node_fixtures_drive_runtime_api(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    for fixture_path in sorted(FIXTURE_DIR.glob("*.zh.json")):
        fixture = _load_fixture(fixture_path)
        project = fixture["project"]
        request = fixture["request"]
        expected = fixture["expected"]
        project_id = project["project_id"]
        client.post("/projects", json=project)

        result = client.post(f"/projects/{project_id}/prompt-optimizations", json=request)

        assert result.status_code == 200, fixture_path.name
        payload = result.json()
        trace = client.get(f"/artifacts/{payload['artifacts']['prompt_assembly_trace']['artifact_id']}").json()["payload"]
        manifest = client.get(f"/artifacts/{payload['artifacts']['prompt_optimization_safe_manifest']['artifact_id']}").json()["payload"]
        brief = client.get(f"/artifacts/{payload['artifacts']['creative_brief']['artifact_id']}").json()["payload"]
        serialized = json.dumps({"payload": payload, "trace": trace, "manifest": manifest, "brief": brief}, ensure_ascii=False)
        domains = {rule["domain"] for rule in trace["knowledge_rules"]}
        sections = _prompt_sections(payload, brief)

        assert payload["ui_surface"] == "node_prompt_optimizer"
        assert payload["optimized_prompt"]
        assert payload["provider_calls_started"] is False
        assert manifest["provider_calls_started"] is False
        assert set(expected["expected_domains"]).issubset(domains)
        assert set(expected["expected_sections"]).issubset(sections)
        assert all(rule.get("rule_id") and rule.get("match_reason") for rule in trace["knowledge_rules"])
        assert not FORBIDDEN_PAYLOAD.search(serialized)


def test_prompt_optimizer_demo_project_seed_is_safe_and_complete() -> None:
    seed = _load_fixture(DEMO_PROJECT_PATH)
    assert seed["artifact_type"] == "afs_prompt_optimizer_demo_project_seed"
    assert len(seed["characters"]) == 2
    assert len(seed["scenes"]) == 2
    assert len(seed["prompt_nodes"]) == 6
    assert {node["request"]["node_type"] for node in seed["prompt_nodes"]} == set(NODE_FIXTURES)
    serialized = json.dumps(seed, ensure_ascii=False)
    assert not FORBIDDEN_PAYLOAD.search(serialized)


def test_prompt_optimizer_api_smoke_tool_runs_against_fixtures(tmp_path) -> None:
    output_dir = tmp_path / "prompt_optimizer_api_smoke"
    result = subprocess.run(
        [
            sys.executable,
            str(SMOKE_TOOL),
            "--fixture-dir",
            str(FIXTURE_DIR),
            "--output-dir",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(result.stdout)
    report = json.loads((output_dir / "prompt_optimizer_api_smoke.json").read_text(encoding="utf-8"))

    assert payload["status"] == "passed"
    assert report["status"] == "passed"
    assert report["summary"]["passed"] == 6
    assert report["summary"]["failed"] == 0
    assert report["summary"]["provider_calls_started"] == 0
    assert report["summary"]["unsafe_matches"] == 0
