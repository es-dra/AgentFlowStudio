from __future__ import annotations

from tools.evaluate_m6_6_visible_creative_tasks_screenplay_graph_actions import REPO_ROOT, evaluate


def test_m6_6_visible_creative_tasks_screenplay_graph_actions_evaluator_passes() -> None:
    report = evaluate(REPO_ROOT)

    assert report["summary"]["status"] == "PASS", report["findings"]
    assert report["summary"]["p0"] == 0
    assert report["summary"]["p1"] == 0
    assert report["node_probe"]["nodeCount"] >= 5
    assert report["node_probe"]["edgeCount"] >= 5
    assert report["node_probe"]["screenplayRevisionCount"] == 2
    assert report["node_probe"]["companionCommandType"] == "start_embedded_creative_action"
