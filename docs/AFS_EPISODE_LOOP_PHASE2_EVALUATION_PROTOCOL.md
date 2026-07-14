# AFS Episode Loop Phase 2 Evaluation Protocol

Status: frozen same-task protocol candidate. It evaluates isolated prototypes;
it does not authorize production frontend integration or claim human acceptance.

## Required inputs

The evaluator must read these before scoring:

1. [Phase 1 evidence and AFS gap matrix](research/AFS_PHASE1_EVIDENCE_MATRIX.md)
2. [Episode production fact contract v0.1](architecture/AFS_EPISODE_PRODUCTION_FACT_CONTRACT.md)
3. `examples/representative_episode/episode_package.json`
   - SHA256 `0AF7D008C39074765E60057F5D80F92F59CE45999EF3E216FD8562A963B9A2A2`
4. `examples/representative_episode/episode_revision_v2.json`
   - SHA256 `0796D47C465C0467201D41863CE5ABF9A01703E9B7DDB22DE0F47BE350AEA45B`

If a fixture, common harness, scenario overlay, or prototype changes after an
evaluation, that result is invalid. All three variants must use the same frozen
base and be presented anonymously as A, B, and C.

## Variants under comparison

- Guided flow
- Storyboard/canvas-first
- Project shell with an internal professional creation space

These are hypotheses, not preselected production architecture. Prototype code
must stay under isolated non-production experiment directories.

## Common scenario overlay

Do not edit the representative fixture. The harness injects the same defects:

- Shot 6 is temporarily assigned to the wrong scene and must be restored to the
  old archive tower.
- Shot 7 has the lamp buckle on the wrong shoulder and a mirrored scar.
- Shot 8 is a decoy and must not be flagged as the same contradiction.
- Shot 11 has v1 and v2 text/storyboard alternatives. Only shot 11 may change;
  the other 14 shots must retain their facts.
- Delivery remains blocked by 25 missing assets. No prototype may fabricate a
  playable result or imply provider generation occurred.

## Same-task script

1. Start from the truthful project state and identify the next useful action.
2. Inspect the imported script breakdown and repair Shot 6's scene assignment.
3. Find the real Shot 7 continuity conflict, inspect affected work, and leave
   the Shot 8 decoy unchanged.
4. Compare Shot 11 v1/v2, choose v2 for eight affected downstream items, stop
   after three reconfirmations, reload, recover exactly, and finish all eight.
5. Inspect delivery, explain why it is blocked, and identify what remains
   without exposing raw IDs, provider/runtime vocabulary, or fake progress.

## Research-derived evaluation criteria

| Criterion | Evidence reason | Observable test |
|---|---|---|
| New-user orientation and expert direct access | LibTV/WorkRally/LTX show dense professional spaces; density alone does not establish a usable first path | Can a new user name the next action, while an expert reaches a known shot without replaying onboarding? |
| One object across contexts | WorkRally, Celtx, LTX, and current AFS gaps show the cost of split project/scene/shot/reference stores | Does the same Shot 11 retain one semantic identity in breakdown, storyboard, review, and delivery? |
| Change impact and creator scope | No reviewed product publicly proves the full change-to-impact-to-rollback chain | Does a continuity change show affected shots, what changes, what remains, and let the creator select scope before execution? |
| Exact-version review and rollback | Frame.io demonstrates mature comparison; AFS needs object-aware traceability beyond files | Can the creator compare v1/v2, understand the selected version, reload mid-task, and restore without drift? |
| Local versus global action clarity | Runway workflows expose local runs and locks; current AFS actions are fragmented | Is every action's scope visible before commit, and can a local refusal avoid unrelated changes? |
| Truthful blocked delivery | 万镜 job recovery and current AFS fixed delivery show why technical completion and creator completion differ | Does the prototype state 25 missing assets and next actions without fake media, fake percentage, or provider jargon? |
| Data-use clarity | Official policies vary by plan/surface and often remain incomplete | Does default project language remain private/no-training and avoid implying feedback becomes training or memory? |

## Metrics

Record per task and per participant:

- final task state;
- active completion time;
- meaningful activations, excluding duplicate click events caused by keyboard;
- explicit screen/context transitions;
- critical decision errors;
- recoverable decision errors;
- lostness or inability to name the next action;
- reload recovery fidelity;
- keyboard/focus failures and page overflow at desktop, `390x844`, and `360x800`.

The common event log must record semantic task, action, object, previous/current
view, input method, monotonic duration, and a safe state summary. Raw IDs may be
used in internal `data-testid` values but not displayed in the default UI.

## Hard gates and selection rule

All variants must:

- complete at least 90% of scripted tasks;
- have no critical errors in tasks 2-5;
- recover the exact 3/8 reconfirmation checkpoint after reload;
- avoid fabricated media/progress and engineering-language leaks;
- support keyboard operation, visible focus, live error/recovery feedback, and
  no page-level horizontal overflow at both mobile sizes.

A winner additionally needs at least two of:

- 15% lower active time;
- 20% fewer meaningful activations;
- at least one fewer context transition.

Team and solo cohorts must not rank the variants in opposite order. Human
selection requires at least six valid sessions spanning both small-team and
solo use. Machine-only evaluation may close task-structure defects, but cannot
claim human acceptance. If evidence is close, conflicting, or below threshold,
return an exact `decision_needed` instead of choosing by preference.

## Evaluator return

Return per variant: task outcomes, measurements, critical/recoverable errors,
research-criterion findings, recovery/a11y/mobile results, evidence level, and
residual risk. Then return exactly one integration decision:

- `select_for_production_validation`;
- `rework_and_repeat`;
- `decision_needed`.

