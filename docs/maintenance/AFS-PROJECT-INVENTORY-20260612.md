# AFS Project Inventory

中文摘要：本轮建立了可复跑的项目 inventory / cleanup 工具，并执行低风险本地缓存清理。已删除 `__pycache__`、`.pytest_cache` 和可枚举 pytest basetemp 缓存目标，累计删除 14,452 个缓存目标，约 30.24MB。`configs/providers.local.json`、`configs/models.yaml`、`data/models/`、`data/raw/` 和大型媒体证据均保持 report-only，未被删除。

残留说明：`data/processed/pytest-basetemp` 仍有一批历史目录拒绝当前用户读取 ACL / 删除，Python、PowerShell、`icacls` 均无法完全移除。该目录是 ignored 测试缓存，不影响 tracked 代码，但后续如果要彻底释放空间，需要用拥有该目录所有权的 Windows 用户或管理员 shell 单独清理。

维护结论：当前仓库的“代码冗余”和“本地产物膨胀”必须分开处理。正式产品代码以 git tracked 文件为准，本轮统计到 774 个 tracked 文件，主体维护压力来自 Runtime、Studio 前端和测试文件中少数超过 300 行的文件。ignored 区域的体积远大于 tracked 区域，但其中大部分不是应当提交或直接删除的产品代码，而是本地虚拟环境、模型权重、历史运行产物、媒体证据和测试缓存。后续 provider 中转站建设前，应优先拆分超限 Runtime/Studio 文件，并制定 `data/processed/runs` 的证据归档策略，避免真实模型接入后继续堆积大型媒体字节。

删减边界：本轮只自动删除可再生成缓存，包括 Python 字节码、pytest 缓存和可枚举的 basetemp 文件。凡是可能包含本地密钥、provider 配置、模型权重、原始素材、真实生成结果或人工验收证据的路径，均只进入 report-only 清单，不进入自动删除。这个边界是为了保证清理动作服务于可维护性，而不是把证据链或本地运行能力误删掉。对于历史媒体证据，下一步应按 run manifest 和任务价值决定冷存储、保留最新若干组，或只保留结构化 manifest。

直接删减补充：根据人工引用链核对，本轮继续删除无引用 tracked 空壳 `agentflow_studio/asset_manager/__init__.py`，删除 6 份已被 fixed `visual_asset` / graph resolver 取代的旧 `AFS-PRODUCTION-MEMORY-ASSET-*` handoff，并把 production-memory CLI 从默认可见产品面降为 hidden compatibility only。额外生成过的深度审计辅助代码未保留为仓库工具，避免为了审计继续增加维护面。

阻塞处理建议：`data/processed/pytest-basetemp` 下仍有部分目录拒绝当前用户访问，这不是代码阻塞，也不影响 tracked 验证，但会继续干扰 ignored 统计和本地磁盘清理。建议在下一次维护窗口用拥有该目录所有权的 Windows 用户或管理员 shell 处理；处理前仍应确认目标解析路径位于 `D:\Projects\AgentFlowStudio\data\processed\pytest-basetemp` 内，避免跨目录递归删除。

- Generated at: `2026-06-12T19:36:46`
- Git branch: `codex/afs-project-inventory-001`
- Tracked files: `774`
- Tracked lines: `86068`
- Ignored files: `10046`
- Ignored bytes: `3433518930`
- Auto-delete candidates: `15`
- Oversized tracked files: `7`

## Cleanup Result
- Deleted targets: `14`
- Skipped targets: `1`
- Bytes deleted: `41201`

## Warnings
- `warning: could not open directory 'data/processed/pytest-basetemp/current-ready-full/': Permission denied`
- `warning: could not open directory 'data/processed/pytest-basetemp/demo015-current/': Permission denied`
- `warning: could not open directory 'data/processed/pytest-basetemp/docs-current/': Permission denied`
- `warning: could not open directory 'data/processed/pytest-basetemp/docs-staged-record/': Permission denied`
- `warning: could not open directory 'data/processed/pytest-basetemp/full-current/': Permission denied`
- `warning: could not open directory 'data/processed/pytest-basetemp/full-precommit/': Permission denied`
- `warning: could not open directory 'data/processed/pytest-basetemp/full-staged/': Permission denied`
- `warning: could not open directory 'data/processed/pytest-basetemp/full-suite/': Permission denied`
- `warning: could not open directory 'data/processed/pytest-basetemp/post-rebase-full/': Permission denied`
- `warning: could not open directory 'data/processed/pytest-basetemp/postcommit-record/': Permission denied`
- `warning: could not open directory 'data/processed/pytest-basetemp/pr-readiness/': Permission denied`
- `warning: could not open directory 'data/processed/pytest-basetemp/pr-ready/': Permission denied`
- `warning: could not open directory 'data/processed/pytest-basetemp/pr-record/': Permission denied`
- `warning: could not open directory 'data/processed/pytest-basetemp/pr73-full/': Permission denied`
- `warning: could not open directory 'data/processed/pytest-basetemp/prepush/': Permission denied`
- `warning: could not open directory 'data/processed/pytest-basetemp/review-doc/': Permission denied`
- `warning: could not open directory 'data/processed/pytest-basetemp/review-final-full/': Permission denied`
- `warning: could not open directory 'data/processed/pytest-basetemp/review-fix-full/': Permission denied`
- `warning: could not open directory 'data/processed/pytest-basetemp/review-green/': Permission denied`
- `warning: could not open directory 'data/processed/pytest-basetemp/review-red/': Permission denied`
- `warning: could not open directory 'data/processed/pytest-basetemp/roadmap-docs-final/': Permission denied`
- `warning: could not open directory 'data/processed/pytest-basetemp/staging-preflight/': Permission denied`
- `warning: could not open directory 'data/processed/pytest-basetemp/tracker-staged-record/': Permission denied`

## Top Ignored Files
- `data/models/faster-whisper/models--Systran--faster-whisper-small/snapshots/536b0662742c02347bc0e980a01041f333bce120/model.bin`: 483546902 bytes; protected local model or original source
- `data/models/faster-whisper/models--Systran--faster-whisper-base/snapshots/ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66/model.bin`: 145217532 bytes; protected local model or original source
- `data/raw/demo_zombie/input.mp4`: 133788530 bytes; protected local model or original source
- `data/processed/runs/product_acceptance_video_script_local_asr_small_window_003/final_video_with_bgm.mp4`: 129623002 bytes; media or evidence artifact requires human retention decision
- `data/processed/runs/product_acceptance_video_script_phase14_2/final_video_with_bgm.mp4`: 129623002 bytes; media or evidence artifact requires human retention decision
- `data/processed/runs/product_acceptance_video_script_local_asr_small_window_003/final_video.mp4`: 129619563 bytes; media or evidence artifact requires human retention decision
- `data/processed/runs/product_acceptance_video_script_phase14_2/final_video.mp4`: 129619563 bytes; media or evidence artifact requires human retention decision
- `.venv/Lib/site-packages/playwright/driver/node.exe`: 91694408 bytes; local virtualenv environment
- `data/models/faster-whisper/models--Systran--faster-whisper-tiny/snapshots/d90ca5fe260221311c53c58e660288d3deb8d356/model.bin`: 75538270 bytes; protected local model or original source
- `.venv/Lib/site-packages/ctranslate2/ctranslate2.dll`: 59823104 bytes; local virtualenv environment
- `data/processed/runs/product_acceptance_video_script_local_asr_small_window_003/clips/clip_003.mp4`: 47574412 bytes; media or evidence artifact requires human retention decision
- `data/processed/runs/product_acceptance_video_script_phase14_2/clips/clip_003.mp4`: 47574412 bytes; media or evidence artifact requires human retention decision
- `data/processed/runs/product_acceptance_video_script_local_asr_small_window_003/clips/clip_001.mp4`: 38771951 bytes; media or evidence artifact requires human retention decision
- `data/processed/runs/product_acceptance_video_script_local_asr_small_window_003/clips/clip_002.mp4`: 38771951 bytes; media or evidence artifact requires human retention decision
- `data/processed/runs/product_acceptance_video_script_phase14_2/clips/clip_001.mp4`: 38771951 bytes; media or evidence artifact requires human retention decision
- `data/processed/runs/product_acceptance_video_script_phase14_2/clips/clip_002.mp4`: 38771951 bytes; media or evidence artifact requires human retention decision
- `data/processed/runs/memory_advantage_recording_016/neon_rain_turnback_i2v_20260529_194207/live/memory_backed/neon_rain_turnback/i2v/video_candidates/candidate_001.mp4`: 32430494 bytes; media or evidence artifact requires human retention decision
- `data/processed/runs/memory_advantage_recording_016/neon_rain_turnback_i2v_20260529_195452/live/memory_backed/neon_rain_turnback/i2v/video_candidates/candidate_001.mp4`: 31198488 bytes; media or evidence artifact requires human retention decision
- `data/processed/runs/memory_advantage_recording_016/neon_rain_turnback_i2v_20260529_194207/live/baseline/neon_rain_turnback/i2v/video_candidates/candidate_001.mp4`: 30695005 bytes; media or evidence artifact requires human retention decision
- `data/processed/runs/memory_advantage_recording_016/neon_rain_turnback_i2v_20260529_195452/live/baseline/neon_rain_turnback/i2v/video_candidates/candidate_001.mp4`: 30053463 bytes; media or evidence artifact requires human retention decision

## Oversized Tracked Files
- `apps/api/runtime_context_resolver.py`: 363 lines
- `apps/api/runtime_director_compiler.py`: 315 lines
- `apps/api/runtime_keyframes.py`: 354 lines
- `apps/api/runtime_service.py`: 308 lines
- `apps/studio/src/panels/director-shell.js`: 356 lines
- `tests/test_api_runtime_context_resolver.py`: 385 lines
- `tests/test_api_runtime_creative_agent_keyframes.py`: 314 lines

## Non-Claims
- Not human acceptance.
- Not business validation.
- Not durable memory.
