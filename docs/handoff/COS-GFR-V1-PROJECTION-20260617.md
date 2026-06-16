# COS / GFR V1 执行投影交接 - 2026-06-17

## 范围

本次只同步 COS/GFR V1 在 AFS 仓库内的执行投影。

它不修改 Runtime、Studio、provider adapter、模型配置或任何真实生成链路。
它的目标是让后续 AFS 开发线程明确使用新的 Company OS 控制入口，而不是回到
旧的 Memory OS、local-first 或 provider-gate-first 叙事。

## 源头文件

源头规则仍在本地知识库：

```text
D:\Learning materials\Learning_notes\10-Startup\00-Company-OS\COS-V1-BASELINE.md
D:\Learning materials\Learning_notes\10-Startup\00-Company-OS\context-pack-index.json
D:\Learning materials\Learning_notes\10-Startup\00-Company-OS\GFR-Global-Rule-Compiler.md
D:\Learning materials\Learning_notes\10-Startup\70-Projects\AgentFlow-Studio\PROJECT-CAPSULE.md
```

AFS 仓库内的投影文件：

```text
docs/GFR_EXECUTION_PROJECTION.md
AGENTS.md
docs/company_operating_model.md
```

## 预期工作流

后续 substantial AFS 任务应按这个顺序启动：

```text
project-development-workflow startup scan
  -> GFR packet 或等价内部应用
  -> engineering_delivery + afs_project context pack
  -> 明确写入范围、provider gate、验证命令
  -> 项目 handoff / DEVLOG
  -> 只有可复用经验才进入 Company OS feedback packet
```

## 边界

- 没有写入 secret、provider config、原始 provider 响应、生成媒体字节。
- 没有写入客户材料、真实成本、合同原文或未公开商业判断。
- 没有运行 live provider call。
- 没有把 Company OS candidate 自动晋升为 active rule。
- 本次只属于 structure verification 和 contract verification，不是 human
  acceptance，也不是 business validation。

## 验证命令

本次投影相关验证命令：

```powershell
python "D:\Learning materials\Learning_notes\10-Startup\80-Workflow\ai-native-company-workflow\tools\gfr_audit.py" --root "D:\Learning materials\Learning_notes\10-Startup" --pack-index "D:\Learning materials\Learning_notes\10-Startup\00-Company-OS\context-pack-index.json" --packets-dir "D:\Learning materials\Learning_notes\10-Startup\80-Workflow\ai-native-company-workflow\task-startup-packets"
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe "D:\Learning materials\Learning_notes\10-Startup\80-Workflow\ai-native-company-workflow\contracts\scripts\validate_ai_native_contracts.py"
git -C "D:\Learning materials\Learning_notes" diff --check
git -C "D:\Projects\AgentFlowStudio" diff --check
```

如果后续任务改代码，则继续追加 AFS pytest、Studio JS、Runtime smoke 和
maintenance audit。

## 下一次使用场景

优先在三类任务中继续检验 GFR 是否真实有效：

- AFS provider-connected validation。
- AFS algorithm-library continuation。
- Business/FDE 文件 intake 并转化为安全工程任务。
