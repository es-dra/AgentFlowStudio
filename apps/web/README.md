# AFS 过渡 Web 工作台

本目录保存本地静态 Web workbench。它是过渡 read-only 工具，不是最终前端产品；后续外部画布工作台应主要对接 Runtime Service。

## 模式

- `Review Mode`：read-only、local-only，只检查用户显式选择的 artifact。
- `Production Mode`：通过本地 Web Bridge 在 `127.0.0.1` 上做受监督本地执行。
- `Memory Workbench`：static/local-only evidence canvas，用于 Project -> Assets -> Memory Loaded -> Baseline Run -> Memory-backed Run -> Review -> Feedback -> Next Pass。

直接打开：

```text
apps/web/index.html
```

`Review Mode` 和 `Memory Workbench` 不需要 server。`Production Mode` 需要先启动本地 bridge：

```powershell
python -m apps.cli.main web-bridge --host 127.0.0.1 --port 8787
```

浏览器只连接 `http://127.0.0.1:8787`。

## 当前切片

当前工作台线包括：

- M1.1 safe local artifact parsing。
- M1.2 default Chinese UI，语言切换只保存在 in-memory 状态。
- M1.2.1 更密集的 workbench layout 和 acceptance-oriented metrics。
- M1.3 expanded artifact universe。
- M1.4 production-oriented review information architecture。
- M1.5 explicit local video preview，只支持用户显式选择的 `.mp4`、`.webm`、`.mov`。
- M2 feedback event copy，用于人工复制/export JSON。
- M3 / M3.1 supervised Production Mode。
- M4 到 M4.9 static Memory Workbench、artifact inspector、protocol panel、demo evidence summary。
- M5 到 M5.3 Canvas polish、demo-ready checklist、readiness cockpit、operator command dock。

历史详情见：

- `../../docs/workbench/web_workbench_milestones.md`
- `../../docs/workbench/web_workbench_reference.md`

## 支持的 Artifact

推荐 product-run 文件：

```text
run_manifest.json
finished_package_manifest.json
quality_report.json
review_report.json
package_report.md
```

可选只读 artifact：

```text
delivery_readiness.json
delivery_readiness.md
selection_diagnostics.json
highlight_score_report.json
candidate_windows.json
clip_plan.json
real_slice_manifest.json
final_video_manifest.json
subtitle_manifest.json
audio_mix_manifest.json
cover_manifest.json
```

分类规则：

- `known_contract`：已支持的 AFS artifact。
- `unknown_json`：可解析 JSON，但不进入验收 summary。
- `unsupported_file`：只作为 load note。
- `local_media`：只用于 local video preview。

缺少 `schema_version` 是 warning，不是 fatal error。

## 边界

- read-only。
- local-only。
- no upload。
- no backend execution in Review Mode。
- no remote backend execution。
- no persistence。
- no browser persistence。
- no provider calls。
- no provider config。
- no workflow execution in Review Mode。
- no browser-side workflow execution。
- no automatic directory scanning。
- does not scan directories。
- no manifest path auto-read。
- no SaaS、account system、cloud storage、database、collaboration service。

`feedback event copy` 只生成 JSON 文本，供人工复制。它 does not write files，不上传数据，不调用 backend，也不持久化状态。

`local video preview` 只使用用户显式选择的本地视频文件。

## 编码说明

source files are utf-8。浏览器可直接渲染中文；部分 Windows terminal 可能出现 terminal mojibake。审查时优先用浏览器或 UTF-8 编辑器。
