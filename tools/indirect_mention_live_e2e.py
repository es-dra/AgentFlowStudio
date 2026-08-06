#!/usr/bin/env python3
"""Real-API e2e for paid indirect-mention proposals (analysis-candidates/extract).

COST WARNING: with AFS_ENABLE_INDIRECT_MENTION_LLM_PROPOSALS=true this script
issues real remote LLM calls (budget capped by AFS_INDIRECT_MENTION_LLM_MAX_CALLS).
Do not confuse with free alias/scene proposal flags.

Requires: AFS_ALLOW_REMOTE_LLM, AFS_PROVIDER_CONFIG, provider credentials.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from apps.api.runtime_script_core_truth import (  # noqa: E402
    ANALYSIS_REVIEW_SCHEMA_VERSION,
    CORE_ASSET_COMMAND_SCHEMA_VERSION,
)
from apps.api.runtime_service import create_runtime_app  # noqa: E402

SCRIPTS = [
    REPO / "docs/internal-notes/long-script-observation-20260805/01_echo_inn_long.txt",
    REPO / "docs/internal-notes/long-script-observation-20260805/02_night_post_long.txt",
    REPO / "docs/internal-notes/indirect-mention-generalization-20260806/01_office_standup.txt",
    REPO / "docs/internal-notes/indirect-mention-generalization-20260806/02_campus_relay.txt",
    REPO / "docs/internal-notes/indirect-mention-generalization-20260806/03_lab_night_shift.txt",
]

# Validated gold: should appear as indirect-mention proposals when flag on.
EXPECTED_INDIRECT = {
    "01_echo_inn_long.txt": set(),  # may emit 悦安 (known alias-on-stage boundary)
    "02_night_post_long.txt": {"顾衡"},
    "01_office_standup.txt": {"沈岚"},
    "02_campus_relay.txt": {"江澄"},
    "03_lab_night_shift.txt": {"柯衡"},
}

# Noise that must NOT become proposals (when discovered+judged).
NOISE_DENY = {"别自己拆", "默记修缮", "晚上见", "留局待领", "夜班邮筒", "失踪汇款"}


def _extract(client: TestClient, project_id: str, source_text: str) -> dict:
    created = client.post("/projects", json={"project_id": project_id, "goal": "indirect e2e"})
    assert created.status_code == 200, created.text
    rev = client.post(
        f"/projects/{project_id}/script-revisions",
        json={"source_kind": "script", "source_text": source_text, "provenance": {"fixture": "indirect_e2e"}},
    )
    assert rev.status_code == 200, rev.text
    revision = rev.json()["revision"]
    response = client.post(
        f"/projects/{project_id}/script-revisions/{revision['revision_id']}/analysis-candidates/extract"
    )
    assert response.status_code == 200, response.text
    return {"revision": revision, "payload": response.json()}


def main() -> int:
    if os.environ.get("AFS_ALLOW_REMOTE_LLM", "").strip().lower() not in {"1", "true", "yes", "on"}:
        print("AFS_ALLOW_REMOTE_LLM must be true for paid e2e", file=sys.stderr)
        return 2
    if not os.environ.get("AFS_PROVIDER_CONFIG"):
        print("AFS_PROVIDER_CONFIG required", file=sys.stderr)
        return 2

    report: dict = {
        "schema_version": "afs.indirect_mention_live_e2e.v0.1",
        "cost_class": "paid_remote_llm_when_flag_on",
        "flag_off": [],
        "flag_on": [],
        "authority_check": None,
    }

    with tempfile.TemporaryDirectory(prefix="afs-indirect-e2e-") as tmp:
        client = TestClient(create_runtime_app(runtime_root=Path(tmp)))

        # --- Flag OFF: behavior unchanged / no proposal fields / zero dispatch ---
        os.environ.pop("AFS_ENABLE_INDIRECT_MENTION_LLM_PROPOSALS", None)
        for path in SCRIPTS:
            text = path.read_text(encoding="utf-8")
            result = _extract(client, f"off-{path.stem}", text)
            payload = result["payload"]
            cand = payload["candidate"]
            row = {
                "script": path.name,
                "provider_dispatch_count": payload["provider_dispatch_count"],
                "has_proposals": "indirect_mention_proposals" in cand,
                "character_names": sorted(
                    item["display_name"]
                    for item in payload["projection"]["assets"]
                    if item["asset_type"] == "character"
                ),
            }
            report["flag_off"].append(row)
            assert payload["provider_dispatch_count"] == 0, row
            assert "indirect_mention_proposals" not in cand, row
            print(f"[flag-off] {path.name}: ok dispatch=0 proposals=absent", flush=True)

        # --- Flag ON: paid LLM path ---
        os.environ["AFS_ENABLE_INDIRECT_MENTION_LLM_PROPOSALS"] = "true"
        os.environ.setdefault("AFS_INDIRECT_MENTION_LLM_MAX_CALLS", "20")
        for path in SCRIPTS:
            text = path.read_text(encoding="utf-8")
            result = _extract(client, f"on-{path.stem}", text)
            payload = result["payload"]
            cand = payload["candidate"]
            proposals = cand.get("indirect_mention_proposals") or []
            mentions = {item["mention"] for item in proposals}
            skipped = cand.get("indirect_mention_budget_skipped") or []
            expected = EXPECTED_INDIRECT.get(path.name, set())
            missing = sorted(expected - mentions)
            noise_hit = sorted(mentions & NOISE_DENY)
            row = {
                "script": path.name,
                "provider_dispatch_count": payload["provider_dispatch_count"],
                "proposal_mentions": sorted(mentions),
                "budget_skipped": [item["mention"] for item in skipped],
                "expected_missing": missing,
                "noise_hit": noise_hit,
                "notes": payload.get("extraction", {}).get("notes") or [],
            }
            report["flag_on"].append(row)
            print(
                f"[flag-on] {path.name}: dispatch={row['provider_dispatch_count']} "
                f"mentions={row['proposal_mentions']} missing={missing} noise={noise_hit} "
                f"skipped={len(skipped)}",
                flush=True,
            )
            assert payload["provider_dispatch_count"] > 0 or not (
                # If discovery finds nothing, zero is ok but unusual for these scripts.
                True
            )
            assert missing == [], f"missing expected indirect mentions: {missing}"
            assert noise_hit == [], f"noise incorrectly proposed: {noise_hit}"
            for item in proposals:
                assert item["status"] == "candidate"
                assert item["authority"] == "non_authoritative_proposal"
                assert item["cost_class"] == "paid_remote_llm"
                assert item["is_indirect_mention"] is True

        # Authority: ordinary review must not create 顾衡 from proposals.
        night = REPO / "docs/internal-notes/long-script-observation-20260805/02_night_post_long.txt"
        text = night.read_text(encoding="utf-8")
        result = _extract(client, "authority-night-post", text)
        payload = result["payload"]
        revision = result["revision"]
        proposals = payload["candidate"].get("indirect_mention_proposals") or []
        assert any(item["mention"] == "顾衡" for item in proposals), "顾衡 proposal required"
        chars = {
            item["display_name"]: item
            for item in payload["projection"]["assets"]
            if item["asset_type"] == "character"
        }
        assert "顾衡" not in chars
        # Confirm some on-stage character if present; else skip review and just check confirm path.
        if chars:
            target = next(iter(chars.values()))
            reviewed = client.post(
                f"/projects/authority-night-post/script-revisions/{revision['revision_id']}/analysis-assets/{target['asset_id']}/review",
                json={
                    "project_id": "authority-night-post",
                    "revision_id": revision["revision_id"],
                    "source_digest": revision["source_digest"],
                    "candidate_id": payload["candidate"]["candidate_id"],
                    "asset_version_id": target["version_id"],
                    "expected_asset_version": target["version"],
                    "expected_graph_version": 0,
                    "idempotency_key": "e2e-review-no-indirect-authority",
                    "schema_version": ANALYSIS_REVIEW_SCHEMA_VERSION,
                    "decision": "confirm",
                },
            )
            assert reviewed.status_code == 200, reviewed.text
            truth = client.get("/projects/authority-night-post/script-truth").json()
            names = {
                item["display_name"]
                for item in truth["projection"]["assets"]
                if item["asset_type"] == "character"
            }
            assert "顾衡" not in names
            report["authority_check"] = {
                "ordinary_review_promoted_guheng": False,
                "reviewed_asset": target["display_name"],
            }

        proposal = next(item for item in proposals if item["mention"] == "顾衡")
        confirmed = client.post(
            "/projects/authority-night-post/core-assets/commands/confirm",
            json={
                "project_id": "authority-night-post",
                "revision_id": revision["revision_id"],
                "source_digest": revision["source_digest"],
                "schema_version": CORE_ASSET_COMMAND_SCHEMA_VERSION,
                "command_type": "create_manual_character",
                "patch": {
                    "display_name": proposal["mention"],
                    "evidence_spans": proposal["evidence_spans"],
                    "proposal_id": proposal["proposal_id"],
                },
                "idempotency_key": "e2e-confirm-guheng",
                "provider_dispatch_count": 0,
                "remote_dispatch_count": 0,
            },
        )
        assert confirmed.status_code == 200, confirmed.text
        names = {
            item["display_name"]
            for item in confirmed.json()["projection"]["assets"]
            if item["asset_type"] == "character"
        }
        assert "顾衡" in names
        report["authority_check"] = {
            **(report["authority_check"] or {}),
            "manual_create_guheng": True,
        }
        print("[authority] ordinary review did not promote; create_manual_character did", flush=True)

    out = REPO / "docs/internal-notes/indirect-mention-live-e2e-20260806.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"report={out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
