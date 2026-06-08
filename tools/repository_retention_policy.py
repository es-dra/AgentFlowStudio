from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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
    product_surface: str
    status: str
    rationale: str
    retirement_condition: str

    def as_dict(self) -> dict[str, str]:
        return {
            "path": self.path,
            "kind": self.kind,
            "git_state": self.git_state,
            "product_surface": self.product_surface,
            "status": self.status,
            "rationale": self.rationale,
            "retirement_condition": self.retirement_condition,
        }


def review_directory(path: str) -> ReviewedPath:
    if path == ".":
        return _dir(path, "production_spine", "current", "仓库根目录承载项目入口、配置、文档和源码。")
    if path in {"agentflow", "agentflow/contracts", "agentflow/harness", "agentflow/memory", "agentflow/router", "agentflow/skills"}:
        return _dir(path, "production_spine", "current", "平台 contract、harness、memory、router 或 skill 核心代码。")
    if path.startswith("agentflow_studio"):
        return _dir(path, "production_spine", "current", "内容生产与分发 pipeline 模块仍被测试和 CLI 覆盖；旧 demo 文件会在文件级降级。")
    if path.startswith("apps/api"):
        return _dir(path, "production_spine", "current", "Runtime Service 是前后端唯一对接面。")
    if path.startswith("apps/reporting"):
        return _dir(path, "production_spine", "current", "CLI、Runtime 和过渡面共用的应用层 report helper。")
    if path.startswith("apps/cli"):
        return _dir(path, "operations_spine", "current", "CLI 是本地运维、测试和 deterministic harness 入口；hidden support 命令会在文件级复审。")
    if path.startswith("apps/web_bridge"):
        return _dir(path, "delete_candidate", "legacy_runtime_surface", "旧 Web bridge 已退出当前产品主干，应直接删除。")
    if path.startswith("apps/web"):
        return _dir(path, "transition_surface", "retire_when_replaced", "过渡 read-only Web 工作台仍被静态测试覆盖，外部前端接管后应退休。")
    if path == "apps":
        return _dir(path, "production_spine", "current", "应用入口层，包含 API、CLI 和过渡面。")
    if path.startswith("configs"):
        return _dir(path, "supporting_contract", "current", "提交 example/config contract，不提交本地 secret 配置。")
    if path.startswith("data"):
        return _dir(path, "runtime_placeholder", "current", "只保留 ignored runtime 目录占位文件。")
    if path.startswith("docs/archive"):
        return _dir(path, "historical_reference", "archive_only", "历史证据归档，不作为当前入口。")
    if path.startswith("docs/frontend_integration"):
        return _dir(path, "production_spine", "current", "前端团队对接材料和 Runtime Service contract 映射。")
    if path.startswith("docs/handoff"):
        return _dir(path, "historical_reference", "archive_or_delete_when_indexed", "多切片交接证据；应继续摘要归档和删减。")
    if path.startswith("docs/maintenance"):
        return _dir(path, "production_spine", "current", "维护账本、清理记录和候选规则投影。")
    if path.startswith("docs/task_briefs"):
        return _dir(path, "historical_reference", "archive_or_delete_when_indexed", "历史任务 brief；当前不作为产品入口。")
    if path.startswith("docs"):
        return _dir(path, "mixed_docs_surface", "review_for_currentness", "架构、contract、runbook 或产品当前参考文档；旧长文需要继续归档。")
    if path.startswith("examples"):
        return _dir(path, "supporting_contract", "current", "示例输入和 contract fixture 被测试、CLI smoke 或文档引用。")
    if path.startswith("tests"):
        return _dir(path, "verification_surface", "current", "自动化验证面，支撑重构和前端对接边界。")
    if path.startswith("tools"):
        return _dir(path, "production_spine", "current", "维护、审计和 staging 工具。")
    if path.startswith(("workflows", "prompts", "skills")):
        return _dir(path, "agent_surface", "current", "workflow、prompt、skill 等 Agent 执行投影。")
    return _dir(path, "unknown_surface", "manual_review_required", "未命中已知目录策略，需要人工复审。")


def review_file(path: str, git_state: str) -> ReviewedPath:
    if git_state == "deleted":
        return _file(
            path,
            git_state,
            "delete_candidate",
            "remove_applied_pending_stage",
            "已按当前维护账本在工作树删除，等待提交完成退休。",
            "提交删除后完成退休；如需恢复，必须重新证明其服务当前产品主干。",
        )
    if path == "README.zh-CN.md":
        if git_state == "deleted":
            return _file(
                path,
                git_state,
                "delete_candidate",
                "remove_applied_pending_stage",
                "README.md 已作为中文主入口，旧中文副本已在工作树删除。",
                "提交删除后完成退休；如需恢复，必须证明 README.md 不能覆盖中文入口职责。",
            )
        return _file(path, git_state, "delete_candidate", "delete_candidate", "README.md 已作为中文主入口，旧中文副本会制造双入口漂移。", "删除或转为短跳转后再次运行审查。")
    if path in {"README.md", "AGENTS.md", "TASK_TRACKER.md", "DEVLOG.md", "pyproject.toml", ".gitignore", ".env.example", ".python-version", "LICENSE"}:
        return _file(path, git_state, "production_spine", "current", "项目入口、规则、跟踪、配置或许可证。")
    if path == "apps/__init__.py":
        return _file(path, git_state, "production_spine", "current", "apps Python package marker。")
    if path.endswith("/.gitkeep") and path.startswith("data/"):
        return _file(path, git_state, "runtime_placeholder", "current", "只用于保留 ignored runtime 目录结构。")
    if path.startswith("agentflow/"):
        return _file(path, git_state, "production_spine", "current", "平台 contract、harness、memory、router 或 skill 代码。")
    if _is_memory_advantage_demo_file(path):
        return _file(
            path,
            git_state,
            "quarantine_candidate",
            "legacy_demo_runtime",
            "编号式 memory advantage demo 是历史实验入口，已不属于当前产品脊柱。",
            "迁移仍有价值的 evidence 到 archive summary / generic memory video pipeline 后删除 importable module。",
        )
    if path.startswith("agentflow_studio/"):
        return _file(path, git_state, "production_spine", "current", "内容生产与分发 pipeline 代码。")
    if path.startswith("apps/api/"):
        return _file(path, git_state, "production_spine", "current", "Runtime Service 对接面、模型、job、artifact 或文档。")
    if path.startswith("apps/reporting/"):
        return _file(path, git_state, "production_spine", "current", "CLI、Runtime 和过渡面共用的应用层 report helper。")
    if path == "apps/cli/memory_demo_commands.py":
        if git_state == "deleted":
            return _file(
                path,
                git_state,
                "delete_candidate",
                "remove_applied_pending_stage",
                "旧编号 demo CLI 入口已在工作树删除，等待提交完成退休。",
                "提交删除后完成退休；如需恢复，必须证明旧 demo CLI 仍服务当前产品脊柱。",
            )
        return _file(path, git_state, "quarantine_candidate", "legacy_demo_cli", "只服务编号式 memory advantage demo 的 hidden CLI 命令，应从正式 CLI 体系退休。", "旧 demo module 删除后同步删除该命令文件和 registry 引用。")
    if path == "apps/cli/support_command_registry.py":
        return _file(path, git_state, "transition_surface", "hidden_provider_and_legacy_cli", "隐藏 provider smoke 与旧 demo 命令集中注册；必须继续压缩到 provider gate / tools experimental。", "provider smoke 进入显式 gate 或工具目录、旧 demo 命令删除后退休。")
    if path.startswith("apps/cli/"):
        return _file(path, git_state, "operations_spine", "current", "本地 CLI 命令入口或 registry。")
    if path.startswith("apps/web_bridge/"):
        return _file(path, git_state, "delete_candidate", "legacy_runtime_surface", "本地 Web bridge 已退出当前产品主干，应直接删除。", "提交删除并保持 Runtime Service / local artifact 边界后完成退休。")
    if path.startswith("apps/web/"):
        return _file(path, git_state, "transition_surface", "retire_when_replaced", "过渡 read-only Web 工作台；外部前端上线后按测试覆盖退休。")
    if path.startswith("configs/"):
        status = "split_candidate" if path == "configs/tool_catalog.yaml" else "current"
        return _file(path, git_state, "supporting_contract", status, "配置 template、platform profile 或 tool catalog；不含本地 secret。")
    if path.startswith("docs/archive/"):
        return _file(path, git_state, "historical_reference", "archive_only", "历史执行证据，后续用中文摘要继续瘦身。")
    if path.startswith("docs/frontend_integration/"):
        return _file(path, git_state, "production_spine", "current", "前端对接包、API 适配说明或 fixture。")
    if path.startswith("docs/handoff/"):
        return _file(path, git_state, "historical_reference", "archive_or_delete_when_indexed", "历史/当前切片交接证据，应继续摘要归档和删减。")
    if path.startswith("docs/maintenance/"):
        return _file(path, git_state, "production_spine", "current", "维护账本、清理记录或候选规范。")
    if path.startswith("docs/task_briefs/"):
        return _file(path, git_state, "historical_reference", "archive_or_delete_when_indexed", "任务 brief 历史记录。")
    if path.startswith("docs/"):
        return _file(path, git_state, "mixed_docs_surface", "review_for_currentness", "架构、contract、runbook、产品或测试参考文档。")
    if path.startswith("examples/"):
        return _file(path, git_state, "supporting_contract", "current", "示例输入、contract registry 或前端 request fixture。")
    if path in {"tests/test_memory_advantage_demo_012.py", "tests/test_memory_advantage_demo_015.py"} or path.startswith("tests/memory_advantage_demo_"):
        return _file(path, git_state, "quarantine_candidate", "legacy_demo_verification", "只覆盖编号式历史 demo；旧 demo 退休时应同步删除或迁移为 generic pipeline 测试。", "generic memory video pipeline 覆盖同等 evidence 后删除。")
    if path.startswith("tests/"):
        return _file(path, git_state, "verification_surface", "current", "自动化测试或 fixture。")
    if path.startswith("tools/"):
        return _file(path, git_state, "production_spine", "current", "维护、审计或 staging 工具。")
    if path.startswith(("workflows/", "prompts/", "skills/")):
        return _file(path, git_state, "agent_surface", "current", "Agent workflow、prompt 或 skill 投影。")
    return _file(path, git_state, "unknown_surface", "manual_review_required", "未命中已知文件策略，需要人工复审。", "补充分类策略或删除/归档。")


def is_excluded(path: str) -> bool:
    parts = Path(path).parts
    return any(part in EXCLUDE_DIRS for part in parts)


def _is_memory_advantage_demo_file(path: str) -> bool:
    name = Path(path).name
    return path.startswith("agentflow_studio/") and name.startswith("memory_advantage_demo_")


def _dir(path: str, product_surface: str, status: str, rationale: str) -> ReviewedPath:
    return ReviewedPath(
        path=path,
        kind="directory",
        git_state="derived",
        product_surface=product_surface,
        status=status,
        rationale=rationale,
        retirement_condition="对应能力被替代、测试引用解除、维护账本记录后才能删除。",
    )


def _file(
    path: str,
    git_state: str,
    product_surface: str,
    status: str,
    rationale: str,
    retirement_condition: str = "对应能力被替代、测试引用解除、维护账本记录后才能删除。",
) -> ReviewedPath:
    return ReviewedPath(
        path=path,
        kind="file",
        git_state=git_state,
        product_surface=product_surface,
        status=status,
        rationale=rationale,
        retirement_condition=retirement_condition,
    )
