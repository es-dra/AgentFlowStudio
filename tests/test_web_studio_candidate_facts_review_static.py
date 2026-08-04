from __future__ import annotations

from pathlib import Path


STUDIO_ROOT = Path("apps/studio")


def test_runtime_client_exposes_candidate_fact_review_routes() -> None:
    runtime_client = (STUDIO_ROOT / "src" / "runtime-client.js").read_text(encoding="utf-8")
    assert "getCandidateFactReview(" in runtime_client
    assert "refreshCandidateFactReview(" in runtime_client
    assert "applyCandidateFactAction(" in runtime_client
    assert "/candidate-facts/review" in runtime_client
    assert "/candidate-facts/review/refresh" in runtime_client
    assert "/candidate-facts/actions" in runtime_client


def test_candidate_facts_review_panel_covers_core_actions_and_labels() -> None:
    panel = (STUDIO_ROOT / "src" / "panels" / "candidate-facts-review.js").read_text(encoding="utf-8")
    assert "probeCandidateReviewAvailable" in panel
    assert "buildCandidateFactsReviewPanel" in panel
    assert "extracted_from_text" in panel
    assert "原文提取" in panel
    assert "accept" in panel
    assert "reject" in panel
    assert "edit_confirm" in panel
    assert "刷新候选" in panel


def test_product_shell_mounts_candidate_review_in_asset_bible_when_available() -> None:
    shell = (STUDIO_ROOT / "src" / "product-shell.js").read_text(encoding="utf-8")
    css = (STUDIO_ROOT / "styles" / "asset-bible.css").read_text(encoding="utf-8")
    assert 'from "./panels/candidate-facts-review.js"' in shell
    assert "probeCandidateReviewAvailable" in shell
    assert "candidateReviewAvailable" in shell
    assert "buildCandidateFactsReviewPanel" in shell
    assert "refreshCandidateFactReview" in shell
    assert "applyCandidateFactReviewAction" in shell
    assert "剧本候选审阅" in (STUDIO_ROOT / "src" / "panels" / "candidate-facts-review.js").read_text(encoding="utf-8")
    assert ".candidate-review-panel" in css
