# AFS Studio 全量内测运行记录 - 2026-06-21

## 运行信息

分支：`codex/full-internal-beta-qa-20260621`

目标：在内测前用多角色浏览器测试、Runtime 契约测试、非 video 模型通路检查和三端/服务器检查，提前发现并修复 Studio 问题。

边界：

- 可检查 LLM、image、vision 等非 video 能力，但只在 gate 和配置允许时执行。
- video、ASR、external download 保持关闭。
- 不在记录中写入 secret、provider raw response、signed URL、本地私有素材字节、invite code、session token。

## 进度

| 阶段 | 状态 | 证据 |
|---|---|---|
| 启动扫描 | 已完成 | `AGENTS.md`、`docs/company_operating_model.md`、`TASK_TRACKER.md`、`DEVLOG.md` |
| 本地基线 | 已完成 | pytest 572 passed；Studio JS 98 files passed；CLI help/version passed；maintenance audit failed=0；`git diff --check` passed |
| 浏览器角色链路 | 已完成 | `runs/final_existing_browser_qa_stub_20260621.json`；`runs/final_full_coverage_browser_qa_20260621.json` |
| 服务器和三端检查 | 已完成 | 三端预检、公开边缘预检、服务器 LLM/image/vision 非 video smoke |
| 修复批次 | 已完成 | 见 Findings |
| 最终回归 | 已完成 | pytest 572 passed；两条 browser QA passed；无 console/network 失败 |

## Findings

| ID | 严重级别 | 角色 | 表面 | 复现 | 状态 |
|---|---|---|---|---|---|
| FCQA-001 | S2 | QA 审查者 | 浏览器 QA 启动 | 本机设置 `HTTP_PROXY/HTTPS_PROXY/ALL_PROXY` 时，Python `urlopen` 健康探测访问 `127.0.0.1` 走代理并得到 502，Runtime 实际未收到请求。 | 已修复：QA health probe 使用 no-proxy opener，Runtime 子进程补 `NO_PROXY` 和正确 `AFS_RUNTIME_ROOT`。 |
| FCQA-002 | S2 | QA 审查者 | 旧浏览器 QA 脚本 | 当前创建菜单已改为 quick-create 卡片，旧脚本仍按隐藏 `.menu-item:nth(1)` 点击，导致超时。 | 已修复：脚本点击可见 quick-create 图片卡片，并收窄“保存素材”按钮选择器。 |
| FCQA-003 | S1 | 新创作者 | 团团层级 | 固定素材面板中点击“确认固定”时，团团浮层位于 `var(--z-modal)+1`，拦截模态按钮点击。 | 已修复：团团作为画布伴随层降到 `var(--z-promptbar)-1`，低于 prompt bar、dock、drawer、popover、modal。 |
| FCQA-004 | S2 | 素材管理员 | 素材详情 | 点击普通上传图片素材详情时，前端把 image asset id 请求到 `/visual-assets/{id}`，产生 404 和控制台错误。 | 已修复：普通图片素材只展示本地安全详情；只有 visual asset id 才请求 visual asset detail。 |
| FCQA-005 | S2 | QA 审查者 | 浏览器 QA 稳定性 | 本地 provider registry 没有 `prompt_optimizer` 服务且 `minimax_m3` 配置未就绪时，主浏览器链路无法稳定覆盖 UI。 | 已处理：新增 `--stub-llm` QA 模式，仅用于浏览器 UI/Runtime 交互覆盖；真实 LLM 连通性转入服务器/配置 smoke。 |

## 验证日志

| 时间 | 命令或场景 | 结果 | 备注 |
|---|---|---|---|
| 2026-06-21 | `npm run check:studio-js` | 通过 | 98 files |
| 2026-06-21 | `python -m apps.cli.main --help` | 通过 | CLI 可用 |
| 2026-06-21 | `python -m apps.cli.main version` | 通过 | `0.1.0` |
| 2026-06-21 | `python tools/maintenance_audit.py` | 通过，warning only | failed=0 |
| 2026-06-21 | `python -m pytest -q` | 通过 | 572 passed / 527 deselected / 2 warnings |
| 2026-06-21 | `git diff --check` | 通过 | 无输出 |
| 2026-06-21 | `python -m pytest -q tests/test_studio_asset_context_browser_qa_support.py` | 通过 | 3 passed / 1 existing warning |
| 2026-06-21 | `python -m pytest -q tests/test_web_studio_sprite_static.py` | 通过 | 1 passed |
| 2026-06-21 | `python -m pytest -q tests/test_web_studio_frontend_wave.py::test_asset_drawer_has_app_context_menu_and_image_delete_action` | 通过 | 1 passed |
| 2026-06-21 | `python -m pytest -q tests/test_web_studio_loop003_static.py::test_loop003_qal003_003_asset_detail_reads_runtime_and_exposes_node_actions` | 通过 | 静态契约同步到 visual asset id 分支 |
| 2026-06-21 | `python tools/studio_asset_context_browser_qa.py --stub-llm ...` | 通过 | `runs/final_existing_browser_qa_stub_20260621.json`；上传、固定素材、优化、连接建议、图片 gate blocked、对比报告 |
| 2026-06-21 | `python tools/studio_full_coverage_browser_qa.py ...` | 通过 | `runs/final_full_coverage_browser_qa_20260621.json`；素材预览/删除、团团等待光流和文案轮换、小视口、刷新恢复；console/network error 均为 0 |
