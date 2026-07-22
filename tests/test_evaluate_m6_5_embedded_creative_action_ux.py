from __future__ import annotations

from tools.evaluate_m6_5_embedded_creative_action_ux import REPO_ROOT, evaluate


def test_m6_5_embedded_creative_action_evaluator_passes() -> None:
    report = evaluate(REPO_ROOT)

    assert report["summary"]["status"] == "PASS", report["findings"]
    assert report["summary"]["p0"] == 0
    assert report["summary"]["p1"] == 0
    assert report["node_probe"]["nodeCount"] == 1
    assert report["node_probe"]["revisionCount"] == 1
    assert report["node_probe"]["providerCallsStarted"] is True
    assert report["node_probe"]["graphMutated"] is False
