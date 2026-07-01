# AFS Studio 团团 V2 项目记忆 API 交接 - 2026-06-23

## 范围

Worker 分支：

```text
codex/tuantuan-sprite-memory-api-20260623
```

Worktree：

```text
C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\tuantuan-sprite-memory-api-20260623
```

本切片只实现团团项目级安全记忆 API 的后端基础闭环：

- `GET /projects/{project_id}/sprite/memory`
- `POST /projects/{project_id}/sprite/memory`
- `DELETE /projects/{project_id}/sprite/memory/{memory_id}`
- `POST /projects/{project_id}/sprite/memory/clear`

## 改动文件

- `apps/api/runtime_sprite_memory.py`
- `apps/api/runtime_sprite.py`
- `tests/test_api_runtime_sprite_memory.py`

没有修改 storyboard、keyframe、context resolver、asset popover 或 Studio 前端文件。

## 安全边界

- 写入记忆必须显式传入 `user_confirmed: true`。
- 记忆只保存在 Runtime 项目目录下的 `projects/{project_id}/sprite_memory.json`。
- 状态中显式保留 `writes_company_kb: false` 和 `writes_long_term_memory: false`。
- secret 类文本、provider raw 引用、signed URL、本地媒体路径和私密客户信息会被拒绝。
- 本切片没有打开或新增 `action_execution_enabled`。
- Provider gate 没有变化，也没有启动任何 provider 调用。

## 验证

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_sprite.py tests\test_api_runtime_sprite_memory.py -q
17 passed, 1 warning
```

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_web_studio_sprite_static.py tests\test_api_runtime_sprite.py tests\test_api_runtime_sprite_memory.py -q
18 passed, 1 warning
```

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main --help
passed
```

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main version
0.1.0
```

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest
612 passed, 520 deselected, 2 warnings
```

```text
npm run check:studio-js
JS syntax check passed: 110 files
```

```text
git diff --check
passed
```

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\maintenance_audit.py
failed=0; status=warning，仅剩既有 legacy / 中文覆盖 / secret-like / oversized warnings
```

## 未完成事项

- 前端 opt-in 记忆 UI 不在本切片内。
- Chat 回复尚未读取或使用这些记忆。
- 团团 V2 的人类体验验收和视觉验收仍是后续工作，不能由本次测试通过直接替代。
