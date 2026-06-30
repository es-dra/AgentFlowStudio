from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = REPO_ROOT / "tools"
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from tools import studio_visual_asset_promotion_browser_qa as promotion_qa
from tools.studio_asset_context_browser_qa_support import runtime_test_client


def test_promotion_browser_qa_screenshot_defaults_next_to_report(tmp_path) -> None:
    report = tmp_path / "evidence" / "promotion_browser_report.json"

    screenshot = promotion_qa.resolve_screenshot_path(report, "")

    assert screenshot == report.with_suffix(".png")


def test_promotion_browser_qa_screenshot_can_be_overridden(tmp_path) -> None:
    report = tmp_path / "promotion_browser_report.json"
    explicit = tmp_path / "screens" / "promotion.png"

    screenshot = promotion_qa.resolve_screenshot_path(report, str(explicit))

    assert screenshot == explicit.resolve()


def test_prepare_project_seeds_browser_promotion_contract(tmp_path) -> None:
    project_id = "studio-promotion-browser-test"

    seed = promotion_qa.prepare_project(tmp_path, project_id=project_id)

    assert seed["image_asset"]["asset_id"]
    client = runtime_test_client(tmp_path)
    state = client.get(f"/projects/{project_id}/studio-state").json()["state"]
    node = state["nodes"][promotion_qa.NODE_ID]
    decision = node["params"]["humanGateDecisions"][-1]
    serialized = json.dumps(state, ensure_ascii=False).lower()

    assert state["order"] == [promotion_qa.NODE_ID]
    assert node["params"]["uploads"][0]["asset_id"] == seed["image_asset"]["asset_id"]
    assert decision["target_type"] == "asset_card_candidate"
    assert decision["decision"] == "accepted_for_next_step"
    assert decision["human_gate_id"] == promotion_qa.HUMAN_GATE_ID
    assert decision["target_id"] == promotion_qa.ASSET_CARD_CANDIDATE_ID
    assert "data_base64" not in serialized
    assert "signed_url" not in serialized
