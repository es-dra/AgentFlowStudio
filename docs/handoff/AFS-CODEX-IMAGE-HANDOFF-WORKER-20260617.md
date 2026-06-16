# AFS Codex Image Handoff Worker - 2026-06-17

## 中文摘要

本切片解决的不是“人工在服务器上调用 Codex 生图”，而是把图片生成接成自动化链路：Studio 用户点击生成后，Runtime Service 创建 keyframe job，并在该 run 目录下写入安全任务包；后台 worker 自动扫描 pending 任务、调用服务器本地的 `codex exec` 执行生图、把候选图写回 `image_candidates/candidate_001.png`；Studio 只通过 Runtime poll 接口看到普通的生成中、完成或失败状态。

这版保留清晰边界：前端不显示 Codex、handoff、request.json、内部 job 目录等实现细节；API 响应不返回 provider raw response、secret、cookie、Authorization、signed URL、服务器绝对路径或媒体字节。fake executor 已经验证 Runtime 文件契约和前端轮询链路，但服务器上真实 `codex exec` 是否能稳定产出图片，仍需部署后做一次独立 provider smoke，不能直接等同于真人验收。

上线前服务器配置重点：在 server-local provider config 里启用 `codex_image`，只打开 `AFS_ALLOW_REMOTE_IMAGE=true`，启动一个只处理 runtime root 的 worker 服务。LLM、ASR、video、external download 的 gate 仍按各自能力独立控制，打开 image 不代表授权其他能力。

## Scope

This slice adds an automated image/keyframe provider path for the Studio MVP:

```text
Studio image generate
  -> Runtime Service keyframe submit
  -> async image provider adapter writes a safe job package
  -> background worker consumes pending jobs
  -> Runtime keyframe poll returns safe previews and reusable image assets
```

The user-facing Studio surface does not expose Codex, handoff directories,
request JSON, local absolute paths, provider raw responses, secrets, signed
URLs, or media bytes in API payloads.

## Runtime Contract

- Provider id in example config: `codex_image`
- Provider adapter: `provider="codex_handoff"`, `capability="image"`,
  `execution_mode="async"`.
- Gate: `AFS_ALLOW_REMOTE_IMAGE=true`.
- Job package root per Runtime run:

```text
<runtime-root>/runs/<project_id>/<job_id>/codex_image_job/
  pending/<worker_job_id>/request.json
  running/<worker_job_id>/
  completed/<worker_job_id>/result.json
  failed/<worker_job_id>/result.json
  _logs/events.jsonl
```

The package stores relative reference paths only. Generated candidates are
copied to:

```text
<run-dir>/image_candidates/candidate_001.png
```

Runtime poll route:

```text
POST /projects/{project_id}/keyframe-generations/{job_id}/poll
```

## Worker Operation

Development/fake executor:

```powershell
.\.venv\Scripts\python.exe tools\codex_image_worker.py --runtime-root <runtime-root> --executor fake --once
```

Production executor shape on the server:

```bash
python tools/codex_image_worker.py --runtime-root /var/lib/afs-runtime --executor codex
```

`CodexExecImageExecutor` invokes:

```text
codex exec --ask-for-approval never --sandbox workspace-write --skip-git-repo-check --cd <job-dir> ...
```

The full generation prompt is stored in `worker_prompt.md` inside the runtime
job directory, not placed on the process command line. Worker result summaries
are sanitized; raw provider output is not stored.

## Boundaries

- No secrets or provider credentials are committed.
- No provider raw response, Authorization header, cookie, signed URL, or media
  bytes are returned by the API.
- This is Runtime/provider-smoke readiness, not human acceptance, business
  validation, or durable memory promotion.
- The fake executor proves the file contract. A separate server smoke is still
  required to prove the installed `codex exec` image path can create a real
  `candidate_001.png`.

## Verification

Focused verification during implementation:

```text
pytest tests/test_codex_image_handoff.py -q
pytest tests/test_provider_adapter_registry.py -q
pytest tests/test_api_runtime_keyframe_reference_assets.py -q
pytest tests/test_web_studio_static.py -q
node --check apps/studio/src/runtime-client.js
node --check apps/studio/src/node-actions.js
```
