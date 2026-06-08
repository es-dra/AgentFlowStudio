# Workflow 目录

本目录只保存当前可维护的 YAML workflow definitions。Agent 和前端原型不要扫描全部 workflow 后自行猜测入口，应优先使用下面的当前入口。

## 当前推荐入口

| Workflow | 类型 | 适用场景 | 主要输出 |
|---|---|---|---|
| `clip_plan_to_real_clips.yaml` | slicing / stable | 已有 `clip_plan.json`，需要执行真实切片。 | `clip_plan_validation.json`、`real_slice_manifest.json`、`clips/` |
| `video_to_real_clips.yaml` | slicing / stable | 源视频 + 本地 fixture ASR，生成高亮计划并执行真实切片。 | `transcript.json`、`highlight_plan.json`、`clip_plan.json`、`real_slice_manifest.json`、`clips/` |
| `video_to_highlight_clip_plan.yaml` | planning / stable | 源视频 + 本地 fixture ASR，只生成高亮和切片计划。 | `transcript.json`、`highlight_plan.json`、`clip_plan.json` |
| `video_to_transcript.yaml` | transcription / local fixture | 只验证视频到 transcript 的本地链路。 | `audio_manifest.json`、`transcript.json` |
| `video_to_transcript_real_asr.yaml` | transcription / gated | 明确授权 ASR 后使用远程兼容 provider。 | `audio_manifest.json`、`transcript.json` |
| `transcript_to_candidate_windows.yaml` | candidate / stable | 已有 transcript，需要候选窗口。 | `candidate_windows.json` |
| `transcript_to_highlight_clip_plan.yaml` | planning / stable | 已有 transcript，需要高亮计划和 clip plan。 | `highlight_plan.json`、`clip_plan.json` |
| `video_subtitle_ocr_to_highlight_plan.yaml` | candidate / stable | 使用 OCR subtitle fixture 做候选窗口与评分。 | `ocr_transcript.json`、`candidate_windows.json`、`highlight_score_report.json`、`selection_diagnostics.json` |
| `agentflow_production_handoff.yaml` | production / stable | 从 creative brief 生成结构化 production handoff。 | `production_handoff.json`、`production_report.md`、`memory_candidates.json`、`cost_quality_trace.json` |
| `posterflow_memory_demo.yaml` | demo / optional remote image | 显式授权远程 image provider 后验证视觉记忆 demo。 | `poster_candidates_manifest.json`、`poster_preview.html`、`poster_memory_candidates.json` |

## 已退休入口

以下旧后处理 workflow 不再维护，已从主线删除：

- clips to final video assembly。
- subtitle burn。
- BGM mix。
- cover export。
- finished package。
- delivery readiness。
- video/script to finished package。

删除原因：这些入口不服务 Runtime Service、Production Memory Asset Loop、Project Manifest、Provider Gate、maintenance audit 或 read-only artifact viewer 的当前主线。只读 artifact viewer 可以继续识别历史 artifact 文件名，但仓库不再维护对应生成 pipeline。

## 常用命令

```powershell
.venv\Scripts\afs run-workflow --workflow workflows/video_to_real_clips.yaml --input examples/demo_asr/video_to_highlight_clip_plan_input.example.json --output data/processed/runs/demo_video_to_real_clips
.venv\Scripts\afs inspect-run --run-dir data/processed/runs/demo_video_to_real_clips
.venv\Scripts\afs review-run --run-dir data/processed/runs/demo_video_to_real_clips
```

Production Handoff 示例：

```powershell
.venv\Scripts\afs run-workflow --workflow workflows/agentflow_production_handoff.yaml --input examples/agentflow_production/creative_brief.example.json --output data/processed/runs/demo_agentflow_production_handoff
.venv\Scripts\afs inspect-run --run-dir data/processed/runs/demo_agentflow_production_handoff
.venv\Scripts\afs review-run --run-dir data/processed/runs/demo_agentflow_production_handoff
```

## 边界

- workflow 输出默认写入 `data/processed/` 或 `data/reports/`，这些目录被 Git ignore。
- 真实媒体不提交。
- provider 调用必须有显式 capability gate。
- workflow 通过不等于 human acceptance。
- provider smoke 不等于 business validation。
- memory candidate 不等于 durable memory。
