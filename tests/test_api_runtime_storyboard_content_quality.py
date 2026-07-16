from __future__ import annotations

import json

from fastapi.testclient import TestClient

from apps.api.runtime_errors import response_contains_unsafe_marker
from apps.api.runtime_service import create_runtime_app


def test_storyboard_breakdown_writes_content_quality_report_for_dynamic_assets(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_LLM", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_content_quality_report"
    client.post("/projects", json={"project_id": project_id, "goal": "Quality-gated storyboard plan"})

    response = client.post(
        f"/projects/{project_id}/storyboard-breakdowns",
        json={
            "node_id": "script_001",
            "script_text": (
                "孙悟空大战金刚狼，破碎山巅石台上云雾翻卷。"
                "孙悟空手持金箍棒向前压低身形。"
                "金刚狼伸出钢爪迎面冲来。"
                "两人短兵相接，火花从金箍棒和钢爪之间迸出。"
                "孙悟空侧身跃起，金箍棒横扫。"
                "金刚狼后撤，脚下碎石飞溅。"
                "远处雷光照亮山脊。"
                "两人再次对峙，气氛压迫。"
                "镜头拉远，山巅战场被云海包围。"
                "最后两人同时冲向对方。"
            ),
            "target_platform": "short_video",
            "style": "cinematic",
            "generated_at": "2026-06-30T11:00:00+08:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    report = payload["content_quality_report"]
    checks = {item["id"]: item for item in report["checks"]}
    serialized = json.dumps(report, ensure_ascii=False).lower()

    assert report["artifact_type"] == "agentflow_content_quality_report"
    assert report["pipeline"] == "storyboard_breakdown"
    assert report["summary"]["status"] == "structure_verified_needs_human_review"
    assert report["summary"]["human_review_needed"] is True
    assert report["summary"]["provider_calls_started"] is False
    assert report["summary"]["writes_long_term_memory"] is False
    assert report["summary"]["writes_company_kb"] is False

    assert checks["script_source_grounding"]["status"] == "passed"
    assert checks["dynamic_shot_count"]["status"] == "passed"
    assert checks["dynamic_shot_count"]["details"]["fixed_template_claimed"] is False
    assert checks["asset_evidence"]["status"] == "passed"
    assert checks["asset_evidence"]["details"]["asset_types"] == ["character", "prop", "scene"]
    assert checks["keyframe_and_video_intent"]["status"] == "passed"
    assert checks["safe_boundary"]["status"] == "passed"
    assert "human review required before fixed assets or quality acceptance" in report["non_claims"]
    assert payload["safe_manifest"]["content_quality_report_status"] == report["summary"]["status"]
    assert "content_quality_report" in payload["artifacts"]
    assert response_contains_unsafe_marker(report) is False
    assert "api_key" not in serialized
    assert "signed_url" not in serialized
    assert "d:\\" not in serialized
