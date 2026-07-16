from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from agentflow.harness.json_io import exclusive_file_lock
from agentflow_studio.production_control.contract import (
    ActorIdentity,
    AgentAssignment,
    ArtifactCandidateRegistration,
    ArtifactWriteback,
    BudgetAuthorization,
    BudgetEnvelope,
    CommandEnvelope,
    CostEstimate,
    EpisodeArtifactAdapterRequest,
    ExactObjectRef,
    ImpactAssessment,
    Mission,
    MissionRevision,
    MoneyRange,
    PlanApprovalDecision,
    PlanRevision,
    PlanTask,
    PlanTaskSpec,
    ProductionPlan,
    ProductionRun,
    ProjectScope,
    ReferenceConstraint,
    RevisionIdentity,
    RunAttempt,
    SelectiveRevisionRequest,
)
from agentflow_studio.production_control.harness import (
    AuthorizationError,
    IdempotencyConflictError,
    LedgerIntegrityError,
    ProductionControlError,
    ProductionControlHarness,
    StateConflictError,
    VersionConflictError,
    digest,
    exact_ref,
)
from apps.api.runtime_episode_domain_contract import (
    AssetCandidateVersion,
    EntityVersionRef,
    ProductionControlProvenance,
    ProductionProjectAggregate,
    SafeArtifactRef,
    TenantScope,
)
from apps.api.runtime_episode_domain_store import (
    AggregateNotFoundError,
    EpisodeDomainAggregateStore,
    EpisodeDomainStoreError,
)
from apps.api.runtime_store import RuntimeStore, safe_id


CONTROL_PLAN_SCHEMA_VERSION = "afs.creator-production-control-plan.v0.1"
_DEFAULT_STAMP = "2026-07-16T00:00:00+00:00"
_CAPABILITIES = {
    "mission.write",
    "plan.write",
    "plan.approve",
    "run.execute",
    "run.control",
    "budget.record",
    "provider.evaluate",
    "decision.write",
    "artifact.write",
    "revision.write",
}


class CreatorProductionControlError(RuntimeError):
    pass


def prepare_creator_preview_control_plan(
    store: RuntimeStore,
    *,
    scope: TenantScope,
) -> dict[str, Any]:
    project_scope, actor = _control_identity(scope)
    with _locked_harness(store, project_scope, actor) as harness:
        return {
            "schema_version": CONTROL_PLAN_SCHEMA_VERSION,
            "start_version": harness.projection.version,
            "needs_mission": _latest_model(harness, "mission_revision", MissionRevision) is None,
            "needs_plan": _latest_model(harness, "plan_revision", PlanRevision) is None,
            "needs_approval": not _records(harness, "plan_task"),
        }


def record_creator_preview_control_writeback(
    store: RuntimeStore,
    *,
    scope: TenantScope,
    control_plan: dict[str, Any],
    idempotency_key: str,
    target_ref: EntityVersionRef,
    protected_refs: tuple[EntityVersionRef, ...],
    artifact_id: str,
    artifact_digest: str,
    candidate_ref: EntityVersionRef,
    created_at: str,
) -> dict[str, Any]:
    project_scope, actor = _control_identity(scope)
    token = _command_token(idempotency_key)
    stamp = _stamp(created_at)
    with _locked_harness(store, project_scope, actor) as harness:
        _validate_control_plan(control_plan)
        expected = int(control_plan["start_version"])
        receipts: list[dict[str, Any]] = []

        if control_plan.get("needs_mission") is True:
            receipt = harness.execute(
                _command(
                    harness,
                    actor,
                    "mission.record",
                    _mission_payload(project_scope, stamp),
                    f"{idempotency_key}-control-mission",
                    expected_version=expected,
                )
            )
            receipts.append(receipt.model_dump(mode="json"))
            expected += 1
        elif _latest_model(harness, "mission_revision", MissionRevision) is None:
            raise StateConflictError("production control mission is missing")

        if control_plan.get("needs_plan") is True:
            mission_revision = _latest_model(harness, "mission_revision", MissionRevision)
            if mission_revision is None:
                raise StateConflictError("production control mission is missing")
            payload = _plan_payload(project_scope, mission_revision, stamp)
            receipt = harness.execute(
                _command(
                    harness,
                    actor,
                    "plan.propose",
                    payload,
                    f"{idempotency_key}-control-plan",
                    expected_version=expected,
                    refs=(exact_ref("mission_revision", mission_revision),),
                )
            )
            receipts.append(receipt.model_dump(mode="json"))
            expected += 1
        elif _latest_model(harness, "plan_revision", PlanRevision) is None:
            raise StateConflictError("production control plan is missing")

        if control_plan.get("needs_approval") is True:
            plan_revision = _latest_model(harness, "plan_revision", PlanRevision)
            budget = _latest_model(harness, "budget_envelope", BudgetEnvelope)
            if plan_revision is None or budget is None:
                raise StateConflictError("production control plan cannot be approved")
            payload = _approval_payload(project_scope, plan_revision, budget, stamp)
            receipt = harness.execute(
                _command(
                    harness,
                    actor,
                    "plan.approve",
                    payload,
                    f"{idempotency_key}-control-approve",
                    expected_version=expected,
                    refs=(exact_ref("plan_revision", plan_revision),),
                    budget_authorization=BudgetAuthorization(
                        budget_envelope_ref=exact_ref("budget_envelope", budget),
                        admitted_amount=budget.max_budget,
                        currency=budget.estimated.currency,
                        authorization_ref="budget-provider-closed",
                    ),
                )
            )
            receipts.append(receipt.model_dump(mode="json"))
            expected += 1
        elif not _records(harness, "plan_task"):
            raise StateConflictError("production control tasks are missing")

        task = _task_by_id(harness, "task-002")
        task_ref = exact_ref("plan_task", task)
        run, assignment, attempt = _preview_run_bundle(project_scope, task_ref, token, stamp)
        run_ref = exact_ref("production_run", run)
        attempt_ref = exact_ref("run_attempt", attempt)
        if not harness.projection.has(run_ref):
            receipt = harness.execute(
                _command(
                    harness,
                    actor,
                    "run.start",
                    {
                        "assignment": assignment.model_dump(mode="json"),
                        "run": run.model_dump(mode="json"),
                        "attempt": attempt.model_dump(mode="json"),
                    },
                    f"{idempotency_key}-control-run-start",
                    expected_version=expected,
                    refs=(task_ref,),
                )
            )
            receipts.append(receipt.model_dump(mode="json"))
            expected += 1

        adapter = EpisodeArtifactAdapterRequest(
            mode="asset_candidate",
            predecessor_ref=_exact_ref_from_entity(project_scope, target_ref),
            successor_ref=_exact_ref_from_entity(project_scope, candidate_ref),
            protected_exact_refs=tuple(
                _exact_ref_from_entity(project_scope, ref) for ref in protected_refs
            ),
            existing_typed_operation="asset_candidate.create_version",
        )
        registration = ArtifactCandidateRegistration(
            identity=_identity(
                project_scope,
                f"registration-preview-{token}",
                created_at=stamp,
            ),
            plan_task_ref=task_ref,
            run_ref=run_ref,
            attempt_ref=attempt_ref,
            artifact_id=artifact_id,
            artifact_digest=artifact_digest,
            adapter_request=adapter,
        )
        writeback = ArtifactWriteback(
            identity=_identity(project_scope, f"writeback-preview-{token}", created_at=stamp),
            candidate_registration_ref=exact_ref(
                "artifact_candidate_registration",
                registration,
            ),
            plan_task_ref=task_ref,
            run_ref=run_ref,
            attempt_ref=attempt_ref,
            artifact_id=artifact_id,
            artifact_digest=artifact_digest,
            adapter_request=adapter,
        )
        revision_request = SelectiveRevisionRequest(
            identity=_identity(
                project_scope,
                f"revision-request-preview-{token}",
                created_at=stamp,
            ),
            target_exact_ref=adapter.predecessor_ref,
            protected_exact_refs=adapter.protected_exact_refs,
            requested_changes=("登记确定性制作预览候选，等待创作者审核。",),
            source_writeback_ref=exact_ref("artifact_writeback", writeback),
        )
        impact = ImpactAssessment(
            identity=_identity(project_scope, f"impact-preview-{token}", created_at=stamp),
            revision_request_ref=exact_ref("selective_revision_request", revision_request),
            affected_exact_refs=(adapter.predecessor_ref,),
            preserved_exact_refs=adapter.protected_exact_refs,
            assessment_digest=digest(
                {
                    "affected": adapter.predecessor_ref.model_dump(mode="json"),
                    "preserved": [
                        item.model_dump(mode="json")
                        for item in adapter.protected_exact_refs
                    ],
                }
            ),
        )
        commands = (
            (
                "artifact.register",
                {"registration": registration.model_dump(mode="json")},
                "artifact-register",
                (task_ref, run_ref, attempt_ref, adapter.predecessor_ref, *adapter.protected_exact_refs),
            ),
            (
                "artifact.writeback",
                {"writeback": writeback.model_dump(mode="json")},
                "artifact-writeback",
                (
                    exact_ref("artifact_candidate_registration", registration),
                    adapter.predecessor_ref,
                    *adapter.protected_exact_refs,
                ),
            ),
            (
                "selective_revision.request",
                {"revision_request": revision_request.model_dump(mode="json")},
                "revision-request",
                (
                    exact_ref("artifact_writeback", writeback),
                    adapter.predecessor_ref,
                    *adapter.protected_exact_refs,
                ),
            ),
            (
                "impact.assess",
                {"impact_assessment": impact.model_dump(mode="json")},
                "impact",
                (
                    exact_ref("selective_revision_request", revision_request),
                    *adapter.protected_exact_refs,
                ),
            ),
        )
        for command_type, payload, suffix, refs in commands:
            receipt = harness.execute(
                _command(
                    harness,
                    actor,
                    command_type,
                    payload,
                    f"{idempotency_key}-control-{suffix}",
                    expected_version=expected,
                    refs=refs,
                )
            )
            receipts.append(receipt.model_dump(mode="json"))
            expected += 1

        return {
            "schema_version": "afs.creator-production-control-writeback.v0.1",
            "task": {
                "ref": _control_ref(task_ref),
                "state": "queued",
                "title": "生成制作预览候选",
            },
            "run": {"ref": _control_ref(run_ref), "state": "running"},
            "attempt": {
                "ref": _control_ref(attempt_ref),
                "state": "running",
                "attempt_number": 1,
            },
            "registration_ref": _control_ref(
                exact_ref("artifact_candidate_registration", registration)
            ),
            "writeback_ref": _control_ref(exact_ref("artifact_writeback", writeback)),
            "receipts": receipts,
            "control_receipt": receipts[-1] if receipts else None,
            "next_expected_version": expected,
            "projection_digest": harness.projection.state_digest,
            "event_count": len(harness.events),
            "provider_dispatch_count": harness.provider_dispatch_count,
        }


def apply_creator_preview_episode_candidate(
    store: RuntimeStore,
    *,
    scope: TenantScope,
    control: dict[str, Any],
    idempotency_key: str,
    created_at: str,
) -> dict[str, Any]:
    project_scope, actor = _control_identity(scope)
    with _locked_harness(store, project_scope, actor) as harness:
        writeback_ref = _exact_ref_from_control(project_scope, control["writeback_ref"])
        writeback = _writeback_by_ref(harness, writeback_ref)
    adapter = writeback.adapter_request
    if adapter.mode != "asset_candidate" or adapter.predecessor_ref is None:
        raise StateConflictError("creator preview writeback must target an asset candidate")

    aggregate_store = EpisodeDomainAggregateStore(store.root)
    aggregate = aggregate_store.load(org_id=scope.org_id, project_id=scope.project_id)
    if aggregate.scope != scope:
        raise StateConflictError("episode scope does not match production control scope")

    target_ref = _entity_ref(adapter.predecessor_ref)
    protected_refs = tuple(_entity_ref(ref) for ref in adapter.protected_exact_refs)
    candidate_ref = _entity_ref(adapter.successor_ref)
    _require_latest_refs(aggregate, (target_ref, *protected_refs))
    latest = _latest_candidate_by_entity(aggregate, candidate_ref.entity_id)
    if latest is not None and latest.control_provenance is not None:
        if latest.control_provenance.writeback_ref != _control_ref(writeback_ref):
            raise StateConflictError("episode candidate belongs to a different writeback")
        return {
            "status": "already_applied",
            "aggregate_version": aggregate.aggregate_version,
            "candidate_ref": latest.as_ref().model_dump(mode="json"),
            "episode_event_id": None,
            "aggregate_sha256": "",
        }
    if latest is not None:
        raise StateConflictError("episode candidate identity is already used")

    stamp = _next_stamp(aggregate.evaluated_at, _stamp(created_at))
    candidate = AssetCandidateVersion(
        entity_id=candidate_ref.entity_id,
        version_id=candidate_ref.version_id,
        revision=1,
        parent_version_id=None,
        lifecycle_state="candidate",
        review_state="needs_review",
        content_digest=digest(
            {
                "operation": "creator_production_preview_candidate",
                "target_ref": target_ref.model_dump(mode="json"),
                "writeback_ref": writeback_ref.model_dump(mode="json"),
                "artifact_digest": writeback.artifact_digest,
            }
        ),
        scope=scope,
        created_at=stamp,
        target_ref=target_ref,
        artifact_ref=SafeArtifactRef(
            artifact_id=writeback.artifact_id,
            artifact_type="production_preview_manifest",
            content_digest=writeback.artifact_digest,
        ),
        job_id=f"job-{writeback.run_ref.object_id}",
        job_state="succeeded",
        control_provenance=ProductionControlProvenance(
            plan_task_ref=_control_ref(writeback.plan_task_ref),
            run_ref=_control_ref(writeback.run_ref),
            attempt_ref=_control_ref(writeback.attempt_ref),
            writeback_ref=_control_ref(writeback_ref),
            affected_refs=(target_ref,),
            protected_refs=protected_refs,
        ),
    )
    payload = aggregate.model_dump(mode="python")
    payload.update(
        {
            "aggregate_version": aggregate.aggregate_version + 1,
            "evaluated_at": stamp,
            "asset_candidates": (*aggregate.asset_candidates, candidate),
        }
    )
    updated = ProductionProjectAggregate.model_validate(payload)
    result = aggregate_store.save(
        updated,
        expected_aggregate_version=aggregate.aggregate_version,
        idempotency_key=f"{idempotency_key}-episode-candidate",
        payload_digest=digest(
            {
                "operation": "creator_production_preview_candidate",
                "candidate": candidate.model_dump(mode="json"),
                "expected_aggregate_version": aggregate.aggregate_version,
            }
        ),
    )
    return {
        "status": "applied" if not result.replayed else "replayed",
        "aggregate_version": result.aggregate.aggregate_version,
        "candidate_ref": candidate.as_ref().model_dump(mode="json"),
        "episode_event_id": result.ledger_event_id,
        "aggregate_sha256": result.aggregate_sha256,
    }


def confirm_creator_preview_control_run(
    store: RuntimeStore,
    *,
    scope: TenantScope,
    control: dict[str, Any],
    idempotency_key: str,
) -> dict[str, Any]:
    project_scope, actor = _control_identity(scope)
    with _locked_harness(store, project_scope, actor) as harness:
        run_ref = _exact_ref_from_control(project_scope, control["run"]["ref"])
        receipt = harness.execute(
            _command(
                harness,
                actor,
                "run.transition",
                {
                    "run_ref": run_ref.model_dump(mode="json"),
                    "target_state": "completed",
                },
                f"{idempotency_key}-control-run-complete",
                expected_version=int(control["next_expected_version"]),
                refs=(run_ref,),
            )
        )
        return {
            "receipt": receipt.model_dump(mode="json"),
            "projection_digest": harness.projection.state_digest,
            "event_count": len(harness.events),
            "provider_dispatch_count": harness.provider_dispatch_count,
        }


def read_creator_preview_control_projection(
    store: RuntimeStore,
    *,
    scope: TenantScope,
) -> dict[str, Any]:
    project_scope, actor = _control_identity(scope)
    with _locked_harness(store, project_scope, actor) as harness:
        return {
            "schema_version": "afs.creator-production-control-projection.v0.1",
            "version": harness.projection.version,
            "projection_digest": harness.projection.state_digest,
            "event_count": len(harness.events),
            "provider_dispatch_count": harness.provider_dispatch_count,
            "writeback_refs": sorted(
                f"{kind}:{object_id}:{revision_id}"
                for (kind, object_id, revision_id) in harness.projection.records
                if kind == "artifact_writeback"
            ),
        }


def _validate_control_plan(value: dict[str, Any]) -> None:
    if value.get("schema_version") != CONTROL_PLAN_SCHEMA_VERSION:
        raise StateConflictError("creator preview control plan schema is invalid")
    for key in ("start_version",):
        if not isinstance(value.get(key), int) or isinstance(value.get(key), bool):
            raise StateConflictError("creator preview control plan version is invalid")


@contextmanager
def _locked_harness(
    store: RuntimeStore,
    scope: ProjectScope,
    actor: ActorIdentity,
):
    path = _ledger_path(store, scope.project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with exclusive_file_lock(_lock_path(store, scope.project_id)):
            if path.is_file():
                harness = ProductionControlHarness.load(path, _grants(actor), {actor.actor_id: actor})
                if harness.scope != scope:
                    raise AuthorizationError("production-control ledger scope mismatch")
            else:
                harness = ProductionControlHarness(scope, _grants(actor), {actor.actor_id: actor}, file_path=path)
            yield harness
    except (
        AuthorizationError,
        IdempotencyConflictError,
        LedgerIntegrityError,
        ProductionControlError,
        StateConflictError,
        VersionConflictError,
        EpisodeDomainStoreError,
        ValueError,
    ) as exc:
        raise CreatorProductionControlError(str(exc) or type(exc).__name__) from exc


def _control_identity(scope: TenantScope) -> tuple[ProjectScope, ActorIdentity]:
    project_scope = ProjectScope(org_id=scope.org_id, project_id=scope.project_id)
    actor = ActorIdentity(
        actor_id=scope.actor_id,
        actor_type="human",
        authority_ref=f"runtime-membership-{scope.actor_id}",
    )
    return project_scope, actor


def _ledger_path(store: RuntimeStore, project_id: str) -> Path:
    return store.projects_dir / safe_id(project_id) / "production_control" / "ledger.json"


def _lock_path(store: RuntimeStore, project_id: str) -> Path:
    return store.projects_dir / safe_id(project_id) / "production_control" / "production_control.lock"


def _grants(actor: ActorIdentity) -> dict[str, set[str]]:
    return {actor.actor_id: set(_CAPABILITIES)}


def _identity(
    scope: ProjectScope,
    object_id: str,
    *,
    revision: int = 1,
    parent_revision_id: str | None = None,
    created_at: str,
) -> RevisionIdentity:
    return RevisionIdentity(
        scope=scope,
        object_id=object_id,
        revision_id=f"{object_id}-v{revision}",
        revision=revision,
        parent_revision_id=parent_revision_id,
        created_at=created_at,
    )


def _mission_payload(scope: ProjectScope, stamp: str) -> dict[str, Any]:
    constraint = ReferenceConstraint(
        identity=_identity(scope, "constraint-provider-closed", created_at=stamp),
        constraint_type="delivery",
        rule="本轮制作预览只登记确定性候选，外部生成调用保持为零。",
    )
    revision = MissionRevision(
        identity=_identity(scope, "mission-revision-main", created_at=stamp),
        objective="为创作者登记可恢复、可审核的制作预览候选。",
        reference_constraint_refs=(exact_ref("reference_constraint", constraint),),
    )
    mission = Mission(
        identity=_identity(scope, "mission-main", created_at=stamp),
        head_revision_ref=exact_ref("mission_revision", revision),
    )
    return {
        "mission": mission.model_dump(mode="json"),
        "mission_revision": revision.model_dump(mode="json"),
        "constraints": [constraint.model_dump(mode="json")],
    }


def _plan_payload(
    scope: ProjectScope,
    mission_revision: MissionRevision,
    stamp: str,
) -> dict[str, Any]:
    revision_ref = ExactObjectRef(
        scope=scope,
        object_type="plan_revision",
        object_id="plan-revision-main",
        revision_id="plan-revision-main-v1",
    )
    plan = ProductionPlan(
        identity=_identity(scope, "plan-main", created_at=stamp),
        mission_revision_ref=exact_ref("mission_revision", mission_revision),
        head_revision_ref=revision_ref,
    )
    budget = BudgetEnvelope(
        identity=_identity(scope, "budget-main", created_at=stamp),
        estimated=MoneyRange(
            currency="CNY",
            minimum=0,
            maximum=0,
            unit="deterministic-preview-writeback",
            assumption="Provider dispatch remains zero for this local preview registration.",
        ),
        max_budget=0,
    )
    estimate = CostEstimate(
        identity=_identity(scope, "estimate-main", created_at=stamp),
        plan_revision_ref=revision_ref,
        estimated=budget.estimated,
    )
    specs = (
        PlanTaskSpec(
            task_id="task-001",
            boundary="核对精确镜头、单集和受保护镜头版本。",
            capability="deterministic.preview",
        ),
        PlanTaskSpec(
            task_id="task-002",
            boundary="登记确定性制作预览候选并保留写回来源。",
            capability="deterministic.preview",
            dependency_task_ids=("task-001",),
        ),
        PlanTaskSpec(
            task_id="task-003",
            boundary="把候选交给创作者审核，不自动采用或锁定。",
            capability="deterministic.preview",
            dependency_task_ids=("task-002",),
        ),
    )
    revision = PlanRevision(
        identity=_identity(scope, "plan-revision-main", created_at=stamp),
        plan_ref=ExactObjectRef(
            scope=scope,
            object_type="production_plan",
            object_id="plan-main",
            revision_id="plan-main-v1",
        ),
        task_specs=specs,
        budget_envelope_ref=exact_ref("budget_envelope", budget),
        cost_estimate_refs=(exact_ref("cost_estimate", estimate),),
    )
    return {
        "plan": plan.model_dump(mode="json"),
        "plan_revision": revision.model_dump(mode="json"),
        "budget_envelope": budget.model_dump(mode="json"),
        "cost_estimates": [estimate.model_dump(mode="json")],
    }


def _approval_payload(
    scope: ProjectScope,
    plan_revision: PlanRevision,
    budget: BudgetEnvelope,
    stamp: str,
) -> dict[str, Any]:
    tasks = tuple(
        PlanTask(
            identity=_identity(scope, spec.task_id, created_at=stamp),
            plan_revision_ref=exact_ref("plan_revision", plan_revision),
            boundary=spec.boundary,
            capability=spec.capability,
            dependency_refs=tuple(
                ExactObjectRef(
                    scope=scope,
                    object_type="plan_task",
                    object_id=dep,
                    revision_id=f"{dep}-v1",
                )
                for dep in spec.dependency_task_ids
            ),
        )
        for spec in plan_revision.task_specs
    )
    decision = PlanApprovalDecision(
        identity=_identity(scope, "approval-main", created_at=stamp),
        plan_revision_ref=exact_ref("plan_revision", plan_revision),
        decision="approved",
        approved_task_refs=tuple(exact_ref("plan_task", task) for task in tasks),
        budget_envelope_ref=exact_ref("budget_envelope", budget),
    )
    return {
        "decision": decision.model_dump(mode="json"),
        "tasks": [task.model_dump(mode="json") for task in tasks],
    }


def _preview_run_bundle(
    scope: ProjectScope,
    task_ref: ExactObjectRef,
    token: str,
    stamp: str,
) -> tuple[ProductionRun, AgentAssignment, RunAttempt]:
    assignment = AgentAssignment(
        identity=_identity(scope, f"assignment-preview-{token}", created_at=stamp),
        task_ref=task_ref,
        agent_id="deterministic-preview-worker",
        capability="deterministic.preview",
    )
    run_ref = ExactObjectRef(
        scope=scope,
        object_type="production_run",
        object_id=f"run-preview-{token}",
        revision_id=f"run-preview-{token}-v1",
    )
    attempt = RunAttempt(
        identity=_identity(scope, f"attempt-preview-{token}-001", created_at=stamp),
        run_ref=run_ref,
        attempt_number=1,
    )
    run = ProductionRun(
        identity=_identity(scope, f"run-preview-{token}", created_at=stamp),
        task_ref=task_ref,
        assignment_ref=exact_ref("agent_assignment", assignment),
        execution_state="running",
        latest_attempt_ref=exact_ref("run_attempt", attempt),
    )
    return run, assignment, attempt


def _command(
    harness: ProductionControlHarness,
    actor: ActorIdentity,
    command_type: str,
    payload: dict[str, Any],
    key: str,
    *,
    expected_version: int,
    refs: tuple[ExactObjectRef, ...] = (),
    budget_authorization: BudgetAuthorization | None = None,
) -> CommandEnvelope:
    return CommandEnvelope(
        command_id=f"cmd-{key}",
        command_type=command_type,
        scope=harness.scope,
        actor=actor,
        expected_version=expected_version,
        idempotency_key=key,
        correlation_id=f"corr-{harness.scope.project_id}",
        causation_id=f"cmd-{key}",
        capability={
            "mission.record": "mission.write",
            "plan.propose": "plan.write",
            "plan.approve": "plan.approve",
            "run.start": "run.execute",
            "run.transition": "run.execute",
            "artifact.register": "artifact.write",
            "artifact.writeback": "artifact.write",
            "selective_revision.request": "revision.write",
            "impact.assess": "revision.write",
        }[command_type],
        exact_object_refs=refs,
        budget_authorization=budget_authorization,
        provider_authorization=None,
        payload=payload,
        payload_digest=digest(payload),
    )


def _records(harness: ProductionControlHarness, object_type: str) -> list[dict[str, Any]]:
    return sorted(
        [
            value
            for (kind, _, _), value in harness.projection.records.items()
            if kind == object_type
        ],
        key=lambda item: (item["identity"]["object_id"], item["identity"]["revision"]),
    )


def _latest_model(harness: ProductionControlHarness, object_type: str, model: type[Any]):
    rows = _records(harness, object_type)
    if not rows:
        return None
    return model.model_validate(
        sorted(rows, key=lambda item: (item["identity"]["revision"], item["identity"]["created_at"]))[-1]
    )


def _task_by_id(harness: ProductionControlHarness, task_id: str) -> PlanTask:
    matches = [
        PlanTask.model_validate(item)
        for item in _records(harness, "plan_task")
        if item["identity"]["object_id"] == task_id
    ]
    if not matches:
        raise StateConflictError("production control writeback task is missing")
    return matches[-1]


def _writeback_by_ref(
    harness: ProductionControlHarness,
    ref: ExactObjectRef,
) -> ArtifactWriteback:
    payload = harness.projection.get(ref)
    return ArtifactWriteback.model_validate(payload)


def _exact_ref_from_entity(scope: ProjectScope, ref: EntityVersionRef) -> ExactObjectRef:
    if ref.entity_type not in {"shot", "continuity_state", "asset_candidate"}:
        raise StateConflictError("episode reference cannot be used for production control writeback")
    return ExactObjectRef(
        scope=scope,
        object_type=ref.entity_type,
        object_id=ref.entity_id,
        revision_id=ref.version_id,
    )


def _exact_ref_from_control(scope: ProjectScope, ref: dict[str, str]) -> ExactObjectRef:
    return ExactObjectRef(
        scope=scope,
        object_type=ref["object_type"],  # type: ignore[arg-type]
        object_id=ref["object_id"],
        revision_id=ref["revision_id"],
    )


def _entity_ref(ref: ExactObjectRef) -> EntityVersionRef:
    if ref.object_type not in {"shot", "continuity_state", "asset_candidate"}:
        raise StateConflictError("control reference cannot be mapped to episode facts")
    return EntityVersionRef(
        entity_type=ref.object_type,  # type: ignore[arg-type]
        entity_id=ref.object_id,
        version_id=ref.revision_id,
    )


def _control_ref(ref: ExactObjectRef) -> dict[str, str]:
    return {
        "object_type": ref.object_type,
        "object_id": ref.object_id,
        "revision_id": ref.revision_id,
    }


def _latest_candidate_by_entity(
    aggregate: ProductionProjectAggregate,
    entity_id: str,
) -> AssetCandidateVersion | None:
    matches = [item for item in aggregate.asset_candidates if item.entity_id == entity_id]
    if not matches:
        return None
    return max(matches, key=lambda item: item.revision)


def _require_latest_refs(
    aggregate: ProductionProjectAggregate,
    refs: tuple[EntityVersionRef, ...],
) -> None:
    for ref in refs:
        if ref.entity_type == "shot":
            collection = aggregate.shots
        elif ref.entity_type == "continuity_state":
            collection = aggregate.continuity_states
        else:
            raise CreatorProductionControlError("writeback refs must target shots or continuity facts")
        matches = [item for item in collection if item.entity_id == ref.entity_id]
        if not matches:
            raise CreatorProductionControlError("writeback target ref does not resolve in episode facts")
        latest = max(matches, key=lambda item: item.revision)
        if latest.as_ref() != ref:
            raise CreatorProductionControlError("episode facts changed; reload before writing back")


def _command_token(idempotency_key: str) -> str:
    token = safe_id(idempotency_key)
    return token[:64] or "command"


def _stamp(value: str) -> str:
    text = str(value or _DEFAULT_STAMP).strip().replace("Z", "+00:00")
    datetime.fromisoformat(text or _DEFAULT_STAMP)
    return text or _DEFAULT_STAMP


def _next_stamp(first: str, second: str) -> str:
    first_value = datetime.fromisoformat(_stamp(first))
    second_value = datetime.fromisoformat(_stamp(second))
    value = first_value if first_value >= second_value else second_value
    if value <= first_value:
        value = first_value + timedelta(microseconds=1)
    return value.isoformat()


__all__ = (
    "CreatorProductionControlError",
    "apply_creator_preview_episode_candidate",
    "confirm_creator_preview_control_run",
    "prepare_creator_preview_control_plan",
    "read_creator_preview_control_projection",
    "record_creator_preview_control_writeback",
)
