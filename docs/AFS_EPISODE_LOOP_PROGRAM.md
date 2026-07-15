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

The production frontend structure is selected: Project/Episode shell,
storyboard-centered default workspace, and contextual inspector. Hybrid remains
the information-architecture base; Guided is only the next-action, recovery, and
natural-error mechanism. Mobile is a review, annotation, selection, and recovery
companion. Infinite canvas, a complete NLE, and global Agent chat are not default
entrypoints. This choice is no longer an open prototype vote.

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
| Creator-facing structure | Project/Episode shell + storyboard workspace + contextual inspector | authenticated local vertical-slice tests + independent browser evaluator | selected; productization evaluator pending |
| Generic single-episode loop | Runtime/API/Studio/Review/Delivery | representative 8-15 shot E2E | pending Phase 3 |
| Identity and recovery | auth, persistence, queue, restart | negative isolation + restart/relogin | partial legacy evidence; integrated proof open |
| Content and commercial value | generated output and team use | human evaluation and owner decision | not claimed |

## Integration Queue

1. Keep the frozen domain contract, command API, and creator-safe projection as
   the shared fact boundary.
2. Productize the selected Project/Episode + storyboard + inspector direction
   against authenticated GET, typed commands, and Studio-state recovery.
3. Run fresh desktop/mobile browser QA and an independent evaluator; any final
   diff invalidates the prior verdict.
4. Integrate only exact evaluated commits through the Program Integration Queue.
5. Establish PR/CI, cross-project isolation, recovery, and serial release
   verification before any delivery claim.

## Research conclusion

The traceable findings and current-capability gaps are maintained in the
[Phase 1 evidence matrix](research/AFS_PHASE1_EVIDENCE_MATRIX.md). The historical
three-prototype comparison remains reproducible through the
[Phase 2 evaluation protocol](AFS_EPISODE_LOOP_PHASE2_EVALUATION_PROTOCOL.md),
but it no longer controls the selected frontend direction.
AFS should not differentiate by canvas presence or agent count. The open
product opportunity is one visible chain from object change to affected shots,
creator scope decision, recoverable version update, review evidence, and
delivery traceability.
