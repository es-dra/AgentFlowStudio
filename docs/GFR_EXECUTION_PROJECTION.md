# GFR 执行投影

本文是 Company OS / GFR V1 基线在 AgentFlow Studio 仓库里的执行投影。

它不是源头规则，也不替代 `10-Startup`。它的作用是让后续进入 AFS
项目的 Agent 能够快速知道：应该读哪些源头文件、如何启动任务、写入边界
在哪里、如何验证、什么反馈可以回流 COS。

## 源头控制文件

涉及 AFS 的 substantial 任务，先读这些文件：

```text
D:\Learning materials\Learning_notes\10-Startup\00-Company-OS\AI-Native-Company-OS-MAP.md
D:\Learning materials\Learning_notes\10-Startup\00-Company-OS\GFR-Global-Rule-Compiler.md
D:\Learning materials\Learning_notes\10-Startup\00-Company-OS\default-context-packs.md
D:\Learning materials\Learning_notes\10-Startup\00-Company-OS\context-pack-index.json
D:\Learning materials\Learning_notes\10-Startup\00-Company-OS\COS-V1-BASELINE.md
D:\Learning materials\Learning_notes\10-Startup\70-Projects\AgentFlow-Studio\PROJECT-CAPSULE.md
```

AFS 仓库只保存执行投影。公司源头规则、私有战略、客户材料、真实成本、
合同原文、provider 配置和密钥不写入本仓库。

## 启动行为

 substantial 任务必须由 GFR 编译，或者在对话内部明确应用同等结构：

```text
identity
task type
work modes
context pack
required reads
write scope
non-goals
evidence standard
tool/provider gates
verification route
feedback route
human decisions
```

AFS 开发任务通常读取 `context-pack-index.json` 中的：

```text
engineering_delivery
afs_project
```

如果任务涉及 COS 反馈、规则候选、经验晋升，再追加：

```text
rule_steward
```

## 仓库边界

本仓库可以保存：

- 代码、测试、schema、contract、runbook、handoff。
- safe manifest、safe summary、可公开或半公开工程说明。
- AFS 当前执行状态、验证命令、交接记录。

本仓库不能保存：

- secret、token、cookie、signed URL、provider key。
- provider 原始响应、生成媒体字节、本地私有素材字节。
- 私有战略、真实客户信息、真实成本、合同原文、未公开合作方判断。
- 未经人工审查就晋升为 active 的 Company OS 候选规则。

## 证据边界

AFS closeout 必须区分这些状态：

| 状态 | 说明 |
|---|---|
| Structure verification | 文件、schema、静态检查、fixture 形状正确。 |
| Runtime verification | Runtime Service 或 Studio 真正跑过目标路径。 |
| Provider smoke | 显式 gate 下跑通过某个远程 provider 路径。 |
| Human acceptance | 创始人或目标用户接受结果。 |
| Business validation | 市场、客户、ROI、付费或分发证据支持判断。 |
| Memory promotion | 候选证据经过人工审查后被晋升。 |

Provider smoke 不是 human acceptance。Runtime verification 不是 business
validation。Candidate memory 不是 durable memory。

## 验证命令

修改 COS/GFR 路由或 AFS 投影时，至少运行：

```powershell
python "D:\Learning materials\Learning_notes\10-Startup\80-Workflow\ai-native-company-workflow\tools\gfr_audit.py" --root "D:\Learning materials\Learning_notes\10-Startup" --pack-index "D:\Learning materials\Learning_notes\10-Startup\00-Company-OS\context-pack-index.json" --packets-dir "D:\Learning materials\Learning_notes\10-Startup\80-Workflow\ai-native-company-workflow\task-startup-packets"
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe "D:\Learning materials\Learning_notes\10-Startup\80-Workflow\ai-native-company-workflow\contracts\scripts\validate_ai_native_contracts.py"
git -C "D:\Projects\AgentFlowStudio" diff --check
```

如果改动涉及代码，还必须继续执行 `AGENTS.md` 中要求的 pytest、Studio JS、
maintenance audit 和 Runtime 相关验证。

## 失败信号

出现以下情况，应视为 GFR 启动失败：

- 新任务从旧 AFS draft 或旧展示材料开始，而不是从 Project Capsule 开始。
- 编辑前说不清 identity、读写范围、provider gate、验证命令和反馈路径。
- 把 provider 成功写成用户接受或商业验证。
- 把项目经验直接写成 Company OS active rule。
- 把私有战略、合同、客户、成本或 provider 原文写入 AFS 仓库。
