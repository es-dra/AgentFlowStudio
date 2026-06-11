# AFS Mainline Foundation Cleanup 001

中文摘要：本文是早期主线基础清理的维护记录，当前只作为理解收口经验的辅助证据。现在主线已经转向 Studio、Runtime API、知识库和创作智能体；任何与旧 Web、旧 Workbench 或旧维护叙事绑定的内容都不应再作为当前任务入口。后续若索引不再引用，应直接删除。

保留理由：本文可以帮助理解为什么仓库采用 provider gate、safe artifact、trace-first 和非声明边界。它不应扩大当前任务范围，也不应恢复旧路径。后续维护应以当前 AGENTS、TASK_TRACKER、DEVLOG、Studio handoff 和 Runtime 测试为准；如果这些入口已经覆盖本文内容，就应移除本文。

Status: in progress

Date: 2026-06-03

## Goal

Consolidate AgentFlow Studio after the Production Memory Asset Loop MVP:

```text
merge current PR head
-> establish local and remote mainline
-> audit Loulan evidence branch
-> adopt generic positioning evidence
-> clean merged feature branches and worktrees
```

## Mainline Decision

`master` is the repository mainline. The root checkout should be returned to a
clean `master` state before new maintenance or feature work continues.

Current product framing:

```text
Product: memory-driven AI content production workbench
Architecture: Production Memory Architecture
Long-term vision: Memory OS
```

## Loulan Branch Audit

`codex/loulan-memory-pilot` exposed useful AFS requirements, but it is not the
AFS main product branch.

The branch contains many project-specific modules, commands, Web inspectors,
tests, examples, and handoff records. They are useful as evidence but should
not be merged as one product line.

Generic evidence adopted into mainline:

- product positioning reset;
- Production Memory Architecture naming;
- pressure-sample boundary;
- candidate-only Company knowledge-base feedback loop;
- reminder that tests, provider smoke, human acceptance, and business
  validation are separate claim levels.

Not adopted:

- project-specific content-production flow;
- project-specific Web inspectors;
- project-specific commands and contracts;
- local media, provider routes, private paths, or approval assumptions.

## Cleanup Policy

Merged feature branches can be removed locally and remotely after verifying
they are contained in `origin/master`.

Unmerged evidence branches should be archived before deletion.

No Company knowledge-base files are written by this cleanup.

No provider is called by this cleanup.

## Follow-Up

After this cleanup, the next discussion should focus on project redundancy and
maintainability improvements before cutting a stable testing baseline.
