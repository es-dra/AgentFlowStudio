from pathlib import Path


DOC = Path("docs/handoff/AFS-INTERNAL-BETA-ACCEPTANCE-OPERATING-INDEX-20260619.md")
INDEX = Path("docs/handoff/INDEX.md")


def test_internal_beta_acceptance_operating_index_is_current_and_safe() -> None:
    doc = DOC.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")

    assert DOC.name in index
    assert "tools\\afs_internal_beta_acceptance.py" in doc
    assert "tools\\afs_three_end_status.py" in doc
    assert "--preflight-only" in doc
    assert "--three-end-status" in doc
    assert "AFS_INTERNAL_BETA_ACCEPTANCE_INVITE_CODE" in doc
    assert "AFS_INTERNAL_BETA_ACCEPTANCE_INVITE_CODE_BETA" in doc
    assert "ready_for_http_acceptance" in doc
    assert "contract_verified_pending_human_acceptance" in doc
    assert "pending_human_review" in doc
    assert "human acceptance" in doc
    assert "business validation" in doc
    assert "provider smoke" in doc
    assert "durable memory" in doc
    assert "provider raw response" in doc
    assert "signed URL" in doc
    assert "local absolute path" in doc
    assert "media bytes" in doc
    assert "video=false" in doc
    assert "no provider call" in doc
    assert len(doc.splitlines()) <= 180
