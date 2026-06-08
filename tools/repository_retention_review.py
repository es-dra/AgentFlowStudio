from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "0.1.0"
ARTIFACT_TYPE = "agentflow_repository_retention_review"

EXCLUDE_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
}


@dataclass(frozen=True)
class ReviewedPath:
    path: str
    kind: str
    git_state: str
    status: str
    rationale: str
    retirement_condition: str

    def as_dict(self) -> dict[str, str]:
        return {
            "path": self.path,
            "kind": self.kind,
            "git_state": self.git_state,
            "status": self.status,
            "rationale": self.rationale,
            "retirement_condition": self.retirement_condition,
        }


def build_repository_retention_review(root: Path) -> dict[str, Any]:
    root = root.resolve()
    files = _collect_files(root)
    directories = _collect_directories(files)
    directory_reviews = [
        _review_directory(path)
        for path in directories
        if not _is_excluded(path)
    ]
    file_reviews = [
        _review_file(path, git_state)
        for path, git_state in files.items()
        if not _is_excluded(path)
    ]
    delete_candidates = [
        item for item in [*directory_reviews, *file_reviews] if item.status == "delete_candidate"
    ]
    manual_review_required = [
        item for item in [*directory_reviews, *file_reviews] if item.status == "manual_review_required"
    ]
    status_counts: dict[str, int] = {}
    for item in [*directory_reviews, *file_reviews]:
        status_counts[item.status] = status_counts.get(item.status, 0) + 1

    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": ARTIFACT_TYPE,
        "review_id": "afs_repository_retention_review_current",
        "repository": root.name,
        "summary": {
            "directory_count": len(directory_reviews),
            "file_count": len(file_reviews),
            "delete_candidate_count": len(delete_candidates),
            "manual_review_required_count": len(manual_review_required),
            "status_counts": status_counts,
        },
        "directories": [item.as_dict() for item in directory_reviews],
        "files": [item.as_dict() for item in file_reviews],
        "non_claims": [
            "not human acceptance",
            "not business validation",
            "not durable memory",
        ],
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Review AFS repository paths for retention or cleanup.")
    parser.add_argument("--root", default=".", help="Repository root to scan.")
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Print only counts and candidate lists.",
    )
    args = parser.parse_args()

    report = build_repository_retention_review(Path(args.root))
    if args.summary_only:
        report = {
            key: report[key]
            for key in (
                "schema_version",
                "artifact_type",
                "review_id",
                "repository",
                "summary",
                "non_claims",
                "writes_long_term_memory",
                "writes_company_kb",
            )
        }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _collect_files(root: Path) -> dict[str, str]:
    tracked = _git_paths(root, ["git", "ls-files", "-z"])
    untracked = _git_paths(root, ["git", "ls-files", "--others", "--exclude-standard", "-z"])
    if not tracked and not untracked:
        return {
            path.relative_to(root).as_posix(): "filesystem"
            for path in root.rglob("*")
            if path.is_file()
        }
    files = {
        path: "deleted" if not (root / path).exists() else "tracked"
        for path in tracked
    }
    for path in untracked:
        files.setdefault(path, "untracked")
    return dict(sorted(files.items()))


def _git_paths(root: Path, command: list[str]) -> list[str]:
    try:
        result = subprocess.run(
            command,
            cwd=root,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return []
    raw = result.stdout.decode("utf-8", errors="ignore")
    return sorted(path.replace("\\", "/") for path in raw.split("\0") if path)


def _collect_directories(files: dict[str, str]) -> list[str]:
    directories = {"."}
    for file_path in files:
        current = Path(file_path).parent
        while str(current) not in ("", "."):
            directories.add(current.as_posix())
            current = current.parent
    return sorted(directories)


def _review_directory(path: str) -> ReviewedPath:
    if path == ".":
        return _dir(path, "retain_project_root", "仓库根目录承载项目入口、配置、文档和源码。")
    if path in {"agentflow", "agentflow/contracts", "agentflow/harness", "agentflow/memory", "agentflow/router", "agentflow/skills"}:
        return _dir(path, "retain_backend_core", "平台 contract、harness、memory、router 或 skill 核心代码。")
    if path.startswith("agentflow_studio"):
        return _dir(path, "retain_studio_pipeline", "内容生产与分发 pipeline 模块仍被测试和 CLI 覆盖。")
    if path.startswith("apps/api"):
        return _dir(path, "retain_runtime_service", "Runtime Service 是前后端唯一对接面。")
    if path.startswith("apps/reporting"):
        return _dir(path, "retain_application_reporting", "CLI 和旧 Web bridge 共用的应用层 report helper。")
    if path.startswith("apps/cli"):
        return _dir(path, "retain_cli_ops", "CLI 是本地运维、测试和 deterministic harness 入口。")
    if path.startswith("apps/web"):
        return _dir(path, "retain_transition_web", "过渡 read-only Web 工作台仍被静态测试覆盖，等外部前端接管后再退休。")
    if path.startswith("apps/web_bridge"):
        return _dir(path, "retain_local_bridge", "本地 Web bridge 是历史 runtime/diagnostic 适配层，需在 Runtime Service v0.2 后复审。")
    if path == "apps":
        return _dir(path, "retain_application_entrypoints", "应用入口层，包含 API、CLI、Web 过渡面。")
    if path.startswith("configs"):
        return _dir(path, "retain_config_examples", "提交 example/config contract，不提交本地 secret 配置。")
    if path.startswith("data"):
        return _dir(path, "retain_runtime_placeholders", "只保留 ignored runtime 目录占位文件。")
    if path.startswith("docs/archive"):
        return _dir(path, "retain_historical_evidence", "历史证据归档，不作为当前入口；后续按中文摘要继续瘦身。")
    if path.startswith("docs/frontend_integration"):
        return _dir(path, "retain_frontend_handoff", "前端团队对接材料和 Runtime Service contract 映射。")
    if path.startswith("docs/handoff"):
        return _dir(path, "retain_handoff_evidence", "多切片交接证据；后续只允许摘要归档，不直接删。")
    if path.startswith("docs/maintenance"):
        return _dir(path, "retain_maintenance_ledger", "维护账本、清理记录和候选规则投影。")
    if path.startswith("docs/task_briefs"):
        return _dir(path, "retain_task_brief_history", "历史任务 brief；当前不作为产品入口。")
    if path.startswith("docs"):
        return _dir(path, "retain_docs_contract_or_current_reference", "架构、contract、runbook 或产品当前参考文档。")
    if path.startswith("examples"):
        return _dir(path, "retain_contract_fixtures", "示例输入和 contract fixture 被测试、CLI smoke 或文档引用。")
    if path.startswith("tests"):
        return _dir(path, "retain_verification_surface", "自动化验证面，支撑重构和前端对接边界。")
    if path.startswith("tools"):
        return _dir(path, "retain_maintenance_tools", "维护、审计和 staging 工具。")
    if path.startswith(("workflows", "prompts", "skills")):
        return _dir(path, "retain_agent_surface", "workflow、prompt、skill 等 Agent 执行投影。")
    return _dir(path, "manual_review_required", "未命中已知目录策略，需要人工复审。")


def _review_file(path: str, git_state: str) -> ReviewedPath:
    if path == "README.zh-CN.md":
        if git_state == "deleted":
            return _file(
                path,
                git_state,
                "remove_applied_pending_stage",
                "README.md 已作为中文主入口，旧中文副本已在工作树删除。",
                "提交删除后完成退休；如需恢复，必须证明 README.md 不能覆盖中文入口职责。",
            )
        return _file(path, git_state, "delete_candidate", "README.md 已作为中文主入口，旧中文副本会制造双入口漂移。", "删除或转为短跳转后再次运行审查。")
    if path in {"README.md", "AGENTS.md", "TASK_TRACKER.md", "DEVLOG.md", "pyproject.toml", ".gitignore", ".env.example", ".python-version", "LICENSE"}:
        return _file(path, git_state, "retain_project_entrypoint", "项目入口、规则、跟踪、配置或许可证。")
    if path == "apps/__init__.py":
        return _file(path, git_state, "retain_application_entrypoints", "apps Python package marker。")
    if path.endswith("/.gitkeep") and path.startswith("data/"):
        return _file(path, git_state, "retain_runtime_placeholder", "只用于保留 ignored runtime 目录结构。")
    if path.startswith("agentflow/"):
        return _file(path, git_state, "retain_backend_core", "平台 contract、harness、memory、router 或 skill 代码。")
    if path.startswith("agentflow_studio/"):
        return _file(path, git_state, "retain_studio_pipeline", "内容生产与分发 pipeline 代码。")
    if path.startswith("apps/api/"):
        return _file(path, git_state, "retain_runtime_service", "Runtime Service 对接面、模型、job、artifact 或文档。")
    if path.startswith("apps/reporting/"):
        return _file(path, git_state, "retain_application_reporting", "CLI 和旧 Web bridge 共用的应用层 report helper。")
    if path.startswith("apps/cli/"):
        return _file(path, git_state, "retain_cli_ops", "本地 CLI 命令入口或 registry。")
    if path.startswith("apps/web/"):
        return _file(path, git_state, "retain_transition_web", "过渡 read-only Web 工作台；等新前端上线后按测试覆盖退休。")
    if path.startswith("apps/web_bridge/"):
        return _file(path, git_state, "retain_local_bridge", "本地 Web bridge 适配层，Runtime Service v0.2 后复审。")
    if path.startswith("configs/"):
        status = "retain_split_candidate" if path == "configs/tool_catalog.yaml" else "retain_config_example"
        return _file(path, git_state, status, "配置 template、platform profile 或 tool catalog；不含本地 secret。")
    if path.startswith("docs/archive/"):
        return _file(path, git_state, "retain_historical_evidence", "历史执行证据，后续用中文摘要继续瘦身。")
    if path.startswith("docs/frontend_integration/"):
        return _file(path, git_state, "retain_frontend_handoff", "前端对接包、API 适配说明或 fixture。")
    if path.startswith("docs/handoff/"):
        return _file(path, git_state, "retain_handoff_evidence", "历史/当前切片交接证据。")
    if path.startswith("docs/maintenance/"):
        return _file(path, git_state, "retain_maintenance_ledger", "维护账本、清理记录或候选规范。")
    if path.startswith("docs/task_briefs/"):
        return _file(path, git_state, "retain_task_brief_history", "任务 brief 历史记录。")
    if path.startswith("docs/"):
        return _file(path, git_state, "retain_docs_contract_or_current_reference", "架构、contract、runbook、产品或测试参考文档。")
    if path.startswith("examples/"):
        return _file(path, git_state, "retain_contract_fixture", "示例输入、contract registry 或前端 request fixture。")
    if path.startswith("tests/"):
        return _file(path, git_state, "retain_verification_surface", "自动化测试或 fixture。")
    if path.startswith("tools/"):
        return _file(path, git_state, "retain_maintenance_tool", "维护、审计或 staging 工具。")
    if path.startswith(("workflows/", "prompts/", "skills/")):
        return _file(path, git_state, "retain_agent_surface", "Agent workflow、prompt 或 skill 投影。")
    return _file(path, git_state, "manual_review_required", "未命中已知文件策略，需要人工复审。", "补充分类策略或删除/归档。")


def _dir(path: str, status: str, rationale: str) -> ReviewedPath:
    return ReviewedPath(
        path=path,
        kind="directory",
        git_state="derived",
        status=status,
        rationale=rationale,
        retirement_condition="对应能力被替代、测试引用解除、维护账本记录后才能删除。",
    )


def _file(
    path: str,
    git_state: str,
    status: str,
    rationale: str,
    retirement_condition: str = "对应能力被替代、测试引用解除、维护账本记录后才能删除。",
) -> ReviewedPath:
    return ReviewedPath(
        path=path,
        kind="file",
        git_state=git_state,
        status=status,
        rationale=rationale,
        retirement_condition=retirement_condition,
    )


def _is_excluded(path: str) -> bool:
    parts = Path(path).parts
    return any(part in EXCLUDE_DIRS for part in parts)

if __name__ == "__main__":
    raise SystemExit(main())
