# AFS Single-Episode Loop Program

Status: active internal program, Phase 1 contract freeze. Human acceptance,
business validation, generated-media quality, and public release remain open.

## Goal Contract

Primary users are small manhua-drama production teams, with a compatible path
for individual creators. The first value target is character and scene
continuity plus lower storyboard-review rework.

The deliverable is one real, recoverable, creator-controlled episode loop:

```text
create project or import script
-> establish character and scene facts
-> break down episode, scenes, and shots
-> review and lock storyboard
-> generate asset candidates
-> check continuity
-> revise locally and compare versions
-> lock delivery version
-> create playable preview and export
```

The product structure remains a testable hypothesis. Guided, storyboard-first,
and hybrid prototypes must run the same Rainlight task protocol before the
production frontend structure is selected.

## Stable boundaries

- Project data is private and excluded from training by default.
- Feedback is not durable memory or training consent.
- AOS remains general; AFS is the vertical content-production product.
- Digital crew actions must change or inspect explicit product facts and expose
  creator decisions, not simulate value through chat volume.
- Full localization, skill marketplace, industry protocol, open-source business
  model, and large-scale training are not this Program's goals.
- Provider smoke, content quality, human acceptance, and business validation
  remain separate evidence layers.

## Runtime Surface Vector at Phase 1 entry

- Program base: `d0efbb451bd2172a9b1d565d605bfd8c1b38cb5b`.
- Production `/opt` was deployed and freshly verified at that exact SHA before
  Phase 1 began.
- `/home`, `/test`, and the unmanaged `8791` process are excluded from Program
  writes pending an exact cleanup decision.
- Provider calls are closed for Phase 1. Research and contract work do not
  authorize media generation or uploads.
- Production release remains a single serial Release Lane from a merged exact
  SHA.

## Requirement Closure Map

| Requirement | Target fact or surface | Verification route | Current state |
|---|---|---|---|
| One product fact chain | Episode production aggregate | schema tests + independent contract evaluator | contract candidate written |
| Private and no-training defaults | project data policy | default/negative tests | contract candidate written |
| Exact tenant/project scope | every fact and consent record | cross-project negative tests | contract candidate written |
| Recoverable mutation | aggregate version + idempotency key | persistence/restart tests | contract only; Runtime open |
| Continuity impact and rollback | continuity versions + exact shot refs | affected-shot E2E | contract only; implementation open |
| Candidate-to-delivery trace | candidate, selection, review, delivery refs | locked-delivery negative tests + E2E | contract candidate written |
| Creator-facing structure | three isolated prototypes | same-task protocol + independent evaluator | pending Phase 2 |
| Generic single-episode loop | Runtime/API/Studio/Review/Delivery | representative 8-15 shot E2E | pending Phase 3 |
| Identity and recovery | auth, persistence, queue, restart | negative isolation + restart/relogin | partial legacy evidence; integrated proof open |
| Content and commercial value | generated output and team use | human evaluation and owner decision | not claimed |

## Integration Queue

1. Freeze and independently evaluate the shared domain contract.
2. Commit the contract as the base for all next lanes.
3. Build guided, storyboard-first, and hybrid prototypes in isolated worktrees
   using one fixture, event logger, and evaluation protocol.
4. Prepare Runtime/persistence tests that do not depend on the winning visual
   structure.
5. Select a frontend structure only from evaluator evidence or return an exact
   decision needed.
6. Integrate bounded vertical slices, invalidating evaluator results whenever
   the final diff changes.
7. Run final E2E, cross-project isolation, recovery, CI, merge, and serial
   release verification.

## Research conclusion

The traceable findings and current-capability gaps are maintained in the
[Phase 1 evidence matrix](research/AFS_PHASE1_EVIDENCE_MATRIX.md). The three
prototype structures use the same
[Phase 2 evaluation protocol](AFS_EPISODE_LOOP_PHASE2_EVALUATION_PROTOCOL.md).
AFS should not differentiate by canvas presence or agent count. The open
product opportunity is one visible chain from object change to affected shots,
creator scope decision, recoverable version update, review evidence, and
delivery traceability.
