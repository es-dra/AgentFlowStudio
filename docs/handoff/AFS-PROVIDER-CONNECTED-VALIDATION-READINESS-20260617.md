# AFS Provider-Connected Validation Readiness

Date: 2026-06-17

Branch: `codex/afs-algorithm-library-hard-refactor`

中文摘要：本记录是下一轮真实 provider 链路验证的无成本启动检查。它确认
GFR provider 验证启动包存在、Runtime 能力面已包含必要动作、本机存在
provider config 来源，并且当前环境里 LLM / image gate 处于开启状态。这个
检查没有发起 provider call，没有读取或打印 provider config 真实路径，没有
输出 secret，也不构成人工验收或商业验证。

## Readiness Tool

Command:

```powershell
.\.venv\Scripts\python.exe tools\afs_provider_connected_validation_readiness.py
```

Current result:

```text
status: ready_for_provider_smoke
task_packet: present
runtime health: ready
required Runtime actions: present
provider config source: AFS_PROVIDER_CONFIG, present, path not disclosed
human approval required: true
current-session approval inferred from env: false
provider calls started: false
secrets printed: false
```

Current gate projection from the no-cost report:

| Capability | Gate | Current projection |
|---|---|---|
| LLM | `AFS_ALLOW_REMOTE_LLM` | enabled |
| image | `AFS_ALLOW_REMOTE_IMAGE` | enabled |
| video | `AFS_ALLOW_REMOTE_VIDEO` | closed |
| vision | `AFS_ALLOW_REMOTE_VISION` | closed |

## Recommended Live Smoke Scope

Minimum next live task, if explicitly approved:

1. Use only `AFS_ALLOW_REMOTE_LLM=true` and `AFS_ALLOW_REMOTE_IMAGE=true`.
2. Keep `AFS_ALLOW_REMOTE_VIDEO=false`.
3. Keep `AFS_ALLOW_REMOTE_VISION=false` unless running asset-card vision smoke.
4. Run one prompt optimization + image/keyframe smoke with `candidate_count=1`.
5. Record safe manifest and run trace.
6. Add human scoring separately.

Do not claim:

- human acceptance;
- business validation;
- durable memory promotion;
- video provider readiness;
- vision provider readiness.

## Verification Run This Session

```text
pytest tests/test_afs_provider_connected_validation_readiness.py -q -> 4 passed, 1 warning
pytest tests/test_algorithm_library_contracts.py tests/test_api_runtime_asset_card_drafts.py tests/test_provider_adapter_registry.py::test_provider_registry_supports_fake_vision_descriptor_and_gate tests/test_api_runtime_service.py::test_runtime_service_reports_health_and_capabilities_without_secrets tests/test_api_runtime_service.py::test_runtime_health_provider_gate_projection_is_isolated_and_secret_free -q -> 10 passed, 1 warning
focused algorithm/provider/static/context/retention suite -> 57 passed, 1 warning
full default pytest -> 433 passed, 527 deselected, 2 warnings
```

## Human Decision Required

Before live provider execution, confirm the exact scope:

```text
Authorize one live LLM + image/keyframe provider smoke with candidate_count=1.
Do not authorize video, ASR, vision, or external download.
```

If video should be included, authorize it separately and set the expected
artifact, duration, and cost boundary.
