from __future__ import annotations

import re

SCHEMA_VERSION = "0.1.0"
ARTIFACT_TYPE = "agentflow_maintenance_audit_report"

DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "data/models",
    "data/processed",
    "data/raw",
    "data/reports",
    "node_modules",
}

LEGACY_FROZEN_PREFIXES = (
    "agentflow/memory/",
    "agentflow_studio/asr_sop/",
    "agentflow_studio/audio_sop/",
    "agentflow_studio/candidate_sop/",
    "agentflow_studio/highlight_sop/",
    "agentflow_studio/ocr_sop/",
    "agentflow_studio/production/",
    "agentflow_studio/slicing_sop/",
    "agentflow_studio/workflow_engine/",
    "apps/cli/production_memory_",
)

TEXT_SUFFIXES = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".jsonl",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}

LEGACY_COMPANY_PATTERNS = (
    "D:\\Learning materials\\Learning_notes" + "\\Company",
    "Company " + "source knowledge base",
)

HIGH_CONFIDENCE_SECRET_PATTERNS = (
    re.compile(r"(?<![A-Za-z0-9_])sk-[A-Za-z0-9_\-]{12,}"),
    re.compile(r"(?<![A-Za-z0-9_])AKIA[0-9A-Z]{12,}"),
    re.compile(r"BEGIN [A-Z ]*PRIVATE KEY"),
)

SECRET_FIELD_PATTERNS = (
    re.compile(r"api[_-]?key\s*(?::|=(?!=))", re.IGNORECASE),
    re.compile(r"token\s*(?::|=(?!=))", re.IGNORECASE),
    re.compile(r"cookie\s*(?::|=(?!=))", re.IGNORECASE),
    re.compile(r"signed_url\s*(?::|=(?!=))", re.IGNORECASE),
)

KNOWN_SAFE_SECRET_FIXTURES = {
    "<local-provider-key>",
    "<your-local-key>",
    "?token=secret",
    "abc123",
    "fake",
    "fake-key",
    "fake-secret-key",
    "fake-token",
    "fk-mm-key",
    "provider-secret-url",
    "signed_url=abc",
    "secret-key",
    "sk-test-secret-value",
    "token=abc",
}

HISTORICAL_SUMMARY_PATH = "docs/archive/HISTORICAL_DOCS_SUMMARY.zh-CN.md"

HISTORICAL_DOC_PREFIXES = (
    "docs/company-kb-feedback-candidates/",
    "docs/handoff/",
    "docs/maintenance/",
    "docs/retrospectives/",
    "docs/strategy/",
    "docs/task_briefs/",
    "docs/testing/",
    "docs/workbench/",
)

HISTORICAL_DOC_GLOBS = (
    "docs/afs_delivery_checklist.md",
    "docs/agent_*.md",
    "docs/agentflow_*.md",
    "docs/asset_lifecycle.md",
    "docs/current_architecture.md",
    "docs/feedback_contract.md",
    "docs/golden_*.md",
    "docs/highlight_detection_design.md",
    "docs/local_alpha_*.md",
    "docs/module_boundary.md",
    "docs/platform_profile_contract.md",
    "docs/post_v0_1_0_plan.md",
    "docs/product_*.md",
    "docs/real_*.md",
    "docs/run_contract.md",
    "docs/tool_contracts.md",
    "docs/video_assembly_design.md",
    "docs/viral_clip_quality_plan.md",
    "docs/workflow_plan_contract.md",
    "docs/workspace_contract.md",
    "docs/architecture/production_memory_*.md",
)
