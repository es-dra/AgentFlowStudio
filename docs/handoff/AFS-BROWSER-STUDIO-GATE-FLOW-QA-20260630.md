# AFS TaskRun - Browser Studio Gate Flow QA - 2026-06-30

## 任务

Task ID: `AFS-T13 Browser/Studio Gate Flow QA`

Branch: `codex/afs-project-book-full-goal-20260630`

Start HEAD: `f758ca8da101735cb48ae36b797dbbe0fba5c302`

Status: rendered QA completed; product code unchanged; commit/push handled
after this record is written.

本轮目标是在 T12 asset promotion gate provenance 之后，做一个不调用 provider 的
真实浏览器烟测，确认 `/studio/` 在本地 Runtime 下能加载、能处理空项目 gate、能从
“先新建项目”继续到角色设定模板节点。它不是全量浏览器验收，不是 provider smoke，
也不是人类创作验收。

## QA 环境

- 本地路径：`D:\Projects\AgentFlowStudio`
- Runtime URL：`http://127.0.0.1:8790/studio/`
- Runtime root：临时 `%TEMP%\afs-t13-runtime-*`
- Browser path：Codex in-app Browser
- Provider gates：显式设置为 false
  - `AFS_ALLOW_REMOTE_LLM=false`
  - `AFS_ALLOW_REMOTE_IMAGE=false`
  - `AFS_ALLOW_REMOTE_VIDEO=false`
  - `AFS_ALLOW_REMOTE_ASR=false`
  - `AFS_ALLOW_REMOTE_VISION=false`
  - `AFS_ALLOW_EXTERNAL_DOWNLOAD=false`
- QA 后清理：停止临时 Runtime，`8790` 端口监听数回到 `0`

## Dirty Ownership Ledger

| Surface | Ownership | Handling |
|---|---|---|
| `DEVLOG.md` | T13 record | Keep. |
| `TASK_TRACKER.md` | T13 routing entry | Keep. |
| `docs/handoff/INDEX.md` | T13 handoff index | Keep. |
| `docs/handoff/AFS-BROWSER-STUDIO-GATE-FLOW-QA-20260630.md` | T13 QA handoff | Keep. |
| External execution state YAML | T13 execution state | Update minimally outside AFS git. |
| Temp Runtime root | T13 local QA artifact | Not committed; temporary local runtime data only. |
| Browser screenshots | T13 chat evidence | Emitted in conversation only; not written to repo. |
| `docs/demo-docs-20260629/` | Existing untracked local docs | Do not touch, do not stage, do not clean. |

## Flow Under Test

`/studio/` loads -> user clicks `角色设定卡` while no project exists -> Studio
shows `请先新建项目` gate -> user clicks `新建项目` and `创建并切换` -> Studio
creates `AFS 内测项目` and materializes the role-setting template nodes.

## Results

| Check | Result |
|---|---|
| Runtime health | Passed: `status=ready`, `studio_static.status=ready`. |
| Provider gates | Passed: all observed gates were false in the QA runtime. |
| Page identity | Passed: `/studio/` redirected to `?project=studio-empty`; title was `AFS Studio 创作图谱`. |
| Blank-page check | Passed: DOM snapshot contained the Studio shell and starter templates. |
| Framework overlay | Passed: no error overlay observed in DOM or screenshot. |
| Console health | Passed: warning/error count remained `0` before and after interactions. |
| Empty-project gate | Passed: template click opened `请先新建项目`. |
| Continuation path | Passed: `新建项目` -> `创建并切换` created `AFS 内测项目` and 3 role-setting nodes. |
| Cleanup | Passed: temp Runtime stopped; `listener_count=0` on port `8790`. |

## Evidence Notes

- Screenshot 1 showed the Studio first screen: empty project shell, starter
  templates, assistant panel, and no visible framework overlay.
- Screenshot 2 showed the empty-project gate modal: `请先新建项目`.
- Screenshot 3 showed the created `AFS 内测项目` with three role-setting canvas
  nodes and saved state.
- Screenshots were emitted through the in-app Browser result stream and were
  intentionally not saved into the repository.

## Verification Commands And Browser APIs

```text
Invoke-RestMethod http://127.0.0.1:8790/health
# status=ready; studio_static.status=ready; provider_gates all false

Browser API sequence:
# browser.nameSession("AFS T13 Studio gate-flow QA")
# browser.tabs.new()
# tab.goto("http://127.0.0.1:8790/studio/")
# tab.playwright.domSnapshot()
# tab.dev.logs({ levels: ["error", "warn"], limit: 50 })
# tab.screenshot({ fullPage: false })
# click role-setting template
# click modal new-project continuation
# click create-and-switch
# final console warn/error count 0

Get-NetTCPConnection -LocalPort 8790 -State Listen
# listener_count=0 after cleanup

npm.cmd run check:studio-js
# JS syntax check passed: 127 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4
# existing warning counts remain: human_doc_chinese_coverage=22,
# secret_like_fragments=9, oversized_files=59

git diff --check
# passed

YAML parse check for AFS-Goal-Driven-Execution-State-v0.1.yaml
# yaml_parse_ok; current_task_id=AFS-T13
```

## Non-Claims

本轮不是：

- provider smoke
- generated media validation
- human creative acceptance
- business validation
- deployment verification
- server three-end sync
- full browser acceptance for every Studio flow

## Cleanup Review

- 临时 Runtime 已停止，没有留下后台服务。
- 临时 runtime root 未进入 git。
- 浏览器截图未进入仓库。
- 没有读取、输出或提交 secret、provider key、signed URL、cookie、token、
  本地私有素材字节、provider raw response 或生成媒体字节。
- `docs/demo-docs-20260629/` 保持未跟踪、未触碰。

## Deferred Items

- T13 没有打开 asset upload、image preview、fixed asset promotion modal 或
  provider generation 面板的完整浏览器路径。
- 若下一轮需要验证 T12 promotion provenance 的完整 UI path，需要准备一个
  deterministic image asset fixture 或专用 browser harness，仍应保持 provider gate
  closed。
- Provider smoke 必须等待用户显式授权具体能力。

## Evidence State

```text
runtime_browser_smoke_verified_studio_gate_flow
```

## Next Valid Task

```text
AFS-T14 Deterministic Promotion UI Harness or Provider-Smoke Readiness Review
```

在没有 provider 授权前，优先做 deterministic UI harness，而不是 provider smoke。
