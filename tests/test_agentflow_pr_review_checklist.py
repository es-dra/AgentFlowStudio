from __future__ import annotations

from pathlib import Path


DOCS_INDEX = Path("docs/README.md")
CHECKLIST_PATH = Path("docs/agentflow_pr_review_checklist.md")


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_agentflow_pr_review_checklist_is_discoverable() -> None:
    docs_index = _text(DOCS_INDEX)

    assert CHECKLIST_PATH.exists()
    assert "agentflow_pr_review_checklist.md" in docs_index


def test_agentflow_pr_review_checklist_declares_scope_and_boundaries() -> None:
    checklist = _text(CHECKLIST_PATH)

    assert "Phase 15.8" in checklist
    assert "contract PR review checklist" in checklist
    assert "does not implement runtime validation" in checklist
    assert "does not execute workflows" in checklist
    assert "does not replace `inspect-run` or `review-run`" in checklist


def test_agentflow_pr_review_checklist_requires_current_verification_gate() -> None:
    checklist = _text(CHECKLIST_PATH)

    assert ".venv\\Scripts\\python.exe -m pytest tests/test_contract_examples.py" in checklist
    assert ".venv\\Scripts\\python.exe -m pytest tests/test_agentflow_contract_audit.py" in checklist
    assert ".venv\\Scripts\\python.exe -m pytest" in checklist
    assert ".venv\\Scripts\\python.exe -m compileall apps agentflow_studio agentflow_production tests" in checklist
    assert "git diff --check" in checklist
    assert ".venv\\Scripts\\python.exe -m apps.cli.main --help" in checklist
    assert ".venv\\Scripts\\python.exe -m apps.cli.main version" in checklist


def test_agentflow_pr_review_checklist_covers_contract_review_topics() -> None:
    checklist = _text(CHECKLIST_PATH)

    assert "schema_version: 0.1.0" in checklist
    assert "artifact_type" in checklist
    assert "router decision" in checklist
    assert "memory candidate" in checklist
    assert "feedback signal" in checklist
    assert "cost-quality trace" in checklist
    assert "no private paths" in checklist
