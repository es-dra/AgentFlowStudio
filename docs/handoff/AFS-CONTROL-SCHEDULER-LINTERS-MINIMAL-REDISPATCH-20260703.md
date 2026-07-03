# AFS Control Scheduler Linters Minimal Redispatch - 2026-07-03

## Bottom-Up Feedback

- `bottom_up_feedback_id`: `BU-AFS-V02-IMP-P1-CONTROL-SCHEDULER-LINTERS-MINIMAL-REDISPATCH-20260703-001`
- `top_down_dispatch_id`: `TD-AFS-V02-IMP-P1-CONTROL-SCHEDULER-LINTERS-MINIMAL-REDISPATCH-20260703-001`
- `lane`: `IMP-P1-CONTROL-SCHEDULER-LINTERS-MINIMAL-REDISPATCH`
- `close_state`: `control_scheduler_linters_minimal_redispatch_completed`
- `branch`: `codex/control-scheduler-linters-minimal-redispatch-20260703`
- `source_thread_id`: `019f25c8-37c9-7e30-8c57-279e40a3a1fc`
- `route_basis`: `readback_accepted_reaffirm_parallel_architecture_redispatch`
- `superseded_pending_worktree_id`: `remote-ssh-discovered:afs-bwg-ops:0d897b85-b3f3-43c5-8fbf-f089e442c6fd`

## Durable Artifact Recovery Addendum

- `bottom_up_feedback_id`: `BU-AFS-V02-RECOVERY-P1-CONTROL-SCHEDULER-LINTERS-MINIMAL-DURABLE-ARTIFACT-20260703-001`
- `top_down_dispatch_id`: `TD-AFS-V02-RECOVERY-P1-CONTROL-SCHEDULER-LINTERS-MINIMAL-DURABLE-ARTIFACT-20260703-001`
- `lane`: `RECOVERY-P1-CONTROL-SCHEDULER-LINTERS-MINIMAL-DURABLE-ARTIFACT`
- `close_state`: `control_scheduler_linter_minimal_durable_artifact_recovered`
- `source_thread_id`: `019f25c8-37c9-7e30-8c57-279e40a3a1fc`
- `route_basis`: `accept_scheduler_linter_eval_blocker_authorize_durable_artifact_recovery`
- `prior_evaluator_blocker`: `BU-AFS-V02-EVAL-P1-CONTROL-SCHEDULER-LINTERS-MINIMAL-20260703-001`
- `prior_evaluator_thread`: `019f285a-77d3-7511-aa64-87efad0a294e`
- `durable_branch`: `codex/control-scheduler-linters-minimal-redispatch-20260703`
- `durable_commit`: pending until local recovery commit is created
- `stale_after`: `2026-07-03T23:40:00+08:00`
- `required_correction`: pseudo wakeup fields such as
  `current_codex_delegation_response` and inert `monitor_ref` are rejected
  unless paired with executable automation/thread wakeup evidence.

## Scope Implemented

- Added lint-only control scheduler checks in
  `agentflow.algorithms.control_event_register`.
- The linter consumes a scheduler/register-like mapping and returns findings;
  it does not write files, archive threads, create monitors, dispatch lanes,
  replay history, or call providers.
- Covered these minimal redispatch lint codes:
  - `completed_bu_not_processed`
  - `join_all_without_reason`
  - `single_active_lane_without_dependency_reason`
  - `lane_past_stale_after_without_recovery_outcome`
  - `post_closeout_next_action_without_real_wakeup_monitor`

## Changed Files

- `agentflow/algorithms/control_event_register/_scheduler_lints.py`
- `agentflow/algorithms/control_event_register/__init__.py`
- `tests/test_control_event_register.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-CONTROL-SCHEDULER-LINTERS-MINIMAL-REDISPATCH-20260703.md`

## Version Fields

- `v0.6`: minimal control scheduler lint codes for completed BU processing,
  join-all reason, single-active dependency reason, stale lane recovery outcome,
  and post-closeout wakeup/monitor mechanism.
- `v0.6.1`: lint-only/read-only boundary; no scheduler execution, no archive
  daemon, no destructive migration, and no full historical replay.
- `v0.6.2`: recovery correction for pseudo wakeup rejection; bare
  `monitor_ref` and `current_codex_delegation_response` are not treated as real
  monitor/wakeup evidence.

## Archive Policy

- `policy`: `agent_created_archive_when_useless`
- `owner_manual_archive_excluded`: `no`
- `archive_after_ack_delivery_confirmed`: `true`
- `evaluated_before_archive_execution`: `true`
- `archive_execution_allowed`: `false`
- `blocked_reason`: `ack_delivery_not_confirmed`
- This worker did not self-archive and did not create archive automation.

## Post-Closeout Next Action

```json
{
  "action": "deliver_bottom_up_feedback_to_source_thread_for_ack",
  "mechanism": "current_codex_delegation_response",
  "monitor_ref": "codex_thread:019f25c8-37c9-7e30-8c57-279e40a3a1fc",
  "required_next_state": "ack_delivery_confirmed_before_any_archive_execution",
  "worker_created_external_wakeup_or_monitor": false
}
```

If the control plane needs delayed follow-up after this handoff, it must attach
a real wakeup or monitor mechanism before relying on `post_closeout_next_action`.

The linter intentionally reports this object as
`post_closeout_next_action_without_real_wakeup_monitor`; it is a delivery
description, not executable automation/thread wakeup evidence.

## Validation

Passed:

```text
python3 -m py_compile agentflow/algorithms/control_event_register/__init__.py agentflow/algorithms/control_event_register/_scheduler_lints.py tests/test_control_event_register.py
```

```text
python3 - <<'PY'
# no-pytest assertion script covering clean state, all five requested linter
# codes, pseudo wakeup rejection, and read-only/no-mutation behavior
PY
# control_scheduler_linter_no_pytest_checks: passed
```

Blocked by local environment:

```text
python3 -m pytest tests/test_control_event_register.py -q
# /usr/bin/python3: No module named pytest
```

```text
python3 -m apps.cli.main --help
# ModuleNotFoundError: No module named 'typer'

python3 -m apps.cli.main version
# ModuleNotFoundError: No module named 'typer'
```

## Dirty Ownership Ledger

- Source dirty checkout already contained in-scope scheduler-linter changes in:
  - `agentflow/algorithms/control_event_register/_scheduler_lints.py`
  - `agentflow/algorithms/control_event_register/__init__.py`
  - `tests/test_control_event_register.py`
  - `DEVLOG.md`
  - `TASK_TRACKER.md`
  - `docs/handoff/INDEX.md`
  - `docs/handoff/AFS-CONTROL-SCHEDULER-LINTERS-MINIMAL-REDISPATCH-20260703.md`
- Source dirty checkout also contained unrelated dirty that was preserved and
  excluded from the recovery commit:
  - `docs/openapi/afs-runtime-service.openapi.json`
  - `docs/demo/`
  - `docs/maintenance/AFS-DEMO-DOCS-CHINESE-20260629.md`
- No unrelated OpenAPI snapshot or demo-doc paths were staged, edited, moved,
  deleted, or included in the durable scheduler-linter artifact.

## Non-Claims

- No archive daemon or thread archive automation.
- No destructive migration, cleanup, historical replay, source sync, fetch,
  pull, push, merge, deploy, restart, runtime/server action, REL1B, OpenAPI,
  DOC2, COS, or CompanyOS mutation.
- No provider gate was opened and no provider call occurred.
- No Runtime Service or Studio mutation.
- No generated-media QA, readiness claim, human acceptance, business
  validation, public/legal claim, durable-memory promotion, or COS active-rule
  promotion.
