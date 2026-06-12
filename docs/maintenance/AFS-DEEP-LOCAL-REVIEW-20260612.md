# AFS Deep Local Review

中文摘要：本报告把 tracked、ignored、未忽略本地文件、`.git` 元数据、`.venv`、模型、媒体证据和运行缓存全部纳入同一张本地维护地图。项目自有文本做逐行级统计；本地配置、模型权重、原始素材、媒体字节和第三方虚拟环境只做元数据或哈希级审计，不读取或输出敏感内容。

- Generated at: `2026-06-12T19:54:15`
- Local files observed: `12791`
- Local bytes observed: `3457296904`
- Text files line-reviewed: `755`
- Text lines reviewed: `86993`
- Duplicate groups: `80`
- Duplicate removable bytes if one canonical copy is kept per group: `827477914`
- Mojibake candidates: `0`
- Task-marker candidates: `0`

## Core Findings
- 本地体量主要不在产品代码，而在 `data/processed` 媒体证据、`.venv`、本地模型缓存和原始素材。
- 可直接删除的缓存已由 inventory cleanup 清理；本轮新增发现以重复媒体证据为主，虽然重复度高，但仍需先建立 canonical run / evidence retention 规则。
- 项目文本已完成逐行级统计；可读性后续重点应放在超长文件拆分和重复 prompt/provider 路径收敛。

## Local File Kinds
- `media_or_evidence`: 671 files, 2117495293 bytes
- `local_model`: 17 files, 712299247 bytes
- `local_virtualenv`: 5522 files, 397065066 bytes
- `source_media`: 7 files, 147552901 bytes
- `runtime_or_evidence`: 3834 files, 72629132 bytes
- `repository_internal`: 1950 files, 6623751 bytes
- `project_text`: 755 files, 3496990 bytes
- `cache`: 10 files, 69583 bytes
- `binary_or_other`: 23 files, 63851 bytes
- `local_config`: 2 files, 1090 bytes

## Readability Risks
- No actionable mojibake or task-marker findings after filtering scanner/test fixtures and report self-markers.

## Duplicate Candidates
- 2 files x 129623002 bytes: `data/processed/runs/product_acceptance_video_script_local_asr_small_window_003/final_video_with_bgm.mp4`, `data/processed/runs/product_acceptance_video_script_phase14_2/final_video_with_bgm.mp4`
- 2 files x 129619563 bytes: `data/processed/runs/product_acceptance_video_script_local_asr_small_window_003/final_video.mp4`, `data/processed/runs/product_acceptance_video_script_phase14_2/final_video.mp4`
- 4 files x 38771951 bytes: `data/processed/runs/product_acceptance_video_script_local_asr_small_window_003/clips/clip_001.mp4`, `data/processed/runs/product_acceptance_video_script_local_asr_small_window_003/clips/clip_002.mp4`, `data/processed/runs/product_acceptance_video_script_phase14_2/clips/clip_001.mp4`, `data/processed/runs/product_acceptance_video_script_phase14_2/clips/clip_002.mp4`
- 2 files x 47574412 bytes: `data/processed/runs/product_acceptance_video_script_local_asr_small_window_003/clips/clip_003.mp4`, `data/processed/runs/product_acceptance_video_script_phase14_2/clips/clip_003.mp4`
- 3 files x 28391265 bytes: `data/processed/runs/product_acceptance_video_script_phase14_4b/final_video_with_bgm.mp4`, `data/processed/runs/product_acceptance_video_script_phase14_4e/final_video_with_bgm.mp4`, `data/processed/runs/product_acceptance_video_script_phase14_6/final_video_with_bgm.mp4`
- 3 files x 28387390 bytes: `data/processed/runs/product_acceptance_video_script_phase14_4b/final_video.mp4`, `data/processed/runs/product_acceptance_video_script_phase14_4e/final_video.mp4`, `data/processed/runs/product_acceptance_video_script_phase14_6/final_video.mp4`
- 2 files x 27729274 bytes: `data/processed/runs/product_acceptance_video_script_phase14_6_selection_quality/final_video_with_bgm.mp4`, `data/processed/runs/acceptance/v0_1_0_video_script/final_video_with_bgm.mp4`
- 2 files x 27725061 bytes: `data/processed/runs/product_acceptance_video_script_phase14_6_selection_quality/final_video.mp4`, `data/processed/runs/acceptance/v0_1_0_video_script/final_video.mp4`
- 5 files x 8367203 bytes: `data/processed/runs/acceptance/v0_1_0_video_script/clips/clip_001.mp4`, `data/processed/runs/product_acceptance_video_script_phase14_4b/clips/clip_001.mp4`, `data/processed/runs/product_acceptance_video_script_phase14_4e/clips/clip_001.mp4`, `data/processed/runs/product_acceptance_video_script_phase14_6/clips/clip_001.mp4`
- 6 files x 5816782 bytes: `data/processed/runs/acceptance/v0_1_0_video_script/clips/clip_002.mp4`, `data/processed/runs/product_acceptance_video_script_phase14_2d/clips/clip_003.mp4`, `data/processed/runs/product_acceptance_video_script_phase14_4b/clips/clip_002.mp4`, `data/processed/runs/product_acceptance_video_script_phase14_4e/clips/clip_002.mp4`
- 12 files x 1967644 bytes: `data/processed/runs/acceptance/v0_1_0_video_only/audio/audio.wav`, `data/processed/runs/demo_narratocut_package_alpha/audio/audio.wav`, `data/processed/runs/demo_narratocut_package_alpha_local_override/audio/audio.wav`, `data/processed/runs/demo_video_to_transcript_ffmpeg_real/audio/audio.wav`
- 3 files x 7695849 bytes: `data/processed/runs/product_acceptance_video_script_phase14_4b/clips/clip_003.mp4`, `data/processed/runs/product_acceptance_video_script_phase14_4e/clips/clip_003.mp4`, `data/processed/runs/product_acceptance_video_script_phase14_6/clips/clip_003.mp4`
- 3 files x 6511487 bytes: `data/processed/runs/product_acceptance_video_script_phase14_4b/clips/clip_004.mp4`, `data/processed/runs/product_acceptance_video_script_phase14_4e/clips/clip_004.mp4`, `data/processed/runs/product_acceptance_video_script_phase14_6/clips/clip_004.mp4`
- 8 files x 1990678 bytes: `data/processed/runs/acceptance/v0_1_0_video_script/audio/audio.wav`, `data/processed/runs/product_acceptance_video_script_local_asr_small_window_003/audio/audio.wav`, `data/processed/runs/product_acceptance_video_script_phase14_2/audio/audio.wav`, `data/processed/runs/product_acceptance_video_script_phase14_2d/audio/audio.wav`
- 4 files x 3925017 bytes: `data/processed/runs/demo_narratocut_package_alpha/final_video.mp4`, `data/processed/runs/demo_narratocut_package_alpha_local_override/final_video.mp4`, `data/processed/runs/product_acceptance_video_only_phase14_6_selection_quality/final_video.mp4`, `data/processed/runs/acceptance/v0_1_0_video_only/final_video.mp4`
- 4 files x 3922408 bytes: `data/processed/runs/demo_narratocut_package_alpha/final_video_with_bgm.mp4`, `data/processed/runs/demo_narratocut_package_alpha_local_override/final_video_with_bgm.mp4`, `data/processed/runs/product_acceptance_video_only_phase14_6_selection_quality/final_video_with_bgm.mp4`, `data/processed/runs/acceptance/v0_1_0_video_only/final_video_with_bgm.mp4`
- 2 files x 6822956 bytes: `data/processed/runs/acceptance/v0_1_0_video_script/clips/clip_004.mp4`, `data/processed/runs/product_acceptance_video_script_phase14_6_selection_quality/clips/clip_004.mp4`
- 2 files x 6722059 bytes: `data/processed/runs/acceptance/v0_1_0_video_script/clips/clip_003.mp4`, `data/processed/runs/product_acceptance_video_script_phase14_6_selection_quality/clips/clip_003.mp4`
- 5 files x 1938512 bytes: `data/processed/runs/closeout_real_workflow/clips/clip_001.mp4`, `data/processed/runs/demo_real_video/clips/clip_001.mp4`, `data/processed/runs/golden_path_phase13_real_clips/clips/clip_001.mp4`, `data/processed/runs/phase10_7_real/clips/clip_001.mp4`
- 2 files x 4504260 bytes: `data/processed/runs/product_acceptance_video_script_local_asr_small_window_003/clips/clip_004.mp4`, `data/processed/runs/product_acceptance_video_script_phase14_2/clips/clip_004.mp4`
- 9 files x 913343 bytes: `data/processed/runs/acceptance/v0_1_0_video_only/clips/clip_001.mp4`, `data/processed/runs/demo_narratocut_package_alpha/clips/clip_001.mp4`, `data/processed/runs/demo_narratocut_package_alpha_local_override/clips/clip_001.mp4`, `data/processed/runs/local_alpha_0_4_product_loop/clips/clip_001.mp4`
- 2 files x 4055283 bytes: `data/processed/runs/product_acceptance_video_only_phase14_4e/final_video_with_bgm.mp4`, `data/processed/runs/product_acceptance_video_only_phase14_6/final_video_with_bgm.mp4`
- 2 files x 4054707 bytes: `data/processed/runs/product_acceptance_video_only_phase14_4e/final_video.mp4`, `data/processed/runs/product_acceptance_video_only_phase14_6/final_video.mp4`
- 9 files x 875106 bytes: `data/processed/runs/acceptance/v0_1_0_video_only/clips/clip_002.mp4`, `data/processed/runs/demo_narratocut_package_alpha/clips/clip_002.mp4`, `data/processed/runs/demo_narratocut_package_alpha_local_override/clips/clip_002.mp4`, `data/processed/runs/local_alpha_0_4_product_loop/clips/clip_002.mp4`
- 7 files x 1046633 bytes: `data/processed/runs/acceptance/v0_1_0_video_only/clips/clip_003.mp4`, `data/processed/runs/demo_narratocut_package_alpha/clips/clip_003.mp4`, `data/processed/runs/demo_narratocut_package_alpha_local_override/clips/clip_003.mp4`, `data/processed/runs/product_acceptance_video_only_phase14_4b/clips/clip_003.mp4`
- 2 files x 3443756 bytes: `data/reports/project_inventory/20260612-cleanup/cleanup_plan.json`, `data/reports/project_inventory/20260612-dryrun/cleanup_plan.json`
- 3 files x 2281905 bytes: `data/processed/runs/phase12_2_clips_to_final_video_smoke_20260519/final_video.mp4`, `data/processed/runs/phase12_2_clips_to_final_video_smoke_20260519_final/final_video.mp4`, `data/processed/runs/phase12_2_clips_to_final_video_smoke_safe_20260519/final_video.mp4`
- 5 files x 1093776 bytes: `data/processed/runs/acceptance/v0_1_0_video_only/clips/clip_004.mp4`, `data/processed/runs/demo_narratocut_package_alpha/clips/clip_004.mp4`, `data/processed/runs/demo_narratocut_package_alpha_local_override/clips/clip_004.mp4`, `data/processed/runs/local_alpha_0_4_product_loop/clips/clip_004.mp4`
- 2 files x 2281325 bytes: `data/processed/runs/phase13_5_final_video_with_bgm_smoke_20260519/final_video_with_bgm.mp4`, `data/processed/runs/phase13_6_final_video_with_bgm_smoke_20260519/final_video_with_bgm.mp4`
- 2 files x 1392794 bytes: `data/processed/runs/product_acceptance_video_only_local_asr_small/final_video.mp4`, `data/processed/runs/product_acceptance_video_only_phase14_2/final_video.mp4`

## Cleanup Decision
- Do not delete duplicated media evidence automatically in this pass. Exact duplicates are real redundancy, but several paths are acceptance or provider evidence; deleting one side without a canonical-run rule would weaken traceability.
- Keep local provider config, model weights, source media and unique evidence report-only.
- Next cleanup slice should define retention: keep latest accepted run plus manifest, archive or delete older exact duplicate media bytes, and keep machine reports under `data/reports/project_inventory/` only while useful.

## Recommendations
- `P1` .venv: Keep out of product counts; recreate instead of reviewing as project code.
- `P1` duplicate evidence: Review duplicate runtime/evidence files before adding more providers; keep canonical manifests and avoid deleting unique acceptance evidence.
- `P2` long lines: Wrap long prose/config lines when editing touched files.

## Non-Claims
- Not human acceptance.
- Not business validation.
- Not durable memory.
