#!/usr/bin/env python3
"""Run gold_cases.json through live runtime extract paths (no production edits).

Uses:
  POST .../analysis-candidates/extract
  POST .../analysis-relationships/extract

Writes missing_evidence_candidates_v0.1 JSON for score_missing_evidence.py.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

# Repo root: .../script-understanding-eval/missing-evidence -> internal-notes -> docs -> repo
REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.api.runtime_service import create_runtime_app  # noqa: E402


def _run_case(client: TestClient, gold_case: dict[str, Any]) -> dict[str, Any]:
    case_id = str(gold_case["id"])
    project_id = f"missing-eval-{case_id.lower()}"
    source = str(gold_case.get("source") or "")

    created = client.post("/projects", json={"project_id": project_id, "goal": f"missing-eval {case_id}"})
    if created.status_code != 200:
        raise RuntimeError(f"{case_id}: create project failed: {created.text}")

    revision_resp = client.post(
        f"/projects/{project_id}/script-revisions",
        json={"source_kind": "script", "source_text": source},
    )
    if revision_resp.status_code != 200:
        raise RuntimeError(f"{case_id}: create revision failed: {revision_resp.text}")
    revision = revision_resp.json()["revision"]
    revision_id = revision["revision_id"]

    extract_resp = client.post(f"/projects/{project_id}/script-revisions/{revision_id}/analysis-candidates/extract")
    if extract_resp.status_code != 200:
        raise RuntimeError(f"{case_id}: candidate extract failed: {extract_resp.text}")
    extract_body = extract_resp.json()
    candidate = extract_body.get("candidate") or {}
    assets = list((extract_body.get("projection") or {}).get("assets") or [])

    characters = [
        str(asset.get("display_name") or "")
        for asset in assets
        if asset.get("asset_type") == "character" and asset.get("display_name")
    ]
    scenes = [
        str(asset.get("display_name") or "")
        for asset in assets
        if asset.get("asset_type") == "main_scene" and asset.get("display_name")
    ]
    missing_slots = list(candidate.get("missing_slots") or [])

    relations: list[dict[str, Any]] = []
    if scenes and characters:
        rel_resp = client.post(f"/projects/{project_id}/script-revisions/{revision_id}/analysis-relationships/extract")
        if rel_resp.status_code != 200:
            raise RuntimeError(f"{case_id}: relationship extract failed: {rel_resp.text}")
        id_to_name = {str(asset["asset_id"]): str(asset["display_name"]) for asset in assets}
        for row in rel_resp.json().get("relationships") or []:
            if str(row.get("relation_type") or "") != "scene_cast":
                continue
            relations.append(
                {
                    "relation_type": "scene_cast",
                    "scene": id_to_name.get(str(row.get("scene_asset_id")), ""),
                    "member": id_to_name.get(str(row.get("member_asset_id")), ""),
                    "status": str(row.get("status") or ""),
                    "evidence_status": str(row.get("evidence_status") or ""),
                    "evidence_span_count": len(row.get("evidence_spans") or []),
                }
            )

    return {
        "id": case_id,
        "missing_slots": missing_slots,
        "characters": characters,
        "scenes": scenes,
        "relations": relations,
        "runtime": {
            "project_id": project_id,
            "revision_id": revision_id,
            "candidate_id": candidate.get("candidate_id"),
        },
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gold",
        type=Path,
        default=Path(__file__).with_name("gold_cases.json"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).with_name("runtime_candidates.json"),
    )
    args = parser.parse_args(argv)

    gold = json.loads(args.gold.read_text(encoding="utf-8"))
    cases: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="afs-missing-eval-") as tmp:
        client = TestClient(create_runtime_app(runtime_root=Path(tmp)))
        for gold_case in gold.get("cases") or []:
            cases.append(_run_case(client, gold_case))

    payload = {
        "schema_version": "missing_evidence_candidates_v0.1",
        "mode": "runtime_extract",
        "cases": cases,
    }
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(args.out), "case_count": len(cases)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
