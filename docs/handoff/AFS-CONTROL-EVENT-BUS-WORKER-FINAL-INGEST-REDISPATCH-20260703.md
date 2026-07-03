# AFS Control Event Bus Worker-Final Ingest Redispatch - 2026-07-03

## Bottom-Up Feedback

- `bottom_up_feedback_id`: `BU-AFS-V02-SPEC-P1-CONTROL-EVENT-BUS-WORKER-FINAL-INGEST-REDISPATCH-20260703-001`
- `top_down_dispatch_id`: `TD-AFS-V02-SPEC-P1-CONTROL-EVENT-BUS-WORKER-FINAL-INGEST-REDISPATCH-20260703-001`
- `lane`: `SPEC-P1-CONTROL-EVENT-BUS-WORKER-FINAL-INGEST-REDISPATCH`
- `source_thread`: `019f25c8-37c9-7e30-8c57-279e40a3a1fc`
- `route_basis`: `readback_accepted_reaffirm_parallel_architecture_redispatch`
- `superseded_old_pendingWorktreeId`: `remote-ssh-discovered:afs-bwg-ops:c1ce9c63-b0ec-4a5a-ad13-7a0309dfde2c`
- `stale_after`: `2026-07-03T22:35:00+08:00`
- `close_state`: `control_event_bus_worker_final_ingest_redispatch_completed`
- `branch`: `codex/recovery-p1-control-event-bus-worker-final-ingest-durable-artifact-20260703`
- `commit`: created by durable artifact recovery closeout

## Scope

本 slice 只产出 control event-bus worker-final ingest 的 bounded spec/test
证据。它把 worker final delivery 记录为 repo-local control event register
事件，不实现 runtime worker、归档 daemon、provider 调用、source sync 或 DAG
scheduler。

覆盖内容：

- ingest contract：新增 `worker_final_ingested` control event 表面和
  `payload.worker_final_ingest` contract。
- event fields：校验 `event_id`、`top_down_dispatch_id`、
  `bottom_up_feedback_id` 与 payload canonical fields 一致。
- worker-final direct-read recovery sources：限定为
  `direct_thread_delivery`、`local_final_only`、`legacy_bridge`、
  `pendingWorktreeId`、`worker_final_read`。
- idempotency：相同 TD/BU/event id 的完全重复 worker final 会被 dedupe；
  同一 TD/BU 的冲突 worker final 会 fail closed。
- ACK/no-ACK：`ack_state=no_ack` 保留，`ack_delivery_confirmed=false` 时不能
  允许 archive execution。
- `local_final_only`：作为恢复来源之一显式保留，表示 worker final 可从本地
  final text 恢复，但不等于远端 ACK。
- materialization failure：缺少 `payload.worker_final_ingest` contract object
  时 materialization fail closed。
- safe evidence classification：fixture materialization 只接受已分类的
  `dispatcher_instruction` 和 `repo_fixture` evidence source。

旧 pendingWorktreeId 仅作为 reconciliation evidence 记录在 fixture 中；本轮没有
使用、修复、同步、归档或依赖该旧 remote pending worktree。

## Changed Files

- `agentflow/algorithms/control_event_register/__init__.py`
- `agentflow/algorithms/control_event_register/_constants.py`
- `agentflow/algorithms/control_event_register/_validation.py`
- `agentflow/algorithms/control_event_register/_worker_final.py`
- `agentflow/contracts/examples.py`
- `docs/architecture/AFS_CONTROL_EVENT_REGISTER_CONTRACT.md`
- `examples/agentflow/control_events_worker_final_ingest.example.jsonl`
- `examples/agentflow/contract_registry.example.json`
- `tests/test_control_event_register.py`
- `tests/test_contract_registry_examples.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-CONTROL-EVENT-BUS-WORKER-FINAL-INGEST-REDISPATCH-20260703.md`

## Durable Artifact Recovery Addendum

- `bottom_up_feedback_id`:
  `BU-AFS-V02-RECOVERY-P1-CONTROL-EVENT-BUS-WORKER-FINAL-INGEST-DURABLE-ARTIFACT-20260703-001`
- `top_down_dispatch_id`:
  `TD-AFS-V02-RECOVERY-P1-CONTROL-EVENT-BUS-WORKER-FINAL-INGEST-DURABLE-ARTIFACT-20260703-001`
- `lane`: `RECOVERY-P1-CONTROL-EVENT-BUS-WORKER-FINAL-INGEST-DURABLE-ARTIFACT`
- `source_thread`: `019f25c8-37c9-7e30-8c57-279e40a3a1fc`
- `route_basis`:
  `accept_event_bus_eval_blocker_authorize_durable_artifact_recovery`
- `source_dirty_worktree`:
  `/home/afs-ops/.codex/worktrees/f109/AgentFlowStudio`
- `recovery_branch`:
  `codex/recovery-p1-control-event-bus-worker-final-ingest-durable-artifact-20260703`
- `close_state`:
  `control_event_bus_worker_final_ingest_durable_artifact_recovered`
- `post_recovery_evaluator_required`: `true`
- `evaluator_pass_claim`: `not_claimed`
- `integration_claim`: `not_claimed`

This recovery converted the previously uncommitted worker-final ingest slice
into a durable local branch and commit. It did not merge to `master`, push,
fetch, pull, source-sync, deploy, restart, archive a thread, open a provider
gate, or mutate Runtime Service, Studio, OpenAPI, DOC2, COS, or CompanyOS
surfaces. A fresh evaluator must review the durable branch before any
integration decision.

## Artifact

- `artifact_id`: `spec-control-event-bus-worker-final-ingest-redispatch-20260703`
- `artifact_role`: `spec_test_slice`
- `artifact_kind`: `git_branch_with_repo_files`
- `uri`: `git:codex/recovery-p1-control-event-bus-worker-final-ingest-durable-artifact-20260703`
- `durability_state`: `local_branch_committed_by_recovery`
- `commit`: reported in recovery closeout BU
- `does_not_store_secrets`: `true`
- `does_not_store_private_asset_bytes`: `true`

## Version Fields

- `v0.6`: worker-final ingest event surface.
- `v0.6.1`: canonical TD/BU/event id validation.
- `v0.6.2`: recovery source enumeration for direct-thread, local-final,
  legacy bridge, pendingWorktreeId, and explicit worker-final read paths.
- `v0.6.3`: exact-duplicate idempotency and conflicting TD/BU duplicate
  rejection.
- `v0.6.4`: no-ACK preservation and archive-after-ACK ordering.
- `v0.6.5`: materialization fail-closed behavior for missing worker-final
  payload contract.
- `v0.6.6`: safe evidence classification for redispatch worker-final ingest.

## Archive Policy

- `policy`: `agent_created_archive_when_useless`
- `owner_manual_archive_excluded`: `no`
- `archive_after_ack_delivery_confirmed`: `true`
- `archive_execution_allowed`: `false` while `ack_delivery_confirmed=false`
- `archive_execution`: not implemented and not executed
- `archive_policy`: evaluated before archive execution
- `archive_after_ack_delivery_confirmed=true`
- `owner_manual_archive_excluded=no`

## Validation

Passed in this worktree:

```text
python3 -m py_compile agentflow/algorithms/control_event_register/__init__.py agentflow/algorithms/control_event_register/_constants.py agentflow/algorithms/control_event_register/_helpers.py agentflow/algorithms/control_event_register/_io.py agentflow/algorithms/control_event_register/_validation.py agentflow/algorithms/control_event_register/_worker_final.py tests/test_control_event_register.py tests/test_contract_registry_examples.py
```

```text
python3 - <<'PY'
# worker_final_ingest_no_pytest_assertions:
# fixture load, materialization, recovery sources, exact duplicate dedupe,
# conflicting TD/BU rejection, missing payload materialization failure,
# safe evidence classification, and archive-before-ACK rejection
PY
# worker_final_ingest_no_pytest_assertions: passed
```

```text
python3 - <<'PY'
# worker_final_ingest_contract_example_load:
# AGENTFLOW_EXAMPLE_PATHS contains and loads the JSONL fixture
PY
# worker_final_ingest_contract_example_load: passed
```

```text
git diff --check
# passed
```

Blocked:

```text
python3 -m pytest tests/test_control_event_register.py tests/test_contract_registry_examples.py -q
# /usr/bin/python3: No module named pytest
```

```text
python3 -m apps.cli.main --help
# ModuleNotFoundError: No module named 'typer'

python3 -m apps.cli.main version
# ModuleNotFoundError: No module named 'typer'
```

```text
command -v python
# no output, exit 1

command -v pytest
# no output, exit 1
```

## Non-Claims

- No archive daemon implementation.
- No destructive migration or destructive archive daemon.
- No full historical replay.
- No source sync, fetch, pull, push, or merge.
- No Runtime Service, Studio, OpenAPI, DOC2, COS, CompanyOS, provider, server,
  deploy, restart, or REL1B mutation.
- No provider gate opened and no provider call.
- No generated-media QA.
- No readiness, human acceptance, business validation, public claim, or legal
  claim.
- No CompanyOS/COS public projection or active-rule promotion.
- No durable-memory promotion.
- No self-archive.
- No use, repair, sync, or archive of the superseded old pendingWorktreeId.

## Residual Risks

- This is bounded repo-local spec/test evidence, not a live event-bus worker.
- The durable artifact still requires a fresh evaluator pass before integration
  or any merge decision.
- Focused pytest remains unavailable in this shell because `pytest` is not
  installed for `/usr/bin/python3`.
- CLI help/version checks remain unavailable because `typer` is not installed
  for `/usr/bin/python3`; `python` and `pytest` executables are also absent.

## Post-Closeout Next Action

`post_closeout_next_action`: evaluator should review the redispatch
worker-final ingest contract and decide whether the next bounded slice should
add a scheduler-facing read model or keep this adapter-only as control evidence.
