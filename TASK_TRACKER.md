# AgentFlow Studio Task Tracker

中文摘要：本文件是当前 AFS MVP 的任务入口，只记录仍需要执行、验证或交接的事项。当前主线已经锁定 Studio 前端、Runtime API、专业知识库、创作意图控制智能体和图片/关键帧 provider gate；旧 Workbench、旧 Web RC、历史候选记忆 UI 和过期支线不再作为任务来源。任何事项如果不能导向第一版 MVP 落地、真实模型接入或低成本维护，应从这里移除。

保留理由：本文的价值在于让后续维护者快速判断当前任务是否仍能推动 MVP 收口和真实模型接入。每个任务都必须对应明确接口、测试、证据和非声明边界；没有当前引用的旧任务直接删除。真实模型接入前，所有结论都要重新经过本地测试、provider gate 检查、safe manifest 检查和人工体验确认。

当前口径：待办只保留三类，一是 Studio 和 Runtime 的联合验收，二是图片/关键帧真实模型 gate，三是创作智能体规则、评分和反馈回路的可验证改进。除此之外的旧支线、旧 UI 设想和无测试证据的概念记录都不进入任务列表。

Last updated: 2026-07-05 by Codex

P0 reference upload Runtime error UX local contract addendum: Lane
`FIX-P0-REFERENCE-UPLOAD-RUNTIME-ERROR-UX-LOCAL-CONTRACT` completed a bounded
Studio/Runtime client error-normalization fix for dispatch
`TD-AFS-V02-FIX-P0-REFERENCE-UPLOAD-RUNTIME-ERROR-UX-LOCAL-CONTRACT-20260705-001`
on `codex/p0-reference-upload-runtime-error-ux-20260705`; expected BU
`BU-AFS-V02-FIX-P0-REFERENCE-UPLOAD-RUNTIME-ERROR-UX-LOCAL-CONTRACT-20260705-001`.
The slice prevents reference upload/replace failures from rendering
`[object Object]`, normalizes structured Runtime 422 bodies and validation
arrays into safe Chinese messages with reason, field label, code, request id,
and stage when present, and reuses Studio safe redaction for string errors.
Reference upload now fails locally with clear Chinese messages for unsupported
node targets and unsupported image file types before reading bytes or calling
Runtime. Existing successful upload binding for image, video first frame,
keyframe generation, and asset-card draft references remains covered. Available
validation passed focused pytest (`3 passed`), `python -m py_compile` on the
touched Python test, `npm run check:studio-js`, and direct Node assertions for
object/array error bodies. No browser/server/provider/source-sync/deploy/
restart/COS/CompanyOS/source-KB mutation or generated-media QA is claimed.
Handoff:
`docs/handoff/AFS-P0-REFERENCE-UPLOAD-RUNTIME-ERROR-UX-LOCAL-CONTRACT-20260705.md`.

P0 final media acceptance linked QA decision packet addendum: Lane
`IMPL-P0-FINAL-MEDIA-ACCEPTANCE-LINKED-QA-DECISION-PACKET` completed a bounded
schema/algorithm/static-action contract slice for dispatch
`TD-AFS-V02-IMPL-P0-FINAL-MEDIA-ACCEPTANCE-LINKED-QA-DECISION-PACKET-20260705-001`
on `codex/final-media-acceptance-decision-packet-20260705`; expected BU
`BU-AFS-V02-IMPL-P0-FINAL-MEDIA-ACCEPTANCE-LINKED-QA-DECISION-PACKET-20260705-001`.
The slice adds `agentflow.algorithms.final_media_acceptance_decision` with
artifact type `agentflow_final_media_acceptance_decision`, schema `0.1.0`, and
algorithm id `afs.final_media_acceptance_decision.v0.1`. It consumes only
structured QA checklist packet refs, safe summary counts, safe output
summaries, blocker ids, packet timestamp, and explicit reviewer action; it does
not recalculate checklist truth or copy checklist item arrays into the final
decision artifact. `qa_passed` can enable local reviewer action but cannot set
`accepted_for_local_final_media` without explicit supported-role reviewer
`accept`. Fail-closed coverage includes stale/malformed/unsafe checklist packet
refs, project/target/checklist-ref mismatch, active Runtime states, missing
output, missing safe preview, critical fail count, safety/scope/conflict
blockers, invalid waiver states, missing blocker ids where blocked counts
exist, and unsupported reviewer roles. Static Studio action wiring reuses
existing action ids `accept`, `reject`, and `view_evidence` without changing
Studio JS. Available validation passed `python3 -m py_compile`, focused pytest
through `/home/afs-ops/AgentFlowStudio/.venv/bin/python` (`6 passed`), direct
no-pytest assertions, and `git diff --check`; system `python3` still lacks
`pytest`. No
Runtime/OpenAPI/Studio UI/browser/server/provider/generated-media QA,
human/business/public/legal readiness, durable-memory promotion,
COS/CompanyOS/source-KB mutation, archive execution, or self-archive is
claimed. Handoff:
`docs/handoff/AFS-P0-FINAL-MEDIA-ACCEPTANCE-LINKED-QA-DECISION-PACKET-20260705.md`.

P0 fixed asset reuse link integration addendum: Lane
`IMPL-P0-FIXED-ASSET-REUSE-LINK-INTEGRATION` completed a bounded
Runtime/Studio local contract implementation for dispatch
`TD-AFS-V02-IMPL-P0-FIXED-ASSET-REUSE-LINK-INTEGRATION-20260705-001`
on `codex/p0-fixed-asset-reuse-link-integration-20260705`; expected BU
`BU-AFS-V02-IMPL-P0-FIXED-ASSET-REUSE-LINK-INTEGRATION-20260705-001`.
The slice persists Runtime `asset_auto_binding_graph` through Studio
script-breakdown/storyboard surfaces, maps graph-bound fixed assets into
storyboard shot and asset-card `nodeReferenceStack` plus keyframe
`visualAssets`, preserves actual Studio `assetReuseLocalContract()`
`graph_bound_count`, and requires explicit `link_existing` / `replace` /
`create_new` intent for fixed visual asset submit when a graph-bound or same
type+label fixed asset exists. Runtime visual asset promotion now validates
explicit duplicate/reuse intent, supports `link_existing`, validates
`replace`, emits structured duplicate warnings, and the OpenAPI snapshot was
regenerated for the new request fields. Available validation passed
`npm run check:studio-js` (`143 files`), `python3 -m py_compile` on touched
Python/tests, focused pytest (`54 passed` plus OpenAPI/promotion gate
`3 passed`), direct Node graph-bound intent assertion, and `git diff --check`.
No provider behavior change/call/gate, Runtime/Studio server run, browser/live
`/studio/` QA, deploy/restart, source-sync/fetch/pull/push, generated-media
QA, duplicate-prevention live claim, human/business/public/legal readiness
claim, durable-memory promotion, COS/CompanyOS/source-KB mutation, archive
execution, or self-archive is claimed. Handoff:
`docs/handoff/AFS-P0-FIXED-ASSET-REUSE-LINK-INTEGRATION-20260705.md`.

P2 prompt textarea resize/expand addendum: Lane
`FIX-P2-PROMPT-TEXTAREA-RESIZE-EXPAND` completed a bounded Studio prompt
ergonomics slice for dispatch
`TD-AFS-V02-FIX-P2-PROMPT-TEXTAREA-RESIZE-EXPAND-20260705-001` on
`codex/fix-p2-prompt-textarea-resize-expand-20260705`; expected BU
`BU-AFS-V02-FIX-P2-PROMPT-TEXTAREA-RESIZE-EXPAND-20260705-001`.
The slice makes the inline prompt bar textarea vertically resizable with
responsive height limits, repositions the bar through a resize observer after
manual expansion, exposes the large prompt editor from all prompt-capable Studio
nodes, preserves text/script body content and asset-card user adjustment state
through expanded edits, and makes the generation settings prompt textarea
vertically resizable without changing Runtime/OpenAPI/provider behavior.
Available validation passed `npm run check:studio-js`, focused static pytest
through `/home/afs-ops/AgentFlowStudio/.venv/bin/python` (`15 passed`), direct
Node marker assertions, and required git whitespace checks recorded in BU.
System `python3` still lacks `pytest`. No browser/runtime/server/provider/
generated-media QA, human/business/public/legal readiness claim, source sync,
push, deploy, restart, Runtime/OpenAPI/COS/CompanyOS/source-KB mutation, archive
execution, or self-archive is claimed. Handoff:
`docs/handoff/AFS-P2-PROMPT-TEXTAREA-RESIZE-EXPAND-20260705.md`.

P0 structured QA checklist active Runtime noncompletion recovery addendum: Lane
`FIX-P0-STRUCTURED-QA-CHECKLIST-ACTIVE-RUNTIME-NONCOMPLETION` completed a
bounded recovery callback for dispatch
`TD-AFS-V02-FIX-P0-STRUCTURED-QA-CHECKLIST-ACTIVE-RUNTIME-NONCOMPLETION-20260705-001`
on `codex/p0-structured-source-output-qa-checklist-packet-20260704`; expected
BU `BU-AFS-V02-FIX-P0-STRUCTURED-QA-CHECKLIST-ACTIVE-RUNTIME-NONCOMPLETION-20260705-001`.
The recovery prevents active Runtime states `submitted`, `pending`, `running`,
and `retrying` from producing `checklist_completed` even when all items are
followed or a non-critical waiver would otherwise be valid. Active packets now
remain non-completed as `blocked_missing_evidence` with safe reason code
`runtime_state_not_stable_reviewable`, and waiver validation records the same
reason so active Runtime targets cannot be waived into completion. Stable
completed target behavior, stable partial output preservation, unsafe
fail-closed redaction, invalid waiver handling, critical/safety/scope/project
mismatch, conflict handling, missing first-frame provenance, and forbidden/
non-claim field absence remain covered. Available validation passed
`python3 -m py_compile`, focused pytest through
`/home/afs-ops/AgentFlowStudio/.venv/bin/python` (`7 passed`), direct
no-pytest assertions, `git diff --check`, and alternate-venv CLI help/version;
system `python3` still lacks `pytest`. No Runtime/OpenAPI/Studio/browser/
server, provider, generated-media QA, final media decision,
human/business/public/legal readiness, durable-memory promotion,
COS/CompanyOS/source-KB mutation, archive execution, or self-archive is claimed.
Handoff:
`docs/handoff/AFS-P0-STRUCTURED-QA-CHECKLIST-ACTIVE-RUNTIME-NONCOMPLETION-20260705.md`.

P0 structured source/output QA checklist packet addendum: Lane
`IMPL-P0-STRUCTURED-SOURCE-VS-OUTPUT-QA-CHECKLIST-PACKET` completed a bounded
pure algorithm/schema/test slice for dispatch
`TD-AFS-V02-IMPL-P0-STRUCTURED-SOURCE-VS-OUTPUT-QA-CHECKLIST-PACKET-20260704-001`
on `codex/p0-structured-source-output-qa-checklist-packet-20260704`; expected
BU `BU-AFS-V02-IMPL-P0-STRUCTURED-SOURCE-VS-OUTPUT-QA-CHECKLIST-PACKET-20260704-001`.
The slice adds `agentflow.algorithms.structured_source_output_qa_checklist` with
artifact type `agentflow_structured_source_output_qa_checklist`, schema
`0.1.0`, safe source inventory, safe output refs, item outcome/severity/blocker
state, summary counts, waiver validation, sanitized reviewer notes, suggested
local actions, and deterministic fail-closed states for missing evidence,
unsafe payloads, project/target scope mismatch, equal-rank conflicts, and
unverifiable evidence. Waivers can close only non-critical evidence exceptions;
they cannot override critical, safety, scope, project mismatch, unsafe payload,
missing target output, missing safe preview, or active Runtime state conditions.
Available validation passed `python3 -m py_compile` and direct no-pytest
execution of all new test functions; focused pytest is blocked because
`/usr/bin/python3` has no `pytest`. No Runtime/OpenAPI/Studio/browser/server,
provider, generated-media QA, final media decision, human/business/public/legal
readiness, durable-memory promotion, COS/CompanyOS/source-KB mutation, archive
execution, or self-archive is claimed. Handoff:
`docs/handoff/AFS-P0-STRUCTURED-SOURCE-OUTPUT-QA-CHECKLIST-PACKET-20260704.md`.

P0 asset reuse UX safe text redaction recovery addendum: Lane
`FIX-P0-ASSET-REUSE-UX-SAFE-TEXT-REDACTION` recovered evaluator blocker
`fail_closed_redaction_gap` for dispatch
`TD-AFS-V02-FIX-P0-ASSET-REUSE-UX-SAFE-TEXT-REDACTION-20260704-001` on
`codex/p0-asset-reuse-ux-explanation-reversal-20260704`; expected BU
`BU-AFS-V02-FIX-P0-ASSET-REUSE-UX-SAFE-TEXT-REDACTION-20260704-001`.
The recovery adds a shared Studio-local redaction helper used by both
`assetReuseLocalContract()` and `buildOptimizationRequest()` upload summaries,
so unsafe fragments embedded inside otherwise valid `user_intent` text are
redacted consistently. Covered fragments include raw provider markers,
`raw_provider_response`, `data_base64`, `data:*` URIs, base64/media-byte
signatures, long base64-like payloads, signed/private URLs,
bearer/token-like strings, local paths, and raw media markers. Legitimate short
human intent text is preserved. Direct assertions continue to cover asset reuse
states, reversal action applicability, non-destructive preservation,
asset-card draft separation, optimizer `asset_reuse` gating, and
reference-upload actual-path behavior. No fetch/pull/push/source-sync,
Runtime/Studio server/browser run, provider call/gate mutation, deploy/restart,
generated-media QA, OpenAPI/DOC2/COS/CompanyOS/source-KB mutation,
readiness/human/business/public/legal claim, durable-memory promotion, archive
execution, or self-archive is claimed. Handoff:
`docs/handoff/AFS-P0-ASSET-REUSE-UX-SAFE-TEXT-REDACTION-RECOVERY-20260704.md`.

P0 asset reuse UX/explanation/reversal local contract addendum: Lane
`IMPL-P0-ASSET-REUSE-UX-EXPLANATION-REVERSAL-LOCAL-CONTRACT` completed a
bounded Studio local contract slice for dispatch
`TD-AFS-V02-IMPL-P0-ASSET-REUSE-UX-EXPLANATION-REVERSAL-LOCAL-CONTRACT-20260704-001`
on `codex/p0-asset-reuse-ux-explanation-reversal-20260704`; expected BU
`BU-AFS-V02-IMPL-P0-ASSET-REUSE-UX-EXPLANATION-REVERSAL-LOCAL-CONTRACT-20260704-001`.
The slice adds a safe `asset_reuse` node-parameter summary for local Studio
state/explanation/reversal modeling. It recognizes uploads, fixed visual asset
reuse, optional asset auto-binding graph suggestions, node-reference stack
conflict states, blocked candidates, local reversal records, and generation
candidate rejection semantics where locally available. Reversal is
non-destructive: `binding` maps to `unbind`, `generation_candidate` maps to
`reject`, replace-capable entities map to `replace`, and assets/media/provider
artifacts/source evidence/upload records/candidate records are preserved.
Asset-card drafts remain draft/candidate inputs through
`role=asset_reference` and `reference_target=asset_card_draft`; they are not
confirmed fixed assets or ordinary keyframe generations. Available validation
passed `python3 -m py_compile`, direct Node/static assertions for the actual
local paths, `npm run check:studio-js`, and reference-upload regression
assertions; focused pytest is blocked because `.venv/bin/python` is unavailable
and `/usr/bin/python3` has no `pytest`. No fetch/pull/push/source-sync,
provider call/gate mutation, Runtime/Studio server/browser run,
deploy/restart, generated-media QA, OpenAPI/DOC2/COS/CompanyOS/source-KB
mutation, readiness/human/business/public/legal claim, durable-memory
promotion, archive execution, or self-archive is claimed. Handoff:
`docs/handoff/AFS-P0-ASSET-REUSE-UX-EXPLANATION-REVERSAL-LOCAL-CONTRACT-20260704.md`.

P0 reference upload flexibility local contract addendum: Lane
`IMPL-P0-REFERENCE-UPLOAD-FLEXIBILITY-LOCAL-CONTRACT` completed a bounded
Studio local contract slice for dispatch
`TD-AFS-V02-IMPL-P0-REFERENCE-UPLOAD-FLEXIBILITY-LOCAL-CONTRACT-20260704-001`
on `codex/p0-reference-upload-flexibility-20260704`; expected BU
`BU-AFS-V02-IMPL-P0-REFERENCE-UPLOAD-FLEXIBILITY-LOCAL-CONTRACT-20260704-001`.
The slice makes direct reference uploads node-aware in the existing
`params.uploads` path, preserving safe upload metadata and bounded
`user_intent`; video nodes bind uploaded images immediately as first-frame
references, keyframe-generation image nodes carry
`reference_target=keyframe_generation`, and asset-card drafts carry
`role=asset_reference` plus `reference_target=asset_card_draft` so they are not
treated as ordinary keyframe generations. Optimization node parameters now
surface the same safe upload summaries through `uploaded_images`. Available
validation passed `python3 -m py_compile`, direct no-pytest actual-path
execution, `npm run check:studio-js`, and `git diff --check`; focused pytest is
blocked because `.venv/bin/python` is absent and `/usr/bin/python3` has no
`pytest`. No source-sync/fetch/pull/push, provider call/gate, Runtime/Studio
server run, deploy/restart, browser QA, generated-media QA, OpenAPI/DOC2/COS/
CompanyOS/source-KB mutation, readiness/human/business/public/legal claim,
durable-memory promotion, archive execution, or self-archive is claimed.
Handoff:
`docs/handoff/AFS-P0-REFERENCE-UPLOAD-FLEXIBILITY-LOCAL-CONTRACT-20260704.md`.

P0 multi-candidate job-state retry actual-path recovery addendum: Lane
`FIX-P0-MULTI-CANDIDATE-JOB-STATE-RETRY-ACTUAL-PATH-RECOVERY` completed a
bounded callback fix for dispatch
`TD-AFS-V02-FIX-P0-MULTI-CANDIDATE-JOB-STATE-RETRY-ACTUAL-PATH-RECOVERY-20260704-001`
on `codex/p0-multi-candidate-job-state-retry-20260704`. The recovery forwards
`options.retrying` through `applyKeyframeResponse()` into
`updateNodeGenerationState()`, closing the evaluator gap where helper-level
checks passed but the actual keyframe response path dropped retry intent for
active Runtime statuses. The recovery-owned boundary expands to
`apps/studio/src/node-keyframe-response.js` because that was the failing actual
path. Focused direct Node coverage now asserts active `submitted`, `pending`,
and `running` preserve `generationPolicyStatus=retrying` and
`retryFailedItemsOnly=true`, while terminal `complete`, `partially_complete`,
`failed`, and `needs_attention` clear stale retrying. No provider/runtime/server
/browser/deploy/source-sync/readiness claim is made. Handoff:
`docs/handoff/AFS-P0-MULTI-CANDIDATE-JOB-STATE-RETRY-20260704.md`.

P0 multi-candidate job-state retry addendum: Lane
`IMPL-P0-MULTI-CANDIDATE-JOB-STATE-RETRY` completed bounded Studio retry-state
implementation for dispatch
`TD-AFS-V02-IMPL-P0-MULTI-CANDIDATE-JOB-STATE-RETRY-20260704-001` on
`codex/p0-multi-candidate-job-state-retry-20260704`; expected BU
`BU-AFS-V02-IMPL-P0-MULTI-CANDIDATE-JOB-STATE-RETRY-20260704-001`.
The slice preserves failed-items-only retry job state through active keyframe
Runtime responses after a multi-candidate retry submit, including bootstrap
refresh and background polling, and guards terminal responses so stale retrying
state clears on complete/partial/failed/needs-attention outcomes. Available
validation passed `python3 -m py_compile` on the focused static test,
`npm run check:studio-js` (`139 files`), direct no-pytest execution of the new
static regression, direct Node retry-state assertions, and `git diff --check`;
focused pytest is blocked because `/usr/bin/python3` has no `pytest`.
Unrelated Owner dirty docs were preserved by using an isolated worktree. No
fetch/pull/push/source-sync, provider call/gate, Runtime/Studio server run,
deploy/restart, generated-media QA, OpenAPI/DOC2/COS/CompanyOS/source-KB
mutation, readiness/human/business/public/legal claim, durable-memory
promotion, archive execution, or self-archive is claimed. Handoff:
`docs/handoff/AFS-P0-MULTI-CANDIDATE-JOB-STATE-RETRY-20260704.md`.

P0 node reference stack priority eval gaps recovery addendum: Lane
`FIX-P0-NODE-REFERENCE-STACK-PRIORITY-EVAL-GAPS` completed bounded evaluator
recovery for dispatch
`TD-AFS-V02-FIX-P0-NODE-REFERENCE-STACK-PRIORITY-EVAL-GAPS-20260704-001` on
`codex/p0-node-reference-stack-priority-20260704`. The recovery changes
node-reference reversal actions to use a Studio-compatible per-entity map, so
selected `generation_candidate` references emit `reject` rather than
`replace`; blocks `data:*`, `data:image/...;base64`, raw base64 media
signatures, long base64 media-byte-like refs, and bytes targets; and fails
closed when imported `agentflow_asset_auto_binding_graph` suggestions have an
empty fixed asset id, missing `asset_auto_binding_established` relationship, or
missing/incomplete source relationship. Available validation passed
`.venv/bin/python -m py_compile` on touched Python modules/tests,
`git diff --check`, focused pytest `8 passed`, and direct no-pytest assertions
for action applicability, unsafe target blocking, and malformed asset-binding
graph fail-closed behavior. Unrelated dirty owner-matrix and demo/maintenance
docs were preserved outside the staged recovery. No master integration,
source-sync/fetch/pull/push, provider call/gate, Runtime/Studio UI/OpenAPI/DOC2
/COS/CompanyOS mutation, deploy/restart/server action, generated-media QA,
readiness claim, human/business/public/legal claim, durable-memory promotion,
archive execution, or self-archive is claimed. Handoff:
`docs/handoff/AFS-P0-NODE-REFERENCE-STACK-PRIORITY-EVAL-GAPS-20260704.md`.

P0 node reference stack priority addendum: Lane
`IMPL-P0-NODE-REFERENCE-STACK-PRIORITY` completed a bounded contract/model
slice for dispatch
`TD-AFS-V02-IMPL-P0-NODE-REFERENCE-STACK-PRIORITY-20260704-001` on
`codex/p0-node-reference-stack-priority-20260704`; BU
`BU-AFS-V02-IMPL-P0-NODE-REFERENCE-STACK-PRIORITY-20260704-001`, close state
`node_reference_stack_priority_completed`. The slice adds
`agentflow.algorithms.node_reference_stack` with explicit reference
type/scope/status/target-slot/priority fields, deterministic priority then
scope then Studio entity type precedence, fail-closed
`unresolved_equal_rank_conflict` handling, explainability and reversible
`unbind`/`replace` boundaries, and no provider or memory writes. It registers
the module in the algorithm library, depends on existing Studio vocabulary ids
for Project Asset, Reference Input, Generation Candidate, Keyframe Version,
Video Revision, Binding, and Lineage, and imports established
`asset_auto_binding_established` suggestions as reversible `binding`
references where present. Available validation passed `python3 -m py_compile`
on touched node reference stack modules/tests, `git diff --check`, direct
no-pytest execution of the new test functions, asset-binding stack assertions,
equal-rank conflict assertions, and Studio vocabulary marker assertions; focused
pytest remains blocked because `/usr/bin/python3` has no `pytest`, and CLI
help/version checks remain blocked because `/usr/bin/python3` has no `typer`.
No provider behavior change/call/rerun, generated-media QA, node UI redesign,
Runtime, OpenAPI, DOC2, COS, or CompanyOS mutation, multi-candidate retry
engine, keyframe edit, video adherence, source-sync/fetch/pull/push,
deploy/restart/server mutation,
durable-memory promotion, readiness, human/business/public/legal claim, archive
execution, or self-archive is claimed. Handoff:
`docs/handoff/AFS-P0-NODE-REFERENCE-STACK-PRIORITY-20260704.md`.

Asset auto-binding reversible graph addendum: Lane
`IMPL-P0-ASSET-AUTO-BINDING-REVERSIBLE-GRAPH` completed bounded contract and
implementation slice for dispatch
`TD-AFS-V02-IMPL-P0-ASSET-AUTO-BINDING-REVERSIBLE-GRAPH-20260704-001` on
`codex/asset-auto-binding-reversible-graph-20260704`; BU
`BU-AFS-V02-IMPL-P0-ASSET-AUTO-BINDING-REVERSIBLE-GRAPH-20260704-001`, close
state `asset_auto_binding_reversible_graph_completed`. The slice adds
`agentflow.algorithms.asset_auto_binding` with deterministic exact
type/normalized-label matching, confidence threshold `0.82`, required candidate
evidence, required fixed source evidence, duplicate/unsupported/merge-candidate
fail-closed blocking, and explicit reversible `unbind` plans. Production graph
snapshots now include safe `asset_auto_binding_established` relationships and a
nested `agentflow_asset_auto_binding_graph`; storyboard output also writes a
standalone `asset_auto_binding_graph` artifact, safe manifest counts, and
evidence ledger role. Available validation passed `python3 -m py_compile` on
touched Python files/tests, `git diff --check`, pure no-pytest binding
assertions, static contract assertions, and direct production-graph integration
assertions. CLI help/version checks are blocked because `/usr/bin/python3` has
no `typer`; focused pytest is blocked because `/usr/bin/python3` has no
`pytest`; direct Runtime route substitute is blocked because `/usr/bin/python3`
has no `fastapi`, and no `.venv` is present. No provider call/rerun,
generated-media QA, human acceptance, node reference stack UI,
multi-candidate retry engine, keyframe edit, video adherence implementation,
source-sync/fetch/pull/push, deploy/restart/runtime server mutation,
OpenAPI/DOC2/COS/CompanyOS mutation, fixed-asset promotion, durable-memory
promotion, readiness, human/business/public/legal claim, archive execution, or
self-archive is claimed. Handoff:
`docs/handoff/AFS-ASSET-AUTO-BINDING-REVERSIBLE-GRAPH-20260704.md`.

Safe packet and Studio vocabulary contract integration addendum: Lane
`INT-P1-P0-SAFE-PACKET-AND-STUDIO-VOCAB-CONTRACT` integrated accepted safe
human-review packet/redaction tip
`6bf93bc63c57523a08a3226c723aee5fc14bf90d` and P0 Studio
entity/status/action vocabulary contract tip
`6adbcd018f0af08975223ef9537b0dabecbceac6` into local `master` for dispatch
`TD-AFS-V02-INT-P1-P0-SAFE-PACKET-AND-STUDIO-VOCAB-CONTRACT-20260704-001`.
Pre-integration HEAD was
`c40c4c40a2a77b6c915ef798b14dfef2d6e5f564`, and both source commits were
locally readable and branch-contained before mutation. Integration used
non-mutating merge-tree inspection plus `git cherry-pick --no-commit` over the
two source ranges; only expected additive conflicts in `DEVLOG.md` and
`docs/handoff/INDEX.md` were manually resolved, while `TASK_TRACKER.md`
auto-merged. Verification passed `git diff --check`, `git diff --cached
--check`, `npm run check:studio-js`, py_compile on touched Python files/tests
with temp pycache routing, safe-packet redaction no-pytest assertions, Studio
entity/action no-pytest assertions over 39 pairs, and focused pytest
`9 passed`. Pre-existing dirty docs were preserved outside the staged
integration: Owner acceptance matrix handoff, `docs/demo/`, and
`docs/maintenance/AFS-DEMO-DOCS-CHINESE-20260629.md`. No source-sync/fetch/pull
/push, provider gate/call, deploy/restart/runtime server mutation,
generated-media QA, video/vision readiness, packet-readiness,
human/business/public/legal readiness, OpenAPI/DOC2/COS/CompanyOS mutation,
durable-memory promotion, archive execution, or self-archive is claimed.
Handoff:
`docs/handoff/AFS-SAFE-PACKET-STUDIO-VOCAB-CONTRACT-INTEGRATION-20260704.md`.

P0 Studio entity/status action consistency recovery addendum: Lane
`FIX-P0-STUDIO-ENTITY-STATUS-ACTION-CONSISTENCY` corrected evaluator blocker
`fail_contract_action_applicability_mismatch` for dispatch
`TD-AFS-V02-FIX-P0-STUDIO-ENTITY-STATUS-ACTION-CONSISTENCY-20260704-001` on
`codex/p0-studio-entity-status-vocab-contract-20260704`. The recovery keeps the
existing `lineage` next action intent and makes `replace.appliesTo` include
`lineage` in both `apps/studio/src/studio-entity-status-vocabulary.js` and
`docs/handoff/AFS-P0-STUDIO-ENTITY-STATUS-VOCAB-CONTRACT-20260704.md`. Focused
static coverage now asserts every entity `nextActions[]` entry resolves to an
action whose `appliesTo[]` includes that entity, preventing this mismatch from
recurring. Available validation passed `git diff --check`,
`npm run check:studio-js`, `python3 -m py_compile` on the focused static test,
and a standalone Node nextAction/appliesTo consistency assertion over 39 pairs.
Focused pytest remains blocked because `/usr/bin/python3` has no `pytest` and
`.venv/bin/python` is absent. No UI behavior,
Runtime/OpenAPI/DOC2/COS/CompanyOS mutation, provider call,
generated-media/browser QA, source-sync/fetch/pull/push, deploy/restart/server
action, readiness claim, human/business/public/legal claim, durable-memory
promotion, archive execution, or self-archive is claimed.

P0 Studio entity/status vocabulary contract addendum: Lane
`IMPL-P0-STUDIO-ENTITY-STATUS-VOCAB-CONTRACT` established the first shared
Studio UI and Owner acceptance vocabulary baseline for dispatch
`TD-AFS-V02-IMPL-P0-STUDIO-ENTITY-STATUS-VOCAB-CONTRACT-20260704-001` on
`codex/p0-studio-entity-status-vocab-contract-20260704`. The contract covers
`Project Asset`, `Reference Input`, `Generation Candidate`, `Keyframe Version`,
`Video Revision`, `Binding`, and `Lineage`; maps canonical statuses
`queued/submitted/running/succeeded/failed/retryable/cancelled/blocked/needs_attention/partial`
to existing Runtime/Studio equivalents; defines action vocabulary
`bind/unbind/replace/reference/retry/accept/reject/view_lineage/view_evidence/continue_to_video/edit_keyframe`;
and adds a small Studio vocabulary constants module at
`apps/studio/src/studio-entity-status-vocabulary.js` with focused static
coverage. Available validation passed `npm run check:studio-js` (`139 files`),
`git diff --check`, `python3 -m py_compile` on the focused static test,
no-pytest contract/record assertions, Node vocabulary import assertions, and
new-file whitespace checks; focused pytest is blocked because `/usr/bin/python3`
has no `pytest` module and `.venv/bin/python` is absent or not executable. This
is a contract baseline only: no auto-binding graph behavior, reference stack UI,
multi-candidate retry engine, local keyframe edit, video adherence panel,
provider call, generated-media QA, browser QA, deploy/restart,
OpenAPI/DOC2/COS/CompanyOS mutation, readiness, human/business/public/legal
claim, durable-memory promotion, archive execution, or self-archive is claimed.
Handoff:
`docs/handoff/AFS-P0-STUDIO-ENTITY-STATUS-VOCAB-CONTRACT-20260704.md`.

Current-state maintenance pointer - 2026-07-03: For tracker/devlog current
entrypoints, release/current-state summary, provider/REL1B blockers, historical
summary routes, and the rule blocking old-stream pruning until docs refscan plus
Owner/CTO gates, use
`docs/maintenance/AFS-TRACKER-DEVLOG-CURRENT-STATE-INDEX-20260703.md`. This is
an additive pointer only; no tracker content has been pruned, archived, deleted,
or promoted to readiness/provider/human/business/legal/COS claims.

Human review prompt redaction recovery addendum: Lane
`FIX-P1-REL1B-HUMAN-REVIEW-PROMPT-REDACTION` recovered evaluator blocker
`fail_prompt_review_redaction_value_leak` for dispatch
`TD-AFS-V02-FIX-P1-REL1B-HUMAN-REVIEW-PROMPT-REDACTION-20260704-001` on
`codex/imp-p1-rel1b-human-review-safe-packet-surface-fields-20260704`.
Prompt review summary redaction now removes full secret-like label/value
fragments before `prompt_optimization_review_summary.json` is persisted,
covering password, token/access-token, auth/authorization, cookie/session,
bearer, api-key, secret, signed-url, and key variants across `=`, `:`,
whitespace, quoted, and JSON-like forms. The safe human-review packet forbidden
surface was widened for the same label family, and focused tests/static
assertions prove synthetic forbidden values do not persist into the prompt
review summary or packet prompt summary while unsafe stale packet prompt text
fails closed. Available validation passed `python3 -m py_compile` on touched
Runtime/test modules, a no-pytest standard-library redaction assertion script,
and `git diff --check`; focused pytest remains blocked because
`/usr/bin/python3` has no `pytest`, with `fastapi` and `pydantic` also missing
from system Python and no `.venv` or `python` command available. Evaluator issue
is fixed at implementation/assertion level, pending fresh evaluator. No provider
gate/call, source sync/fetch/pull/push, deploy/restart/runtime server mutation,
OpenAPI/DOC2/COS/CompanyOS mutation, integration to master, packet-readiness
claim, human acceptance, generated-media QA, durable-memory promotion, archive
execution, or self-archive is claimed. Handoff:
`docs/handoff/AFS-HUMAN-REVIEW-PROMPT-REDACTION-RECOVERY-20260704.md`.

Human review safe packet surface fields addendum: Lane
`IMP-P1-REL1B-HUMAN-REVIEW-SAFE-PACKET-SURFACE-FIELDS` implemented a bounded
Runtime source/contract slice on
`codex/imp-p1-rel1b-human-review-safe-packet-surface-fields-20260704` for
dispatch
`TD-AFS-V02-IMP-P1-REL1B-HUMAN-REVIEW-SAFE-PACKET-SURFACE-FIELDS-20260704-001`.
Keyframe safe manifest and candidate summary now persist safe
`review_preview_refs` with only route/ref and dimensions/hash/byte-count
metadata; prompt optimization now writes
`prompt_optimization_review_summary.json` with prompt character count,
sanitized bounded prompt text, and creative-brief source artifact id. A
fail-closed packet selector/builder reads only these safe fields and focused
tests cover missing safe fields, forbidden-field exclusion, and happy-path safe
packet plan creation. Available verification passed `python3 -m py_compile` on
touched Runtime/test modules and `git diff --check`; focused pytest is blocked
because this checkout has no `.venv`, no `python` command, and
`/usr/bin/python3` lacks `pytest`, `fastapi`, and `pydantic`. No provider
gate/call, deploy/restart/runtime server mutation, source sync/fetch/pull/push,
OpenAPI/DOC2/COS/CompanyOS mutation, generated-media QA, human creative
acceptance, product/business/public/legal readiness claim, durable-memory
promotion, self-archive, or merge is claimed.
Handoff:
`docs/handoff/AFS-HUMAN-REVIEW-SAFE-PACKET-SURFACE-FIELDS-20260704.md`.

Control kernel Phase1b scheduler/eventbus integration addendum: Lane
`INT-P1-CONTROL-KERNEL-PHASE1B-SCHEDULER-EVENTBUS-INTEGRATION` integrated
accepted scheduler-linter source commit
`03d39eb5dc5c577af6ce87b6b4da1e770a9fe6d2` and event-bus worker-final ingest
source commit `28616fdd7ac55bd8093f7af07abf6acb3a2c1a26` into local `master`
for dispatch
`TD-AFS-V02-INT-P1-CONTROL-KERNEL-PHASE1B-SCHEDULER-EVENTBUS-INTEGRATION-20260703-001`.
Pre-integration HEAD was OpenAPI baseline
`4966d20aeea35dfc0bc6d33b0110689dbed02f81`, which was preserved. Conflict
strategy was non-mutating merge simulation followed by `git cherry-pick
--no-commit`; only expected additive conflicts in tracker/devlog/index,
`control_event_register` export, and focused tests were resolved. Verification
available in this checkout passed `python3 -m py_compile` on touched control
modules/tests and `.venv/bin/python -m pytest tests/test_control_event_register.py
tests/test_contract_registry_examples.py -q` with `20 passed`; system
`python3 -m pytest` remains blocked because `/usr/bin/python3` has no `pytest`
module. Pre-existing untracked `docs/demo/` and
`docs/maintenance/AFS-DEMO-DOCS-CHINESE-20260629.md` were preserved untouched.
No source-sync/fetch/pull/push, deploy/restart/runtime/server action, provider
gate/call, REL1B, generated-media QA, OpenAPI/DOC2/COS/CompanyOS mutation,
readiness/human/business/public/legal claim, durable-memory promotion, archive
execution, or self-archive is claimed. Archive policy remains
`agent_created_archive_when_useless`, `owner_manual_archive_excluded=no`,
`archive_after_ack_delivery_confirmed=true`. Handoff:
`docs/handoff/AFS-CONTROL-KERNEL-PHASE1B-SCHEDULER-EVENTBUS-INTEGRATION-20260703.md`.

Control scheduler linters minimal redispatch addendum: Lane
`IMP-P1-CONTROL-SCHEDULER-LINTERS-MINIMAL-REDISPATCH` implemented a bounded
lint-only scheduler check slice on
`codex/control-scheduler-linters-minimal-redispatch-20260703` for dispatch
`TD-AFS-V02-IMP-P1-CONTROL-SCHEDULER-LINTERS-MINIMAL-REDISPATCH-20260703-001`.
The slice adds read-only `lint_control_scheduler_state()` findings for completed
BU not processed, join_all without reason, single active lane without dependency
reason, stale lane without recovery outcome, and post-closeout next action
without a real wakeup/monitor mechanism. Verification available in this checkout
passed `python3 -m py_compile` on touched control/test modules and a no-pytest
assertion script covering clean state, all five requested findings, pseudo
wakeup rejection for `current_codex_delegation_response` plus inert
`monitor_ref`, and read-only/no-mutation behavior. Recovery dispatch
`TD-AFS-V02-RECOVERY-P1-CONTROL-SCHEDULER-LINTERS-MINIMAL-DURABLE-ARTIFACT-20260703-001`
created a durable local artifact on the same scheduler-linter branch and does
not claim evaluator pass or integration. Focused pytest is blocked because
`/usr/bin/python3` has no `pytest`; CLI help/version checks are blocked because
`/usr/bin/python3` has no `typer`. No archive daemon, destructive migration,
historical replay, source-sync/fetch/pull/push, deploy/restart/runtime/server
action, REL1B, provider gate/call, Runtime/Studio/OpenAPI/DOC2/COS/CompanyOS
mutation, generated-media QA, readiness claim, human/business/public/legal
claim, durable-memory promotion, self-archive, or merge is claimed. Archive
policy remains `agent_created_archive_when_useless`,
`owner_manual_archive_excluded=no`,
`archive_after_ack_delivery_confirmed=true`, with execution blocked until ACK
delivery is confirmed. Handoff:
`docs/handoff/AFS-CONTROL-SCHEDULER-LINTERS-MINIMAL-REDISPATCH-20260703.md`.

Project Book Owner acceptance matrix redispatch addendum: Lane
`DOC-P1-PROJECT-BOOK-OWNER-ACCEPTANCE-MATRIX-UPDATE-REDISPATCH` produced a
bounded Owner-facing acceptance matrix from the existing Owner index and
checklist for dispatch
`TD-AFS-V02-DOC-P1-PROJECT-BOOK-OWNER-ACCEPTANCE-MATRIX-UPDATE-REDISPATCH-20260703-001`.
The matrix maps landing route, package split/order, `/studio/` internal tryout,
SPEC2/accepted-plan structure, provider/media gates, runtime freshness, human
review, business/legal/COS gates, and archive policy as review decisions rather
than completion claims. It supersedes waiting on old pendingWorktreeId
`remote-ssh-discovered:afs-bwg-ops:792b0510-ea03-46c0-a0c6-8bd06486cad4`;
that worktree was not used or repaired. No provider/REL1B/generated-media QA,
source-sync/fetch/pull/push, deploy/restart/runtime/server mutation,
OpenAPI/DOC2/COS/CompanyOS mutation, cleanup/delete/archive, package-complete
claim, readiness claim, human/business/public/legal claim, or durable-memory
promotion occurred. Handoff:
`docs/handoff/AFS-PROJECT-BOOK-OWNER-ACCEPTANCE-MATRIX-REDISPATCH-20260703.md`.

Control event bus worker-final ingest durable recovery addendum: Lane
`RECOVERY-P1-CONTROL-EVENT-BUS-WORKER-FINAL-INGEST-DURABLE-ARTIFACT`
recovered the previously uncommitted worker-final ingest slice onto durable
local branch
`codex/recovery-p1-control-event-bus-worker-final-ingest-durable-artifact-20260703`
for dispatch
`TD-AFS-V02-RECOVERY-P1-CONTROL-EVENT-BUS-WORKER-FINAL-INGEST-DURABLE-ARTIFACT-20260703-001`.
Source worktree was `/home/afs-ops/.codex/worktrees/f109/AgentFlowStudio`;
close state is
`control_event_bus_worker_final_ingest_durable_artifact_recovered`. This is
durable artifact recovery only, not evaluator pass or integration. No merge,
push/fetch/pull, source-sync, provider gate/call, archive daemon, Runtime,
Studio, OpenAPI, DOC2, COS, CompanyOS, server/deploy/restart, readiness,
human/business/public/legal claim, durable-memory promotion, or self-archive is
claimed. Post-closeout next action: run a fresh evaluator against the durable
branch. Handoff:
`docs/handoff/AFS-CONTROL-EVENT-BUS-WORKER-FINAL-INGEST-REDISPATCH-20260703.md`.

Control event bus worker-final ingest redispatch addendum: Lane
`SPEC-P1-CONTROL-EVENT-BUS-WORKER-FINAL-INGEST-REDISPATCH` produced a bounded
repo-local spec/test slice on
`codex/spec-p1-control-event-bus-worker-final-ingest-redispatch-20260703` for
dispatch
`TD-AFS-V02-SPEC-P1-CONTROL-EVENT-BUS-WORKER-FINAL-INGEST-REDISPATCH-20260703-001`.
Route basis is CTO disposition
`readback_accepted_reaffirm_parallel_architecture_redispatch`. The control
event register adapter now accepts `worker_final_ingested` events with canonical
TD/BU/event ids, bounded recovery sources `direct_thread_delivery`,
`local_final_only`, `legacy_bridge`, `pendingWorktreeId`, and
`worker_final_read`, exact-duplicate idempotency, conflicting duplicate TD/BU
rejection, materialization-failure coverage, no-ACK preservation, safe evidence
classification, and archive-after-ACK blocking. The superseded old
pendingWorktreeId
`remote-ssh-discovered:afs-bwg-ops:c1ce9c63-b0ec-4a5a-ad13-7a0309dfde2c`
is recorded as reconciliation evidence only and was not used, repaired, synced,
or archived. Verification available in this checkout passed `python3 -m py_compile`,
a focused no-pytest assertion script, contract fixture load, and
`git diff --check`; focused pytest is blocked because `/usr/bin/python3` has no
`pytest` module, and CLI help/version checks are blocked because
`/usr/bin/python3` has no `typer` module. No archive daemon,
destructive migration/archive daemon, full historical replay,
source sync/fetch/pull/push, Runtime/Studio/OpenAPI/DOC2/COS/CompanyOS/provider
or server/deploy/restart mutation, provider gate/call,
readiness/human/business/public/legal claim, durable-memory promotion,
self-archive, or merge is claimed. Handoff:
`docs/handoff/AFS-CONTROL-EVENT-BUS-WORKER-FINAL-INGEST-REDISPATCH-20260703.md`.

Runtime idempotent submit redispatch durable addendum: Lane
`IMP-P1-RUNTIME-IDEMPOTENT-SUBMIT-REDISPATCH-DURABLE` implemented a bounded
Runtime submit idempotency candidate on
`codex/runtime-idempotent-submit-redispatch-durable-20260703` for dispatch
`TD-AFS-V02-IMP-P1-RUNTIME-IDEMPOTENT-SUBMIT-REDISPATCH-DURABLE-20260703-001`.
Runtime keyframe, video, and generation-comparison submit routes now reserve a
project/action/stable-request-id ledger before job allocation or provider-capable
dispatch. Completed duplicate submits replay the same public response and job
identity; changed payloads with the same stable request id return 409
`idempotency_conflict` with `provider_calls_started=false`. Focused tests were
added in `tests/test_api_runtime_idempotent_submit.py`; available verification
passed `python3 -m py_compile` on touched Runtime/test modules and
`git diff --check`. Pytest and adjacent suites are blocked in this checkout
because there is no `.venv`, no `python` command, and `/usr/bin/python3` lacks
`pytest`, `pip`, `fastapi`, and `pydantic`. No provider gate was opened, no live
provider call, generated-media QA, server/deploy/restart, OpenAPI mutation,
CompanyOS/COS mutation, durable-memory promotion, human acceptance,
product/business/public/legal readiness, push, or merge is claimed. Handoff:
`docs/handoff/AFS-RUNTIME-IDEMPOTENT-SUBMIT-REDISPATCH-DURABLE-20260703.md`.

Control event log register adapter addendum: Lane
`IMP-P1-AFS-CONTROL-EVENT-LOG-REGISTER-ADAPTER` implemented a repo-local
active/pending control event adapter on
`codex/control-event-log-register-adapter-20260703`. The slice adds
`agentflow_control_event` JSONL helpers, `agentflow_control_register`
materialization, durable implementation artifact handle validation,
first-class claim-state events, non-claim separation, fixed role surfaces,
evidence source classification, no-ACK preservation, and archive-policy
evaluation before archive execution. It includes current active/pending sample
events and a checked register fixture. Verification available in this checkout
passed `python3 -m py_compile`, a no-pytest assertion script for
materializer/validator/registry behavior, and contract example enumeration.
Focused pytest is blocked because no `.venv`, `python`, or `pytest` executable
exists and `/usr/bin/python3` has no `pytest` module. CLI help/version checks
are blocked because `/usr/bin/python3` has no `typer` module. No thread archive
automation, historical replay, provider gate/call, Runtime/Studio/OpenAPI
mutation, server/deploy action, generated-media QA, human acceptance,
business/public/legal/product readiness, CompanyOS/COS promotion,
durable-memory promotion, push, or merge is claimed. Handoff:
`docs/handoff/AFS-CONTROL-EVENT-LOG-REGISTER-ADAPTER-20260703.md`.

P0 Runtime + Studio state recovery integration candidate addendum: Integration
branch `codex/p0-state-recovery-integration-20260703` was created from
baseline/reference `dd027f72173a5a14ebd2f52a7ab587e1cecb6d4f` in
`/home/afs-ops/.codex/worktrees/14b4/AgentFlowStudio`. The worker integrated
only the accepted Runtime recovery candidate from worktree `2bb8` and the
accepted Studio gate/status recovery candidate from worktree `6775`, leaving
both source worktrees read-only. Final candidate adds the Runtime
`runtime_recovery` envelope and safe manifest recovery fields, Studio status and
retry-failed-items surfaces, direct Studio consumption of `runtime_recovery`
status/preserved outputs/safe artifact pointers, safe repeated async keyframe
terminal poll reconstruction without public provider-output echo, and
cross-platform safe image upload filename sanitization. Verification passed:
py_compile on touched Runtime/tests, Studio JS `138 files`, focused
Runtime/Studio recovery pytest `53 passed`, mocked Playwright job-center
recovery checks at `390x820` and `1366x900`, maintenance audit `failed=0`
warning-only, and `git diff --check`. Full non-legacy pytest was run; after
in-scope fixes, residual blockers are the absent external
`D:/.../10-Startup/.../knowledgebase` path and OpenAPI `ValidationError` schema
drift from the temporary latest dependency environment. No provider gate opened,
no live provider call, no generated-media QA, no server/deploy/restart, no
push/merge, no runtime loaded-code freshness, no human acceptance, no product or
business readiness, and no CompanyOS/COS or durable-memory promotion is claimed.
Handoff:
`docs/handoff/AFS-P0-STATE-RECOVERY-INTEGRATION-CANDIDATE-20260703.md`.

Runtime state/artifact recovery addendum: Lane
`IMP-P0-RUNTIME-STATE-ARTIFACT-RECOVERY` implemented a Runtime-side recovery
contract on `codex/runtime-state-artifact-recovery-20260703` for dispatch
`TD-AFS-V02-IMP-RUNTIME-STATE-ARTIFACT-RECOVERY-20260703-001`. Runtime now has
a shared safe recovery envelope for keyframe/image, multi-image comparison, and
video responses, carrying accepted public batch states, stage, provider gate,
`provider_calls_started`, safe artifact pointers, provenance, retry metadata,
and non-claim review copy. Keyframe partial provider results preserve and
register valid generated image assets while failed/missing items remain visible
and retryable; async keyframe poll recovery preserves valid outputs from
failed/blocked provider payloads. Mixed multi-image comparison arms now surface
`partially_complete` and no longer expose relative `image_ref` paths. Video
no-output completion no longer creates fake MP4 placeholders outside fake/fixture
providers and surfaces `needs_attention` with safe retry metadata. Verification
available in this shell passed `python3 -m py_compile` on touched Runtime/tests,
`git diff --check`, and helper line count `291`. Focused pytest is still pending
because this checkout has no `python` command and `/usr/bin/python3` lacks the
`pytest` module. No provider gate was opened; no live provider submit/poll,
generated-media QA, server/deploy/restart, Runtime loaded-code freshness,
human acceptance, product/business/public/legal readiness, CompanyOS/COS
promotion, or durable-memory promotion is claimed. Handoff:
`docs/handoff/AFS-RUNTIME-STATE-ARTIFACT-RECOVERY-20260703.md`.

Runtime async poll safe-manifest fixback addendum: Lane
`FIX-P0-RUNTIME-ASYNC-POLL-SAFE-MANIFEST-SANITIZE` removed the verifier-found
public async keyframe poll leak where `safe_manifest.outputs` echoed normalized
provider outputs and provider `image_path` became `image_ref`. The async poll
public response now preserves reviewable partial artifacts only through safe
candidate preview and `runtime_recovery` pointers; provider-output internals and
run-local media refs are not echoed through the public safe manifest. A focused
async submit-plus-poll regression was added to assert public poll JSON excludes
`image_candidates/`, `image_ref`, `image_path`, `output_dir`, `request.json`,
and handoff-job internals while keeping retry scope on failed/missing items.
Available local verification passed `python3 -m py_compile` on the touched
Runtime/test modules and `git diff --check`; pytest remains pending because
`/usr/bin/python3` has no `pytest` module in this checkout. No live provider,
Studio, deploy/restart, merge/push, generated-media QA, human acceptance,
product/commercial/public/legal readiness, CompanyOS/COS promotion, or durable
memory promotion is claimed.

I2 hardening integration execution addendum: I2 fast-forwarded evaluator-passed
I1 branch `codex/afs-pre-human-hardening-integration-20260702` into local
`master` and pushed `origin/master` from
`f00fbc6c1404a4c3b812056a0f142626edb75ea8` to
`eebb9180810825d286a736cabba854512bfff466`. Pre-push verification on I1 and
post-push verification on integrated `master` both passed OpenAPI snapshot
(`1 passed`), Studio JS (`135 files`), full pytest (`892 passed, 520
deselected, 2 warnings`), maintenance audit (`failed=0`, warning-only), and
`git diff --check`. Server `/home/afs-ops/AgentFlowStudio` and
`/opt/afs/AgentFlowStudio` were fast-forwarded to the pushed integration hash
with ancestry-safe commands and no reset/clean; `/home` ops-local untracked docs
were preserved. Service-control is blocked because `sudo -n true` requires a
password, so `afs-runtime.service` was not restarted/reloaded; local/public
`/health` returned `status=ready`, but runtime loaded-code freshness is not
claimed. Provider smoke was not rerun; E1 remains pre-integration external route
smoke evidence only. This is origin integration plus server hash sync evidence,
not generated-media QA, human creative acceptance, product readiness,
business/public/legal readiness, CompanyOS projection, durable-memory promotion,
COS active-rule promotion, or runtime loaded-code freshness. Handoff:
`docs/handoff/AFS-I2-HARDENING-INTEGRATION-MERGE-SERVER-SYNC-20260702.md`.

Pre-human creative hardening integration addendum: Lane I1 integrated D2, D5,
D1/D1R, D3/D3R, and D4 on isolated branch
`codex/afs-pre-human-hardening-integration-20260702` from verified
`origin/master=f00fbc6c1404a4c3b812056a0f142626edb75ea8`. Integration preserved
accepted-plan non-acceptance boundaries, provider-submit preflight requirements,
scoped runtime readiness wording, runtime log/artifact leakage hardening, and
provider-closed readiness packet currency. D3 compatibility was handled by not
adding an alias for the retired runtime freshness field; active consumers now use
`runtime_three_end_alignment_evidence` and
`runtime_loaded_code_freshness_claim: "not_claimed"`, with no active retired
field references found. Stale deterministic tests were updated to either keep
provider gates closed or run fresh preflight before fake-provider submit.
Verification passed: focused union (`194 passed, 1 warning`), OpenAPI snapshot
(`1 passed` after export), Studio JS (`135 files`), full pytest (`892 passed,
520 deselected, 2 warnings`), maintenance audit (`failed=0`, warning-only), and
`git diff --check`. This is local integration readiness for evaluator review,
not provider smoke, generated-media QA, human creative acceptance, product
readiness, business/public/legal readiness, deploy/runtime loaded-code
freshness, CompanyOS projection, durable-memory promotion, or COS active-rule
promotion. Handoff:
`docs/handoff/AFS-PRE-HUMAN-CREATIVE-HARDENING-INTEGRATION-20260702.md`.

Runtime log/artifact leakage hardening addendum: Lane D4 hardens PB-P1-10 /
PB-P1-11 surfaces without provider calls or server operations. Runtime logging
now uses a shared sensitive-key/private-fragment sanitizer for client events,
request/audit/business logs, and file logs. Nested sensitive keys, prompt
fragments, local/private paths, signed/remote URLs, raw payloads, and media
bytes are omitted or redacted from durable logs. `/studio/client-events` also no
longer crashes when a client payload includes its own `event_type`. Runtime
artifact reads now use path/index-derived project ownership for artifacts under
`projects/`, `runs/`, and `feedback/`, enforcing auth-scoped cross-project
access while preserving auth-disabled local artifact reads. Focused red/green
evidence passed (`3 failed, 1 passed` before implementation; then `4 passed`);
adjacent Runtime/Auth/Media/Logging tests passed (`29 passed`); full pytest
passed (`871 passed, 520 deselected, 2 warnings`); `git diff --check` passed.
This is deterministic leakage-hardening evidence only, not provider smoke,
generated-media QA, human creative acceptance, Runtime loaded-code freshness,
product/business/public/legal readiness, server/deploy health, CompanyOS
projection, durable-memory promotion, or COS active-rule promotion. Handoff:
`docs/handoff/AFS-RUNTIME-LOG-ARTIFACT-LEAKAGE-HARDENING-20260702.md`.

D5 provider-closed readiness packet currency addendum: Lane D5 updates the
provider-closed internal tryout/readiness packet path on top of D2 commit
`654002a295330c0722102d8a2202804189865235`. The readiness browser QA now opens
the Studio accepted generation plan modal and records default blocked preview
evidence (`preview_status=blocked`, `job.status=blocked`, `accepted=false`,
`source_mode=fixture_demo`, `provider_calls_started=false`,
`provider_gate=closed`). The delivery readiness gate now requires
`accepted_generation_plan_default_blocked_preview`; the tryout packet carries an
`accepted_generation_plan_bridge` section with preview artifact/job refs and
fails closed if the accepted-plan evidence claims product readiness,
deploy/runtime health, provider smoke, generated-media QA, human creative
acceptance, business validation, public/legal/patent readiness, or COS
promotion. Focused packet/browser tests passed (`21 passed, 1 warning`), real
browser QA passed and wrote ignored local evidence under `runs\d5_*`, packet
generation passed, combined accepted-plan/static/packet/browser tests passed
(`36 passed, 1 warning`), Studio JS passed (`135 files`), and `git diff
--check` passed. Maintenance audit reported `failed=0` with warning-only
categories. This is provider-closed structure/readiness evidence only, not
provider smoke, generated-media QA, human creative acceptance, product
readiness, business validation, deploy/runtime freshness, CompanyOS/COS
promotion, durable-memory promotion, or final integration. Handoff:
`docs/handoff/AFS-D5-PROVIDER-CLOSED-READINESS-PACKET-CURRENCY-20260702.md`.

D2 accepted generation plan evidence hardening addendum: Lane D2 converts the
accepted-generation-plan preview from fixture acceptance simulation into a
local step-gate evidence path. Runtime preview now accepts optional
`source_artifact_id` and `source_human_gate_id`; `accepted=true` is possible
only for a safe project-scoped plan packet whose evidence origin is not
`repo_local_fixture` and whose source artifact is targeted by a manifest-linked
`accepted_generation_plan_packet` human-gate decision. Bundled fixture modes,
including `confirmed_local_fixture`, remain non-acceptance demo evidence and
return blocked workflow state (`job.status=blocked`, `preview_status=blocked`,
manifest status `blocked`). Runtime writes safe `accepted_generation_plan_refs`
into the project manifest for evaluator/operator recovery. Studio now labels
the fixture control as `Fixture demo (blocked)` and reserves accepted copy for
project artifact step-gate evidence. Focused Runtime/human-gate tests passed
(`9 passed, 1 warning`), Studio static tests passed (`5 passed`), OpenAPI
snapshot was regenerated and the final combined guard passed (`16 passed, 1
warning`), Studio JS passed (`135 files`), final Runtime/OpenAPI focus passed
(`11 passed, 1 warning`), and `git diff --check` passed. This is
provider-closed plan-review/local
step-gate evidence only, not provider smoke, generated-media QA, human creative
acceptance, product readiness, business validation, deploy/runtime freshness,
CompanyOS/COS promotion, durable-memory promotion, or final integration.
Handoff:
`docs/handoff/AFS-D2-ACCEPTED-GENERATION-PLAN-HARDENING-20260702.md`.

Accepted generation plan Runtime/Studio bridge addendum: Lane C adds a
provider-closed Runtime/Studio review bridge for the T58
`accepted_generation_plan_packet` capability. Runtime now exposes
`POST /projects/{project_id}/accepted-generation-plan-packets/preview`, writes a
safe preview artifact and run trace, and keeps the default `default_unconfirmed`
package blocked with `packet_state=blocked_pending_generation_plan_prerequisites`
and `accepted=false`. Surfacing
`packet_state=accepted_local_generation_plan_packet` requires explicit
`fixture_mode=confirmed_local_fixture` and local fixed-asset/residual-closure
contract conditions. Studio adds only a minimal dock-opened review modal and
Runtime client method; it loads the blocked default first and shows state,
provenance, residual blockers, residual closure refs, and explicit non-claim
boundaries. Focused red/green API evidence passed (`3 failed` with 404 before
implementation, then `3 passed`); combined API/Studio static tests passed (`5
passed, 1 warning`); OpenAPI snapshot passed after regeneration (`1 passed`);
Studio JS passed (`135 files`); impacted T58/T57/T56/T55/T54/T53/T52/algorithm
contract bundle passed (`75 passed, 1 warning`); Runtime service tests passed
(`12 passed, 1 warning`); `git diff --check` passed. This is Runtime/Studio
plan-review evidence only, not provider smoke, live provider calls, generated
media, generated-media QA, human creative acceptance, business validation,
product readiness, server/deploy/runtime health, CompanyOS projection,
durable-memory promotion, or COS active-rule promotion. Handoff:
`docs/handoff/AFS-ACCEPTED-GENERATION-PLAN-RUNTIME-STUDIO-BRIDGE-20260702.md`.

Professional Prompt Optimization deterministic hardening addendum: real Chinese
image/keyframe/video prompts now enter a provider-closed professional visual
contract path before prompt assembly. The new helper extracts actual CJK
subject, emotion, scene, action, and motion semantics for prompts such as
`女生在笑`, `女生微笑`, `雨夜街道，紧张`, `让她慢慢回头微笑`, and `开心`.
Optimized image/keyframe prompts now include subject identity, restrained
realistic expression cues, expression decomposition before action, body/action
carrier, scene grounding, light/camera details, continuity, and negative
constraints. Optimized video prompts now include start state, transition,
movement/body carrier, camera/environment motion, end state, duration/beat
language, and first-frame/source continuity when available; image-to-video
optimization focuses on motion-first continuation rather than restating the
whole upstream image. Focused red/green semantic tests passed (`5 failed` before
implementation, then `5 passed`); impacted prompt optimizer/API contract tests
passed (`81 passed`); full pytest passed (`862 passed, 520 deselected, 2
warnings`). Studio JS was not touched. This is deterministic prompt-contract
verification only, not provider smoke, generated-media quality, human creative
acceptance, business validation, deploy/runtime health, CompanyOS projection,
durable-memory promotion, or COS active-rule promotion. Handoff:
`docs/handoff/AFS-PROFESSIONAL-PROMPT-OPTIMIZATION-DETERMINISTIC-HARDENING-20260702.md`.


Video node duration/provenance idempotence revision addendum: this revision
patches the evaluator-blocking follow-up on top of commit `2f96939c`. Studio
first-frame provenance is now idempotent across repeated
`ensureVideoFirstFrameAsset()` and `videoInputSourceForRequest()` calls:
generic upload `source_node_id` / `source_job_id` no longer imply keyframe
provenance, direct uploads remain `uploaded_image`, upstream uploaded images
remain `upstream_uploaded_image`, and explicit keyframe/generated indicators
still preserve `upstream_generated_image` with the original keyframe node/job
ids. Studio video duration choices now cover all one-second modes from `1s`
through `15s`; backend/provider duration guards remain unchanged. Focused
red/green tests reproduced the direct-upload/upstream-upload flips and the
four-option duration surface before the patch, then passed after the patch
(`24 passed`). Required verification passed: Studio JS check (`134 files`),
impacted bundle (`64 passed, 1 warning`), full pytest (`857 passed, 520
deselected, 2 warnings`), maintenance audit (`failed=0`, warning-only
categories), and `git diff --check`. OpenAPI was not touched. This is
deterministic Studio/request contract verification only, not provider smoke,
generated-media quality, human creative acceptance, business validation, deploy
or Runtime health verification, CompanyOS projection, durable-memory promotion,
or COS active-rule promotion. Handoff:
`docs/handoff/AFS-VIDEO-NODE-DURATION-PROVENANCE-IDEMPOTENCE-REVISION-20260702.md`.


Video node keyframe provenance revision addendum: resolved the evaluator-blocking
keyframe-continuation provenance gap on
`codex/afs-video-node-keyframe-provenance-revision-20260702` from
`87cbe3247261d819e3752e0e5a18cf96223d03e4`. Keyframe-created video nodes now
persist `videoInputSource.source_mode=upstream_generated_image` with the
original keyframe node id, first-frame asset id, and keyframe job id.
`ensureVideoFirstFrameAsset()` no longer downgrades that continuation path to
`explicit_first_frame_selection` when a first-frame id already exists. The
backend Studio-state sanitizer now allowlists and narrowly sanitizes
`videoInputSource` so save/reload preserves the source model. Detached-base
reproduction failed with the evaluator symptom. Focused regression/persistence
checks passed (`3 passed`); required Studio/video/frontend bundle passed (`52
passed`); full pytest passed (`856 passed, 520 deselected, 2 warnings`).
Maintenance audit reported `failed=0` with warning-only existing categories,
and `git diff --check` passed.
This is deterministic provenance/request/state evidence only, not provider
smoke, generated-media quality, human creative acceptance, business validation,
deploy/runtime health, CompanyOS projection, durable-memory promotion, or COS
active-rule promotion. Handoff:
`docs/handoff/AFS-VIDEO-NODE-KEYFRAME-PROVENANCE-REVISION-20260702.md`.

Video node deterministic slice recovery addendum: recovered an inspectable
provider-closed video-node contract on
`codex/afs-video-node-deterministic-slice-recovery-20260702` from baseline
`38c7cf5ef08b6d84217ef145129c4592866d8b49`. Studio now preserves explicit
first-frame input-source state for direct video-node uploads, upstream
uploaded-image nodes, upstream generated-image/keyframe nodes, fixed visual
asset references, and explicit first-frame selection. Runtime now carries
`input_source`, `input_mode`, and a 1-15 second `duration_contract` through
preflight, model-call context, provider-neutral request plan, safe manifest,
and task state. Closed video gates return deterministic planning artifacts
without provider calls; gate-open provider-specific unsupported duration and
input-mode paths reject with structured errors before provider submit. Focused
red/green evidence passed (`8 failed, 1 passed` expected red; then `10
passed`); required video/adapter/frontend focused tests passed (`50 passed`);
OpenAPI snapshot passed (`1 passed`); full pytest passed (`854 passed, 520
deselected, 2 warnings`); maintenance audit reported `failed=0` with
warning-only existing categories; `git diff --check` passed. This is
deterministic request-planning and validation evidence only, not provider smoke,
generated-media quality, human creative acceptance, business validation,
deploy/runtime health, CompanyOS projection, durable-memory promotion, or COS
active-rule promotion. Handoff:
`docs/handoff/AFS-VIDEO-NODE-DETERMINISTIC-SLICE-RECOVERY-20260702.md`.

SPEC2 accepted generation plan assembly contract addendum: T58 adds the next
deterministic `branch_workflow_package` report section,
`accepted_generation_plan_packet`. The default T57 package remains blocked
because branch-specific fixed-asset confirmation and residual-question closure
evidence are incomplete. An explicitly confirmed repo-local fixture mutation
can now assemble `packet_state=accepted_local_generation_plan_packet` with
fixed asset refs, residual closure refs, evidence refs, owner/reviewer/close
condition refs, review state, non-claim boundaries, and provider-closed
generation-request planning fields. The packet is structure evidence only and
keeps provider calls, generated media, graph writes, Runtime/OpenAPI/Studio,
reader playback, storage lifecycle, human acceptance, business validation,
final schema acceptance, product readiness, deploy/runtime health, CompanyOS
projection, durable-memory promotion, and COS active-rule promotion as
non-claims. Focused red/green pytest passed (`2 failed, 1 passed` expected red;
then `3 passed`); branch workflow contract tests passed (`37 passed`);
impacted T58/T57/T56/T55/T54/T53/T52/algorithm contract tests passed
(`69 passed`). Maintenance audit reported `failed=0` with warning-only
categories, including the current-scope `_validator.py` 311-line oversized
warning; `git diff --check` passed.
Handoff:
`docs/handoff/AFS-T58-SPEC2-ACCEPTED-GENERATION-PLAN-ASSEMBLY-CONTRACT-20260702.md`.

SPEC2 fixed-asset confirmation evidence contract integration addendum: T57 was
integrated into `master` from evaluated worktree
`C:\Users\chenzy\.codex\worktrees\5e58\AgentFlowStudio` on top of docs-cleanup
commit `7823a86c972b238227da50d3009b24ef9bfcd0ba`. The integration replayed
only the scoped `branch_workflow_package` confirmation-evidence algorithm,
fixture, focused/contract tests, T57 handoff, and handoff-index delta, while
merging `DEVLOG.md` and this tracker deliberately above the C2 docs-cleanup
records. The new deterministic contract adds `fixed_asset_confirmation_evidence`
and residual-question closure evidence: the shared map fixed asset is confirmed
by default, while branch-specific assets remain visible as unconfirmed
candidates and cannot become implementation-ready or generation-planning
eligible without repo-local confirmation records, fixed asset source refs,
confirmation source refs, owner/reviewer decision refs, close-condition refs,
protected non-claim refs, provider prompt closure, and graph-write closure.
Residual questions cannot be closed without target refs, evidence refs,
owner/reviewer decision refs, and a non-claim-preserving close condition.
Focused integration pytest passed (`16 passed`); branch workflow contract tests
passed (`34 passed`); impacted T57/T56/T55/T54/T53/T52/algorithm contract tests
passed (`66 passed`); full pytest passed (`841 passed, 520 deselected, 2
warnings`). Maintenance audit reported `failed=0` with warning-only categories,
including the current-scope T57 focused test oversized warning. This is
deterministic confirmation/closure evidence only, not final schema acceptance,
product readiness, Runtime/OpenAPI/Studio readiness, provider smoke,
generated-media quality, human creative acceptance, business validation,
public/legal/patent decision, deploy/runtime health, CompanyOS projection,
durable-memory promotion, or COS active-rule promotion.
Handoff:
`docs/handoff/AFS-T57-SPEC2-FIXED-ASSET-CONFIRMATION-EVIDENCE-CONTRACT-20260702.md`.

Docs low-value deletion cleanup addendum: The C2 docs cleanup on
`codex/afs-docs-low-value-deletion-cleanup-20260702` deleted the 20 C1 archive
copies under `docs/archive/handoff/` and `docs/archive/maintenance/`. Those
files had already been removed from active `docs/handoff/` and
`docs/maintenance/`, had no current index route, and were referenced only by
the archive summary / cleanup ledger and DEVLOG. Current recovery route:
`git restore --source=61b5b8b9d98577df1d2b7c0c273f32869ffb8518 -- docs/archive/handoff docs/archive/maintenance`.
This is docs noise reduction only, not product readiness, provider smoke,
Runtime/Studio verification, generated-media validation, server/deploy health,
CompanyOS projection, durable-memory promotion, or COS active-rule promotion.

SPEC2 generation-planning evidence gate addendum: T56 extends the T55-hardened
`branch_workflow_package` contract with a deterministic
`generation_planning_candidate` report section. The new gate accepts only
repo-local fixture evidence; integration narrowed the accepted evidence-origin
set to the literal `repo_local_fixture` value. It preserves shared versus
branch-specific asset policy, keeps confirmed and unconfirmed candidate assets
separate, rejects
non-local evidence origins, and requires implementation-ready asset evidence,
generation-planning review acceptance, no unresolved open questions,
residual-boundary allowance, and protected non-claim preservation before the
candidate becomes eligible. The default T54/T55 fixture remains blocked because
branch-specific assets are unconfirmed and PB3/T54 residual questions still
block `accepted_for_generation_planning`; the reported candidate is structure
evidence only, not provider, product, Runtime, Studio, or human-acceptance
readiness. Focused red/green pytest passed (`3 failed, 18 passed` expected red;
then `21 passed`); impacted T56/T55/T54/T53/T52/algorithm contract tests passed
(`53 passed`). Maintenance audit reported `failed=0` with existing warning-only
categories, and `git diff --check` passed. This is deterministic
generation-planning evidence gating only, not final schema acceptance, product
readiness, Runtime/OpenAPI/Studio readiness, provider smoke, generated-media
quality, human creative acceptance, business validation, public/legal/patent
decision, deploy/runtime health, CompanyOS projection, durable-memory
promotion, or COS active-rule promotion.
Handoff:
`docs/handoff/AFS-T56-SPEC2-GENERATION-PLANNING-EVIDENCE-GATE-20260702.md`.

SPEC2 review-status residual-boundary hardening addendum: T55 integrates a
deterministic hardening layer for the T54 `branch_workflow_package` contract
after rebasing onto current `origin/master` at `f15b47db`. The new
`_review_status` validator requires structured review open questions, non-empty
target/evidence refs, owner/next-action/close-condition routing, and a structured
`residual_boundary` envelope. Unresolved residuals now remain review-only,
block `accepted_for_generation_planning`, keep implementation-ready evidence
incomplete, and expose blocked stages plus unresolved question refs in the
validation report. Focused post-rebase pytest passed (`18 passed`); impacted
T55/T54/T53/T52/algorithm contract tests passed (`50 passed`). Integration
gates passed: maintenance audit `failed=0`, full pytest `825 passed, 520
deselected, 2 warnings`, and `git diff --check` passed. This is deterministic
residual-boundary validation only, not final schema acceptance, product
readiness, Runtime/OpenAPI/Studio readiness, provider smoke, generated-media
quality, human creative acceptance, business validation, public/legal/patent
decision, deploy/runtime health, CompanyOS projection, durable-memory
promotion, or COS active-rule promotion.
Handoff:
`docs/handoff/AFS-T55-SPEC2-REVIEW-STATUS-RESIDUAL-BOUNDARY-HARDENING-20260702.md`.

SPEC2 branch workflow package contract addendum: T54 adds the deterministic
`branch_workflow_package` wrapper contract on top of T53 rather than
duplicating the T53 branch package validator. The new algorithm validates a
SPEC2 package object with choice point, branch path, branch shot, asset need,
continuity constraint, evidence requirement, review status, and handoff
envelope fields. It cross-checks the T53 fixture as source evidence, preserves
shared versus branch-specific asset scopes, excludes unconfirmed candidates
from implementation-ready evidence, keeps review-ready evidence separate from
accepted-for-generation evidence, rejects unsafe markers, preserves protected
non-claims, and keeps Production Graph usage reference-only with no graph node
writes. PB3 commit `8296afa31b639224bcb3e7c1f8dea70000ea00b4` remains
`review_pending_local_package`, and PB3 SPEC plus Stage0/Stage1 evaluator
outcomes remain `pass_with_residual_risk` boundaries only. Focused red/green
pytest passed (`9 passed` after the expected missing-module red); impacted
T54/T53/T52/algorithm contract tests passed (`41 passed`). Maintenance audit
reported `failed=0` with warning-only categories, including the new English T54
handoff under human_doc_chinese_coverage, and `git diff --check` passed. This
is deterministic branch workflow package readiness
verification only, not final schema acceptance, product readiness,
Runtime/OpenAPI/Studio readiness, provider smoke, generated-media quality,
human creative acceptance, business validation, public/legal/patent decision,
deploy/runtime health, CompanyOS projection, durable-memory promotion, or COS
active-rule promotion.
Handoff:
`docs/handoff/AFS-T54-SPEC2-BRANCH-WORKFLOW-PACKAGE-CONTRACT-20260702.md`.

Interactive Manga branch package contract addendum: T53 adds the deterministic
Stage 2 branch package fixture before reader/provider/Social Square/Director
Console work. The new `interactive_manga_branch_package` algorithm validates a
repo-local fixture with one choice point, two branch paths, four branch shots,
base storyboard/shot mappings plus branch-specific shot refs, shared and
branch-specific asset needs, shared and branch-specific continuity constraints,
evidence mappings to storyboard refs, Production Graph artifact refs, asset
refs, evidence refs, and handoff envelope refs, without graph node writes.
Unsafe markers fail closed and protected non-claims remain false, including
provider prompt inclusion, reader playback, Runtime route, Studio UI, OpenAPI
path, generated media, human creative acceptance, business validation, deploy
runtime health, CompanyOS projection, final schema acceptance, and product
readiness. Focused red/green pytest passed (`9 passed` after the expected
missing-module red); impacted T53/T52/algorithm contract tests passed
(`32 passed`). Maintenance audit reported `failed=0` with warning-only
existing categories, and `git diff --check` passed. This is deterministic
branch package structure verification only, not final schema acceptance,
product readiness, Runtime/OpenAPI/Studio readiness, provider smoke,
generated-media quality, human creative acceptance, business validation,
public/legal/patent decision, deploy/runtime health, CompanyOS projection,
durable-memory promotion, or COS active-rule promotion.
Handoff:
`docs/handoff/AFS-T53-INTERACTIVE-MANGA-BRANCH-PACKAGE-CONTRACT-20260701.md`.

Shared object evidence fixture addendum: T52 adds a deterministic local
contract fixture before Interactive Manga, Social Square, or Director Console
expansion. The new `shared_object_evidence` algorithm validates a repo-local
fixture for canonical refs, object counts, unresolved refs, Production Graph
node/reference separation, unsafe-marker rejection, evidence-gap reasons,
handoff envelope completeness, fixed-asset source evidence, reuse scope, and
protected non-claims. The Stage1 evaluator system-error residual is carried as
`stage1_evaluator_system_error_residual`, not erased or upgraded into acceptance.
Focused red/green pytest passed (`8 passed` after the expected missing-module
red), impacted algorithm/graph/ledger tests passed (`36 passed, 1 warning`).
Maintenance audit reported `failed=0` with warning-only existing categories,
and `git diff --check` passed.
This is deterministic structure verification only, not final schema acceptance,
Runtime/OpenAPI/Studio readiness, provider smoke, generated-media quality,
human creative acceptance, business validation, public/legal/patent decision,
deploy/runtime health, CompanyOS projection, or COS active-rule promotion.
Handoff:
`docs/handoff/AFS-T52-SHARED-OBJECT-EVIDENCE-FIXTURE-20260701.md`.

Provider-closed internal tryout packet addendum: T51 adds a deterministic
packet builder for the T50 Studio/Runtime browser readiness report. The packet
requires `delivery_readiness.verdict=internal_provider_closed_tryout_ready`,
fails closed on any `provider_calls_started=true` signal, preserves explicit
non-claims for provider smoke, generated-media quality, human creative
acceptance, business validation, public/legal/patent approval, deploy/runtime
health, and COS active-rule promotion, and writes JSON plus optional Markdown
evidence under `runs/`. The evaluator revision makes the `/studio-state`
`409 Conflict` filter recovery-aware: only a conflict paired with persisted
saved keyframe/feedback evidence may be suppressed, while unrecovered
`/studio-state` conflicts, unrelated `409` responses, and non-recovered
console/network failures remain actionable. Focused pytest passed
(`17 passed, 1 warning`), browser readiness evidence passed with
`provider_calls_started=false`, and the packet builder passed with
`provider_calls_started=false`. This records no environment-level provider gate
state claim. Project gates passed:
`tools/maintenance_audit.py` reported `failed=0`, and `git diff --check`
passed with line-ending normalization warnings only. This is an internal
provider-closed tryout packet only, not provider smoke, live provider call,
generated media, human creative acceptance, business validation, public claim,
patent/legal decision, external download, deploy verification, Runtime health
verification, or COS active-rule promotion. Handoff:
`docs/handoff/AFS-T51-PROVIDER-CLOSED-INTERNAL-TRYOUT-PACKET-20260701.md`.

Studio main-path delivery readiness addendum: T50 adds a provider-closed
internal delivery readiness gate for the Studio/Runtime main path. The browser
QA harness now seeds the real `multi_role_prop_exchange_chase` benchmark and
emits `delivery_readiness.verdict=internal_provider_closed_tryout_ready` only
when storyboard/content-quality, asset-card candidate/fixed-asset path,
Production Graph fixed-asset reuse, keyframe request/preflight/blocked bridge,
feedback overlay, and provider-closed browser/runtime checks pass. Focused
pytest passed (`9 passed, 1 warning`), impacted Runtime/Studio tests passed
(`20 passed, 1 warning`), Studio JS passed (`134 files`), browser readiness
harness passed with `provider_calls_started=false`, maintenance audit had
`failed=0`, and `git diff --check` passed. Product readiness is limited to
internal provider-closed tryout as structure-verified workflow evidence; human
creative acceptance, provider smoke, generated-media quality, business
validation, public/legal/patent decisions, deploy/runtime health, and COS
active-rule promotion remain separate gates. Handoff:
`docs/handoff/AFS-STUDIO-MAIN-PATH-DELIVERY-READINESS-GATE-20260701.md`.

Content-quality benchmark expansion addendum: T49 adds a provider-closed
real-script benchmark, `multi_role_prop_exchange_chase`, to cover a
three-character misunderstanding, restaurant/street/office scene transitions,
map and letter prop continuity, emotion shift, action continuity, and
six-beat narrative shot rhythm. The benchmark test now verifies asset-card
candidate continuity and Production Graph relationships, not only report-level
content-quality checks. Focused benchmark pytest passed (`1 passed`), impacted
storyboard/content-quality/runtime tests passed (`26 passed, 1 warning`),
maintenance audit had `failed=0`, and `git diff --check` passed. The benchmark
file remains under the 300-line ideal threshold at 297 lines. The AFS
Redundancy Maintenance Lane is now blocker-closed through fresh rebuild on
`codex/afs-redundancy-maintenance-ledger-rebuild-20260701` at `eb16cc3e`, with
owner review/push pending outside this T49 lane. This is deterministic
provider-closed benchmark/runtime structure evidence only, not provider smoke,
generated media, human creative acceptance, business validation, public claim,
patent/legal decision, external download, deploy verification, Runtime health
verification, or COS active-rule promotion. Handoff:
`docs/handoff/AFS-CONTENT-QUALITY-BENCHMARK-EXPANSION-20260701.md`.

Full pytest residual triage addendum: T48 resolves the T47 full pytest quality
debt without opening provider or expanding product/runtime surfaces. The
`.venv` basetemp maintenance failures were fixture isolation debt; the affected
maintenance-audit fixtures now initialize their own git repos. The
`runtime_root_persisted` failure was a hard-coded assertion against a
path-sensitive production helper; the test now asserts against
`runtime_root_is_persisted(tmp_path)`. The Codex local provider error test now
isolates `AFS_CODEX_HOME` under pytest tmp and disables bootstrap so workstation
`C:/Users/chenzy/.afs-codex` chmod state cannot mask the missing-CLI behavior.
Focused residual pytest passed (`4 passed, 1 warning`), full pytest passed
(`778 passed, 520 deselected, 2 warnings`), maintenance audit had `failed=0`,
and `git diff --check` passed. This is deterministic fixture/test
stabilization only, not provider smoke, generated media, human creative
acceptance, business validation, public claim, patent/legal decision, external
download, deploy verification, Runtime health verification, or COS active-rule
promotion. Handoff:
`docs/handoff/AFS-FULL-PYTEST-RESIDUAL-TRIAGE-20260701.md`.

Studio main-path browser QA addendum: T47 records the execution method as Agentic Loop Engineering; the project book, execution spec, task ledger, and state file are loop artifacts, while AFS remains the AI-native manga/video/image content production workbench. T47 verifies `/studio/` can carry the
Runtime main-loop evidence path without opening providers: real benchmark
storyboard seed -> asset card/fixed asset/human-gate evidence -> production
graph summary -> keyframe request plan and blocked bridge evidence -> feedback
overlay include decision -> second blocked keyframe bridge. A small Runtime
state sanitizer fix preserves safe production graph/source-evidence/non-claim
fields while pruning unsafe runtime trace payloads. Browser QA passed with
`provider_calls_started=false`, `console_error_count=0`, and
`response_error_count=0`; Studio JS passed (`134 files`); focused related pytest
passed (`18 passed, 1 warning`); maintenance audit had `failed=0`; `git diff
--check` and execution YAML parsing passed. Cleanup note: generated
`.tmp/pytest-t47-*` basetemp remains local cleanup pending after Windows access
denial; it is not staged and follow-up verification used ignored `.venv`
basetemp. This is browser/runtime structure verification only, not provider
smoke, generated media, human creative acceptance, business validation, public
claim, patent/legal decision, external download, deploy verification, or COS
active-rule promotion. Handoff:
`docs/handoff/AFS-STUDIO-MAIN-PATH-BROWSER-QA-20260701.md`.

Main-loop E2E integration gate addendum: T46 rechecked the normal integration
gate for `codex/afs-goal-mode-main-loop-e2e-20260630` and fast-forwarded the
coherent provider-closed T41-T45 evidence package into `master`. Premerge branch
review passed with `blocker_count=0` and `merge_review_threshold_reached=false`;
full pytest passed (`773 passed, 520 deselected, 2 warnings`); maintenance audit
had `failed=0`; `git diff --check` passed; and the execution YAML files parsed.
Local `master`, `origin/master`, server `/home/afs-ops/AgentFlowStudio`, and
server `/opt/afs/AgentFlowStudio` were fast-forwarded to `72c698ac` without
reset/clean. Runtime health returned `status=ready`. This is runtime/structure
verification only, not provider smoke, live provider call, generated media,
human creative acceptance, business validation, public claim, patent/legal
decision, or COS active-rule promotion. Handoff:
`docs/handoff/AFS-MAIN-LOOP-E2E-INTEGRATION-GATE-20260630.md`.

Multi-shot request-plan bridge consistency addendum: T45 adds a narrow
provider-closed consistency regression to the real
`multi_character_restaurant_note` path. The test now reads the
`keyframe_request_plan` artifact and verifies its context bundle carries the
same two fixed asset ids, source asset-card candidate ids, and feedback overlay
id that appear in blocked keyframe bridge evidence. Focused test passed
(`1 passed, 1 warning`), adjacent bridge set passed (`5 passed, 1 warning`),
and full pytest passed (`773 passed, 520 deselected, 2 warnings`). Maintenance
audit stayed green for blocking failures (`failed=0`) and `git diff --check`
passed. No Runtime route, OpenAPI path, Studio UI, provider call, generated
media, human creative acceptance, business validation, public claim,
patent/legal decision, or COS active-rule promotion occurred. Handoff:
`docs/handoff/AFS-MULTI-SHOT-REQUEST-PLAN-BRIDGE-CONSISTENCY-20260630.md`.

Main-loop E2E redundancy cleanup addendum: T44 classified the current T41-T43
branch redundancy and reduced the duplicated test-support surface instead of
adding a new record-heavy feature slice. The multi-character bridge regression
now reuses shared parameterized storyboard, feedback overlay, and keyframe
preflight helpers; the shared support file is 299 lines and the multi-character
test is 178 lines. Focused E2E passed (`3 passed, 1 warning`), adjacent bridge
set passed (`5 passed, 1 warning`), and full pytest passed
(`773 passed, 520 deselected, 2 warnings`). Maintenance audit stayed green for
blocking failures (`failed=0`) and `git diff --check` passed. No Runtime route,
OpenAPI path, Studio UI, provider call, generated media, human creative
acceptance, business validation, public claim, patent/legal decision, or COS
active-rule promotion occurred. Handoff:
`docs/handoff/AFS-MAIN-LOOP-E2E-REDUNDANCY-CLEANUP-20260630.md`.

Multi-character bridge regression addendum: the next provider-closed slice adds
a second real benchmark regression using `multi_character_restaurant_note`. It
promotes two fixed character assets (`周岚` and `陈默`), runs the real
storyboard/content-quality path, records a local feedback overlay, and submits a
keyframe request that carries both fixed assets into blocked keyframe bridge
evidence. The bridge now proves two source-evidence refs reach
`context_evidence` while `provider_calls_started=false`, the image gate remains
blocked, no candidate previews or reusable generated image assets are returned,
and feedback overlay prompt inclusion remains blocked by default. Full pytest
passed (`773 passed, 520 deselected, 2 warnings`). No Runtime route, OpenAPI
path, Studio UI, provider call, generated media, human creative acceptance,
business validation, public claim, patent/legal decision, or COS active-rule
promotion occurred. Handoff:
`docs/handoff/AFS-MULTI-CHARACTER-KEYFRAME-BRIDGE-REGRESSION-20260630.md`.

Main-loop keyframe bridge evidence addendum: the next provider-closed slice
extends the real `multi_scene_map_chase` Runtime E2E harness from keyframe
preflight into blocked local keyframe generation bridge evidence. The bridge now
records safe fixed-asset source-evidence refs inside `context_evidence`, proving
the human-gate id, asset-card candidate id, fixed visual asset, feedback overlay,
and context bundle reached the generation bridge input while the image provider
gate remained blocked. The red/green loop first failed on missing
`included_asset_source_evidence_refs`, then passed after the bridge carried the
safe digest. Full pytest passed (`772 passed, 520 deselected, 2 warnings`). No
Runtime route, OpenAPI path, Studio UI, provider call, generated media, human
creative acceptance, business validation, public claim, patent/legal decision,
or COS active-rule promotion occurred. Handoff:
`docs/handoff/AFS-MAIN-LOOP-KEYFRAME-BRIDGE-EVIDENCE-20260630.md`.

Main-loop E2E baseline addendum: fresh branch
`codex/afs-goal-mode-main-loop-e2e-20260630` adds the first provider-closed
Runtime E2E regression for a real benchmark script. It connects storyboard
content quality, Production Graph, fixed visual asset source evidence, Evidence
Ledger, Human Gate, asset-graph Feedback Candidate, feedback context overlay,
and keyframe preflight context consumption in one test. The red/green loop
fixed CJK candidate-ref truncation in human-gate target IDs and fixed-asset
source evidence. Full pytest passed (`771 passed, 520 deselected, 2 warnings`),
maintenance audit has `failed=0`, and diff check passed. This is deterministic
runtime verification, not provider smoke, generated media, human creative
acceptance, business validation, public claim, patent/legal decision, or COS
active-rule promotion. Handoff:
`docs/handoff/AFS-MAIN-LOOP-E2E-BASELINE-20260630.md`.

T40 authorized merge/sync/runtime health addendum: standing integration
authorization conditions were rechecked for
`codex/afs-goal-mode-threshold-gate-20260630`. Branch review was
`ready_for_human_merge_review` with `blocker_count=0`; full pytest passed
(`770 passed, 520 deselected, 2 warnings`), Studio JS passed (`134 files`),
maintenance audit had `failed=0`, diff check passed, CLI help/version passed,
and the execution YAML files parsed. Local `master`, `origin/master`, server
`/home`, and server `/opt` were fast-forwarded to
`3f65c0a1178ecbe1d51c8fd16f4ca56a374d6084` without reset/clean. Runtime health
is `ready`. This is runtime health verification after sync, not provider smoke,
human creative acceptance, business validation, public claim, patent/legal
decision, or COS active-rule promotion. Handoff:
`docs/handoff/AFS-AUTHORIZED-T40-MERGE-SYNC-RUNTIME-HEALTH-20260630.md`.

Goal-mode threshold merge review addendum: T39 stops feature work on
`codex/afs-goal-mode-threshold-gate-20260630` for the mandatory merge review
gate. Precommit branch review from `origin/master` to
`fa04cfbe83b9559303d256a1b8813d64cce144af` found 19 commits, 59 changed files,
4610 insertions, 20 deletions, and 0 blockers; the T39 record commit reaches the
20-commit threshold. Full pytest, Studio JS check, maintenance audit
(`failed=0`), diff check, CLI help/version, and branch review passed. The
recommended next action is human-authorized merge/split/defer decision, not more
feature work on this branch. Handoff:
`docs/handoff/AFS-GOAL-MODE-THRESHOLD-MERGE-REVIEW-GATE-20260630.md`.

Studio source-evidence non-claim flags addendum: the next provider-closed
product slice retains `provider_calls_started` and
`human_creative_acceptance_claimed` inside the shared Studio `sourceEvidenceRefs()`
normalizer. This keeps preflight, keyframe layer, trace, and asset-detail
evidence surfaces aligned around the same safe non-claim flags without adding
Runtime routes, OpenAPI paths, provider calls, generated media, deploy, server
sync, human creative acceptance, or business validation. Handoff:
`docs/handoff/AFS-STUDIO-SOURCE-EVIDENCE-NON-CLAIM-FLAGS-20260630.md`.

Studio asset-library source-evidence preservation addendum: the next
provider-closed product slice preserves fixed visual asset `source_evidence`
when a promoted asset is added to the Studio asset library entry. This keeps
node-local asset detail and library-opened asset detail aligned without adding
Runtime routes, OpenAPI paths, provider calls, generated media, deploy, server
sync, human creative acceptance, or business validation. Handoff:
`docs/handoff/AFS-STUDIO-ASSET-LIBRARY-SOURCE-EVIDENCE-PRESERVATION-20260630.md`.

Studio asset-detail source-evidence addendum: the next provider-closed product
slice surfaces fixed visual asset `source_evidence` inside the Studio asset
detail popover. The view is a white-listed local review surface for human gate,
asset-card candidate, stage, and non-claim booleans; it does not expose signed
URLs, local paths, media bytes, provider raw data, Runtime routes, OpenAPI
paths, provider calls, deploy, server sync, human creative acceptance, or
business validation. Handoff:
`docs/handoff/AFS-STUDIO-ASSET-DETAIL-SOURCE-EVIDENCE-SURFACE-20260630.md`.

Studio promotion-gate production-graph evidence addendum: the next
provider-closed product slice records a safe `production_graph_artifact_id` in
Studio human-gate asset-card review notes and surfaces it in the fixed visual
asset promotion review summary. This connects `production_graph_snapshot ->
human gate -> promotion review` in the operator evidence chain without adding
Runtime routes, Runtime promotion payload fields, OpenAPI paths, provider
calls, generated media, deploy, server sync, human creative acceptance, or
business validation. Handoff:
`docs/handoff/AFS-STUDIO-PROMOTION-GATE-PRODUCTION-GRAPH-EVIDENCE-20260630.md`.

Studio production-graph keyframe trace addendum: the next provider-closed
product slice carries a safe `production_graph_review` summary from Studio
storyboard breakdown state into generated keyframe layers and
`lastKeyframeSourceEvidenceTrace`. The summary is limited to the production
graph snapshot artifact id, fixed-asset reuse count, and fixed visual asset
ids, so keyframe output records can explain fixed-asset reuse alignment without
provider raw data, signed URLs, local paths, generated media bytes, Runtime API
expansion, provider calls, deploy, server sync, human creative acceptance, or
business validation. Handoff:
`docs/handoff/AFS-STUDIO-PRODUCTION-GRAPH-KEYFRAME-TRACE-ALIGNMENT-20260630.md`.

Studio keyframe source-evidence output-record addendum: the next
provider-closed product slice surfaces `lastKeyframeSourceEvidenceTrace` in the
Studio inspector `输出记录`. The record shows fixed-asset source evidence and
`provider_prompt_inclusion_policy=excluded_by_default` without adding Runtime
routes, OpenAPI fields, provider calls, deploy, server sync, or human creative
acceptance claims. Handoff:
`docs/handoff/AFS-STUDIO-KEYFRAME-SOURCE-EVIDENCE-OUTPUT-RECORD-20260630.md`.

Studio keyframe source-evidence trace addendum: the next provider-closed
product slice records a safe `lastKeyframeSourceEvidenceTrace` when keyframe
responses are applied. The trace reuses the existing source-evidence normalizer
and explicitly records `provider_prompt_inclusion_policy=excluded_by_default`,
so it remains local evidence and does not enter provider prompts by default.
This does not expand Runtime API/OpenAPI, call providers, deploy, server sync,
or claim human creative acceptance. Handoff:
`docs/handoff/AFS-STUDIO-KEYFRAME-SOURCE-EVIDENCE-LOCAL-GENERATION-TRACE-20260630.md`.

Studio keyframe evidence inspector addendum: the next provider-closed product
slice surfaces T30 `keyframeLayer.fixed_asset_source_evidence_refs` in the
Studio inspector `本次参考摘要`. Operators can now review which fixed asset,
human gate, or asset-card candidate supplied a keyframe node's source evidence.
This is a local review surface only; it does not expand Runtime API/OpenAPI,
change provider prompt inclusion policy, call providers, deploy, server sync,
or claim human creative acceptance. Handoff:
`docs/handoff/AFS-STUDIO-KEYFRAME-EVIDENCE-INSPECTOR-REVIEW-SURFACE-20260630.md`.

Studio promotion-to-keyframe evidence-chain addendum: the next provider-closed
product slice carries fixed visual asset source evidence into the Studio
`keyframeLayer` created from storyboard output. The layer now records
`fixed_asset_source_evidence_count` and safe
`fixed_asset_source_evidence_refs`, using the existing source-evidence
normalizer instead of adding a duplicate sanitizer. This does not expand
Runtime API/OpenAPI, change provider prompt inclusion policy, call providers,
deploy, server sync, or claim human creative acceptance. Handoff:
`docs/handoff/AFS-STUDIO-PROMOTION-TO-KEYFRAME-EVIDENCE-CHAIN-20260630.md`.

Studio promotion-gate fixed-reuse addendum: the next provider-closed product
slice carries T28 human-gate `fixed_asset_reuse_count` into the visual-asset
promotion review summary. The promotion panel now shows candidate provenance
plus fixed-asset reuse background before an operator confirms a fixed visual
asset. This does not add Runtime routes, request fields, OpenAPI paths,
provider calls, generated media, deploy, server sync, human creative
acceptance, or business validation. Handoff:
`docs/handoff/AFS-STUDIO-PROMOTION-GATE-FIXED-REUSE-SUMMARY-20260630.md`.

Studio production-graph fixed-asset reuse addendum: the next provider-closed
product slice persists Runtime `production_graph` into Studio storyboard
breakdown state and surfaces fixed-asset reuse evidence as human-gate metadata
such as `Fixed reuse / 1 asset`. This keeps the graph visible in the operator
review path without adding a new Runtime `target_type`, route, request field,
OpenAPI path, provider call, generated media, deploy, server sync, human
creative acceptance, or business validation. Handoff:
`docs/handoff/AFS-STUDIO-PRODUCTION-GRAPH-FIXED-ASSET-REUSE-SURFACE-20260630.md`.

Studio preflight source-evidence surface addendum: the next provider-closed
product slice surfaces Runtime `included_asset_source_evidence_refs` in the
existing fixed-asset carry confirmation modal. Operators can now see the human
gate or asset-card candidate source for carried fixed assets before continuing
generation. The slice adds a small pure Studio helper, reuses existing asset
label helpers, and shrinks `node-generation-guards.js` slightly. It does not
add Runtime routes, request fields, OpenAPI paths, provider calls, generated
media, deploy, server sync, human creative acceptance, or business validation.
Handoff:
`docs/handoff/AFS-STUDIO-KEYFRAME-PREFLIGHT-SOURCE-EVIDENCE-SURFACE-20260630.md`.

Keyframe-preflight source-evidence addendum: the next provider-closed product
slice adds a compact safe review summary for fixed visual asset source evidence
to generation preflight responses. `included_asset_source_evidence_count` and
`included_asset_source_evidence_refs` let keyframe review surfaces identify
which included fixed assets came from which human gate and asset-card
candidate. The preflight token digest now includes the same source-evidence
identifiers. This does not add routes, request fields, OpenAPI paths, provider
calls, generated media, deploy, server sync, human creative acceptance, or
business validation. Handoff:
`docs/handoff/AFS-KEYFRAME-PREFLIGHT-SOURCE-EVIDENCE-SUMMARY-20260630.md`.

Production-graph fixed-asset reuse addendum: the next provider-closed product
slice lets storyboard production graph consume current project fixed visual
assets through their safe public projection. The graph now includes
`fixed_visual_asset` nodes, `script_can_reuse_fixed_asset` relationships, and a
safe manifest count for fixed asset source evidence. This does not add request
fields, expand OpenAPI, call providers, deploy, or claim human creative
acceptance. Handoff:
`docs/handoff/AFS-PRODUCTION-GRAPH-FIXED-ASSET-REUSE-EVIDENCE-20260630.md`.

Fixed-asset source-evidence addendum: the next provider-closed product slice
adds a safe `source_evidence` projection to fixed visual assets, derived from
the existing `promotion_gate`. Keyframe context now carries this evidence via
the existing `public_visual_asset()` path, connecting `asset_card_candidate ->
human gate -> fixed visual asset -> keyframe context` without adding request
fields, expanding OpenAPI, calling providers, or claiming human creative
acceptance. Handoff:
`docs/handoff/AFS-FIXED-ASSET-SOURCE-EVIDENCE-CONTEXT-20260630.md`.

Studio promotion-gate reuse-summary addendum: the next provider-closed product
slice surfaces the latest accepted asset-card human-gate reuse summary inside
the fixed visual asset promotion panel. The review surface shows safe local
labels such as `Project reuse / 3 shots`, while the Runtime promotion payload
remains limited to the existing provenance IDs and does not add `reuse_scope`.
This does not expand Runtime API/OpenAPI, call providers, deploy, or claim
human creative acceptance. Handoff:
`docs/handoff/AFS-STUDIO-PROMOTION-GATE-REUSE-SUMMARY-SURFACE-20260630.md`.

Studio human-gate reuse-policy addendum: the next provider-closed product slice
surfaces storyboard-derived `asset_card_candidates.reuse_policy` inside the
Studio human-gate target contract. The human-gate menu now shows a visible
reuse marker such as `Project reuse / 3 shots`, and the Runtime human-gate
decision note carries only the safe reuse summary. This does not promote fixed
assets, expand Runtime API/OpenAPI, open provider gates, or claim human creative
acceptance. Handoff:
`docs/handoff/AFS-STUDIO-HUMAN-GATE-ASSET-REUSE-POLICY-SURFACE-20260630.md`.

Asset reuse candidate addendum: the next provider-closed product slice adds
`reuse_policy` to storyboard-derived `asset_card_candidates`. Multi-shot
assets are now marked as `project_reuse_candidate`, single-shot assets remain
`shot_local_candidate`, and the storyboard safe manifest records
`asset_card_project_reuse_candidate_count`. This advances fixed-asset reuse and
human-gate preparation without writing fixed assets or calling providers.
Handoff: `docs/handoff/AFS-ASSET-REUSE-CANDIDATE-POLICY-20260630.md`.

Branch threshold gate addendum: after the authorized T19 merge/sync, new work
continues from `master` commit `f51237df89c680dafc54296d7e013bd98cd459af` on
fresh branch `codex/afs-goal-mode-threshold-gate-20260630`. The branch
integration preflight now exposes the next mandatory merge-review threshold:
20 commits, 80 changed files, or 5000 insertions. Handoff:
`docs/handoff/AFS-BRANCH-SIZE-MERGE-REVIEW-THRESHOLD-GATE-20260630.md`.

Authorized merge/sync addendum: on 2026-06-30 the human technical lead selected
`merge` for `codex/afs-project-book-full-goal-20260630`. The release gate was
rerun from `aba7494b88fd969bf337d692e2be3d5f63f1751f`: full pytest passed,
Studio JS check passed, maintenance audit had `failed=0`, branch preflight was
`ready_for_human_merge_review`, and `git diff --check` passed. Local `master`
was fast-forwarded from the frozen baseline `6071ef1a` to `aba7494b`, pushed to
GitHub, and fast-forwarded on both `/home/afs-ops/AgentFlowStudio` and
`/opt/afs/AgentFlowStudio`. Runtime `/health` was read-only checked as
`status=ready`; no provider smoke, live provider call, human acceptance, or
business validation occurred. Handoff:
`docs/handoff/AFS-AUTHORIZED-MASTER-MERGE-THREE-END-SYNC-20260630.md`.

Current goal-mode addendum: 2026-06-30 started the project-book full goal-mode
branch `codex/afs-project-book-full-goal-20260630` from the synced baseline
`6071ef1aa665930df2b9fa383260fc68ed4e4e64`. First verified slice targets
`AFS-T14 Content Quality Evaluation`: Runtime storyboard breakdown now emits a
deterministic `content_quality_report` artifact that checks source grounding,
dynamic shot-count policy, asset evidence, keyframe/video intent fields, and
safe non-claim boundaries. This is structure verification for content-production
quality gates, not provider smoke, human creative acceptance, business
validation, or durable memory promotion. Handoff:
`docs/handoff/AFS-CONTENT-QUALITY-REPORT-TASKRUN-20260630.md`.

Quality-feedback browser QA addendum: the current closeout slice verifies the
T15h quality-feedback next-context overlay UI through a real local
Playwright/browser harness without opening provider gates. The browser run
found and fixed a long Runtime artifact id contract bug: feedback, promotion,
and context-overlay artifact refs now use a 512-character artifact-ref bound in
Studio summaries/requests and Runtime Studio-state sanitization, while ordinary
operator text remains separately bounded. This is runtime/browser evidence for
the feedback candidate path, not provider smoke, human creative acceptance,
business validation, master merge, deploy, or server sync. Handoff:
`docs/handoff/AFS-STUDIO-QUALITY-FEEDBACK-CONTEXT-OVERLAY-BROWSER-QA-20260630.md`.

Content-quality benchmark addendum: the next slice adds
`examples/agentflow/content_quality_benchmark_scripts.example.json` plus
`tests/test_storyboard_content_quality_benchmarks.py` as the first T13/T14
regression pack. It covers dialogue, action, emotion turn, multi-scene,
line-based steps, and multi-character cases. The red/green loop fixed two
local fallback scene-label gaps (`海边`, `餐厅`) without provider calls or UI
changes. Handoff:
`docs/handoff/AFS-CONTENT-QUALITY-BENCHMARKS-TASKRUN-20260630.md`.

Production-graph addendum: the next verified slice adds
`agentflow.algorithms.production_graph` and Runtime storyboard breakdown now
returns and persists a safe `production_graph` snapshot. The graph links script,
shot, candidate asset, and content-quality-report nodes with explicit
relationships, records node count in the safe manifest, and writes a
`production_graph_snapshot` artifact. This is a candidate production data-model
contract for later asset cards and keyframes; it is not fixed asset memory,
provider smoke, human creative acceptance, business validation, or durable
memory promotion. Handoff:
`docs/handoff/AFS-PRODUCTION-GRAPH-CONTRACT-TASKRUN-20260630.md`.

Asset-card-candidate addendum: the next slice adds
`agentflow.algorithms.asset_card_candidates` and Runtime storyboard breakdown
now returns and persists safe `asset_card_candidates` derived from
`asset_graph`. Each candidate remains unconfirmed, blocks fixed asset memory
writes, carries safe shot/evidence refs, and marks provider enrichment as gated
by `AFS_ALLOW_REMOTE_VISION`. Existing `/asset-card-drafts` remains the
vision-gated enrichment route and was not expanded. Handoff:
`docs/handoff/AFS-ASSET-CARD-CANDIDATES-TASKRUN-20260630.md`.

Context-resolver candidate-boundary addendum: the next slice verifies that
`asset_card_candidate:*` refs produced by storyboard breakdown stay out of
keyframe preflight `included_assets`, `reference_image_channel`, and
`subject_reference_asset_id`. Their excluded reason is now
`asset_card_candidate_unconfirmed` instead of generic missing asset, while
fixed visual asset selection remains unchanged. Handoff:
`docs/handoff/AFS-CONTEXT-RESOLVER-CANDIDATE-BOUNDARY-TASKRUN-20260630.md`.

Evidence-ledger addendum: the next slice adds
`agentflow.algorithms.evidence_ledger` and Runtime storyboard breakdown now
returns and persists a safe `evidence_ledger` artifact. The ledger binds the
storyboard request plan, safe artifact, safe manifest, asset graph, content
quality report, production graph snapshot, and asset card candidates into one
structure/runtime evidence record with explicit non-claims. This is not provider
smoke, human creative acceptance, business validation, fixed asset memory, or
durable memory promotion. Handoff:
`docs/handoff/AFS-EVIDENCE-LEDGER-STORYBOARD-ASSET-TASKRUN-20260630.md`.

Generation-bridge addendum: the next slice adds
`agentflow.algorithms.generation_bridge` and gate-closed keyframe generation
now writes a safe `keyframe_generation_bridge` artifact. This gives T8 a
fake/local deterministic generation bridge that records model/context/request
refs, planned candidate ids, and provider-gate evidence without starting
provider calls, generating media bytes, or claiming human/business success.
Handoff:
`docs/handoff/AFS-KEYFRAME-GENERATION-BRIDGE-TASKRUN-20260630.md`.

Human-gate addendum: the next slice adds `agentflow.algorithms.human_gate` and
public Runtime route `POST /projects/{project_id}/human-gate-decisions`.
Runtime can now record safe local step-gate decisions for
`asset_card_candidate` and `keyframe_generation_bridge` targets, append them to
project `feedback_refs`, and expose the contract through OpenAPI. Studio has a
thin `recordHumanGateDecision(payload)` client method, but no UI state machine
or fixed asset promotion was added. This is not provider smoke, human creative
acceptance, business validation, generated media, or durable memory promotion.
Handoff:
`docs/handoff/AFS-HUMAN-GATE-CONTRACT-TASKRUN-20260630.md`.

Studio human-gate hook addendum: the next slice adds a thin Studio UI hook for
the Runtime human gate contract. Storyboard breakdown keeps safe
`asset_card_candidates` refs on the source script node, keyframe generation
keeps safe `generation_bridge` refs on the image node, and the node menu shows
`记录人工 Gate` only when such targets exist. The UI calls
`recordHumanGateDecision(payload)` and records only safe decision summaries in
node params. No fixed asset promotion, provider gate, provider call, generated
media, or business/human acceptance claim was added. Handoff:
`docs/handoff/AFS-STUDIO-HUMAN-GATE-UI-HOOK-TASKRUN-20260630.md`.

Asset-promotion-gate addendum: the next slice adds optional provenance between
accepted asset-card human gate decisions and fixed visual asset promotion.
Runtime `VisualAssetPromoteRequest` accepts `source_human_gate_id` and
`source_asset_card_candidate_id`, stores them as a safe `promotion_gate`, and
keeps direct manual promotion backwards-compatible. Studio attaches only the
latest accepted `asset_card_candidate` human gate summary when present. This is
promotion provenance, not provider smoke, generated media evidence, human
creative acceptance, business validation, or durable memory promotion. OpenAPI
path count remains 50; the exporter-generated snapshot now includes the two
optional request fields. Handoff:
`docs/handoff/AFS-ASSET-PROMOTION-GATE-TASKRUN-20260630.md`.

Browser Studio gate-flow QA addendum: the next slice performs an in-app Browser
smoke against local `/studio/` with a temporary Runtime root and explicit
provider gates set to false. The QA verifies the first screen renders, console
warn/error logs stay empty, the empty-project template gate asks the user to
create a project, and the project-creation continuation path creates a role
setting template with three canvas nodes. This is rendered UI/runtime smoke
only, not provider smoke, generated media evidence, human creative acceptance,
business validation, deploy verification, or server three-end sync. Handoff:
`docs/handoff/AFS-BROWSER-STUDIO-GATE-FLOW-QA-20260630.md`.

Deterministic promotion UI harness addendum: the next slice extracts Studio
fixed-visual-asset promotion payload construction into
`visual-asset-promotion-request.js` and covers it with an executable Node
harness. The harness proves accepted asset-card human gate provenance is
included, sanitized, and omitted for direct promotion without accepted gate
evidence. This replaces a brittle string-only check with deterministic payload
verification and keeps `visual-asset-panel.js` under the 300-line threshold.
This is Studio contract verification only: no Runtime/OpenAPI change, provider
call, generated media, human creative acceptance, business validation, deploy,
or server sync. Handoff:
`docs/handoff/AFS-DETERMINISTIC-PROMOTION-UI-HARNESS-20260630.md`.

Deterministic promotion browser harness addendum: the next slice adds
`tools/studio_visual_asset_promotion_browser_qa.py` as a real browser/runtime
harness for the fixed visual asset promotion path. It seeds a temporary Runtime
project with a safe image asset and accepted asset-card human gate summary,
opens `/studio/`, submits the visual asset modal, and verifies the Runtime
visual asset record carries a sanitized `promotion_gate` while
`provider_calls_started=false`. Runtime Studio-state persistence now allows
safe `humanGateDecisions` through a small dedicated sanitizer module, and common
browser static-route wiring is shared from `studio_asset_context_browser_qa_support.py`
instead of copied across tools. This is browser/runtime verification only: no
provider smoke, generated media, human creative acceptance, business
validation, deploy, or server sync. Handoff:
`docs/handoff/AFS-DETERMINISTIC-PROMOTION-BROWSER-HARNESS-20260630.md`.

Provider-smoke readiness gate addendum: the next slice calibrates
`tools/afs_provider_connected_validation_readiness.py` so local or server
environment gates are no longer treated as current-session authorization. The
tool now distinguishes `ready_for_authorization`,
`ready_for_human_authorization`, and `ready_for_provider_smoke`, with
`ready_for_provider_smoke` requiring an explicit no-cost readiness flag after
human authorization. Current local report is `ready_for_human_authorization`:
Runtime readiness and LLM/image gate projection are technically ready, but this
TaskRun did not authorize live provider smoke. No provider call, generated
media, human creative acceptance, business validation, deploy, or server sync
occurred. Handoff:
`docs/handoff/AFS-PROVIDER-SMOKE-READINESS-GATE-20260630.md`.

Goal-mode branch integration review addendum: the next slice adds
`tools/afs_goal_mode_branch_integration_review.py` plus
`tests/test_afs_goal_mode_branch_integration_review.py` as a deterministic
pre-merge hygiene gate for the accumulated goal-mode branch. The review checks
codex branch naming, local/upstream/GitHub alignment, local `master` versus
`origin/master`, allowed dirty ledger, forbidden local/provider/generated-media
paths, and handoff index coverage. This is branch-readiness evidence for human
merge review only: no merge, deploy, server sync, Runtime health claim,
provider call, generated media, human creative acceptance, business validation,
or durable memory promotion occurred. Handoff:
`docs/handoff/AFS-GOAL-MODE-BRANCH-INTEGRATION-REVIEW-20260630.md`.

Human merge review addendum: the next slice records
`docs/handoff/AFS-HUMAN-MERGE-REVIEW-BASELINE-DECISION-20260630.md` as the
baseline-freeze decision packet for the accumulated goal-mode branch. Current
branch review remains `ready_for_human_merge_review` with `blocker_count=0`;
local HEAD, upstream, and GitHub remote branch are aligned at
`21760e5d59707323ff305ae6a90e8ffa719b04cf`, while `origin/master` remains at
the frozen three-end baseline `6071ef1aa665930df2b9fa383260fc68ed4e4e64`.
This is a human merge-review gate only: no merge, deploy, server sync, Runtime
health claim, provider call, generated media, human creative acceptance,
business validation, or durable memory promotion occurred.

Fast-forward merge preflight addendum: the next slice enhances
`tools/afs_goal_mode_branch_integration_review.py` so the report explicitly
checks whether `origin/master` is an ancestor of the current codex branch
`HEAD`. The report now exposes `base_is_ancestor_of_head` and
`merge_mode_recommendation`, and blocks with `base_not_ancestor_of_head` if the
base has diverged. This prepares the next authorized master-merge task while
still performing no merge, deploy, server sync, Runtime health claim, provider
call, generated media, human creative acceptance, business validation, or
durable memory promotion. Handoff:
`docs/handoff/AFS-FAST-FORWARD-MERGE-PREFLIGHT-GATE-20260630.md`.

Runtime feedback candidate addendum: because `AFS-T19 Authorized Master Merge +
Three-End Sync` still requires explicit human authorization, the next safe
local slice tightens the existing `/feedback` Runtime contract instead of
merging or syncing. Every sanitized Runtime feedback event now carries a safe
`feedback_candidate` summary with `promotion_status=candidate_only`,
`promotion_blocked_by_default=true`, `requires_human_promotion_decision=true`,
and explicit false flags for provider calls, durable memory, Company KB writes,
context overlay eligibility, private external links, local paths, provider raw, and media
bytes. This is T15 feedback-candidate contract evidence only: no new route,
OpenAPI path, Studio UI, provider call, generated media, master merge, deploy,
server sync, Runtime health claim, human creative acceptance, business
validation, or durable memory promotion occurred. Handoff:
`docs/handoff/AFS-RUNTIME-FEEDBACK-CANDIDATE-CONTRACT-20260630.md`.

Runtime feedback candidate promotion addendum: the next local deterministic
slice adds `AFS-T15b Feedback Candidate Promotion Decision Harness`. Runtime now
has `POST /projects/{project_id}/feedback-candidate-promotions`, which reads an
existing `runtime_feedback_event` artifact, verifies its embedded
`feedback_candidate`, and writes a separate safe
`runtime_feedback_candidate_promotion_decision` artifact. The decision can mark
a candidate as `promote_to_context_overlay`, `reject`, or
`needs_more_evidence`, but even the promoted path only sets
`context_overlay_allowed=true`; it does not write context, durable memory,
Company KB rules, generated media, or provider output. Studio only gets a thin
runtime-client method for the route; no UI state machine was added. The Runtime
OpenAPI snapshot was regenerated by exporter and path count is now 51. This is
promotion-decision contract evidence only: no provider call, master merge,
deploy, server sync, Runtime health claim, human creative acceptance, business
validation, or durable memory promotion occurred. Handoff:
`docs/handoff/AFS-RUNTIME-FEEDBACK-CANDIDATE-PROMOTION-TASKRUN-20260630.md`.

Runtime feedback candidate context-overlay addendum: the next local
deterministic slice adds `AFS-T15c Feedback Candidate Context Overlay Harness`.
Runtime now has
`POST /projects/{project_id}/feedback-candidate-context-overlays`, which reads
an existing `runtime_feedback_candidate_promotion_decision` artifact and only
accepts decisions that explicitly allow `promote_to_context_overlay`. It writes
a safe `runtime_feedback_candidate_context_overlay` artifact and appends it to
project `feedback_refs`. The overlay is a local next-context evidence object:
it records that the reviewed candidate may be included in a later local context
pass, but it does not mutate the context resolver, write a context bundle,
write durable memory, write Company KB rules, call providers, generate media,
deploy, or server-sync. Studio only gets a thin runtime-client method for the
route; no UI state machine was added. The Runtime OpenAPI snapshot was
regenerated by exporter and path count is now 52. Handoff:
`docs/handoff/AFS-RUNTIME-FEEDBACK-CANDIDATE-CONTEXT-OVERLAY-TASKRUN-20260630.md`.

Runtime feedback candidate context-consumption addendum: the next local
deterministic slice adds `AFS-T15d Feedback Candidate Context Resolver
Consumption Harness`. Runtime context resolution now reads safe
`runtime_feedback_candidate_context_overlay` artifacts from project
`feedback_refs`, skips missing or unsafe overlay refs, and attaches bounded
`feedback_context_overlays` summaries to the local context bundle. Keyframe
preflight exposes the same summaries and includes them in the preflight token
digest; model-call context records them under feedback context; keyframe safe
manifest and local generation bridge record overlay counts/IDs. The overlay is
feedback evidence only: it does not enter `included_assets`,
`reference_image_channel`, `subject_reference_asset_id`, provider prompt policy,
durable memory, Company KB, generated media, deploy, or server sync. No OpenAPI
snapshot update was needed; path count remains 52. Handoff:
`docs/handoff/AFS-FEEDBACK-CANDIDATE-CONTEXT-CONSUMPTION-TASKRUN-20260630.md`.

Studio feedback overlay review-surface addendum: the next local deterministic
slice adds `AFS-T15e Studio Feedback Overlay Review Surface`. Studio state
now persists bounded safe `lastContextBundle.feedback_context_overlays`
summaries, dropping provider raw, trace internals, signed URLs, local paths,
safety-boundary fragments, and media-byte markers before save/load. The
existing inspector context summary and algorithm process panel now render
consumed feedback overlay counts/summaries from `lastContextBundle` only. This
is a review surface and Studio-state contract, not overlay creation UI, provider
prompt policy, generated media, durable memory, Company KB promotion, deploy,
or server sync. No OpenAPI snapshot update was needed; path count remains 52.
Handoff:
`docs/handoff/AFS-STUDIO-FEEDBACK-OVERLAY-REVIEW-SURFACE-20260630.md`.

Feedback overlay selection addendum: the next local deterministic slice adds
`AFS-T16 Feedback Overlay Selection / Rejection UI Contract`. Studio can now
record local `include_for_next_context` / `reject_for_next_context` decisions
for already-consumed safe feedback overlays, persist only bounded safe decision
fields through `/studio-state`, and carry those decisions into keyframe request
context as `feedback_context_overlay_decisions`. Runtime context resolution now
filters safe `feedback_context_overlays` by selected/rejected overlay IDs and
records decision trace only when an actual decision exists. This is not provider
prompt injection, generated media, durable memory, Company KB promotion, deploy,
server sync, or human/business acceptance. No OpenAPI snapshot update was
needed; path count remains 52. Handoff:
`docs/handoff/AFS-FEEDBACK-OVERLAY-SELECTION-UI-CONTRACT-20260630.md`.

Feedback overlay prompt-policy addendum: the next local deterministic slice
adds `AFS-T17b Feedback Overlay Prompt Policy Gate`. Because this branch already
used `AFS-T17` for goal-mode branch integration review, the suffix avoids a
duplicate task-id collision. Runtime now records one shared
`feedback_overlay_prompt_policy` across context trace, model-call context,
request projection, keyframe safe manifest, and generation bridge evidence.
The default policy is explicit: selected feedback overlays remain local context
evidence only, `provider_prompt_includes_context_overlays=false`, and future
use of overlay text in provider prompts requires a separate prompt policy gate.
This is not provider prompt injection, generated media, durable memory, Company
KB promotion, deploy, server sync, or human/business acceptance. No OpenAPI
snapshot update was needed; path count remains 52. Handoff:
`docs/handoff/AFS-FEEDBACK-OVERLAY-PROMPT-POLICY-GATE-20260630.md`.

Feedback overlay prompt-policy review-surface addendum: the next local
deterministic slice adds `AFS-T18b Feedback Overlay Prompt Policy Review
Surface`. Runtime now exposes the safe prompt policy at
`context_bundle.feedback_context_overlay_prompt_policy`, and Studio state
persistence keeps only bounded policy summary fields. Existing Studio review
surfaces now display the boundary: feedback overlays remain local context and
are not injected into generation prompts by default. This is review-surface
evidence only: no prompt injection authorization, new route, OpenAPI snapshot
update, provider call, generated media, durable memory, Company KB promotion,
deploy, server sync, or human/business acceptance. Handoff:
`docs/handoff/AFS-FEEDBACK-OVERLAY-PROMPT-POLICY-REVIEW-SURFACE-20260630.md`.

Feedback overlay prompt-approval gate addendum: the next local deterministic
slice adds `AFS-T18c Feedback Overlay Prompt Authorization Design Gate`.
The shared prompt policy now includes a structured `prompt_provider_gate`:
provider prompt inclusion is blocked by default, requires human approval,
requires the provider gate, requires prompt budget review, and requires safety
filtering before any future overlay text could be used in provider prompts.
Studio state keeps only this safe gate summary. The implementation deliberately
does not use persisted field names containing `authorization`, because the
existing Studio state sanitizer rejects that security-sensitive marker. This is
not provider prompt injection, generated media, durable memory, Company KB
promotion, deploy, server sync, Runtime health verification, or
human/business acceptance. No OpenAPI snapshot update was needed; path count
remains 52. Handoff:
`docs/handoff/AFS-FEEDBACK-OVERLAY-PROMPT-APPROVAL-GATE-20260630.md`.

Studio state feedback-policy sanitizer split addendum: because T18c pushed
`apps/api/runtime_studio_state_context.py` to exactly 300 lines, the next
provider-closed maintenance slice adds `AFS-T18d Studio State Feedback Policy
Sanitizer Split`. Feedback overlay prompt-policy state sanitization now lives
in `apps/api/runtime_studio_state_feedback_policy.py`, while the context module
returns to 248 lines. The new helper reuses the existing `_text` sanitizer and
`safe_id` boundary, so local-path/runtime-artifact-path rejection and safe ID
normalization remain unchanged. This is a maintenance/contract split only: no
Runtime route, OpenAPI path, Studio fetch, provider call, generated media,
durable memory, Company KB promotion, deploy, server sync, Runtime health
verification, or human/business acceptance. Handoff:
`docs/handoff/AFS-STUDIO-STATE-FEEDBACK-POLICY-SANITIZER-SPLIT-20260630.md`.

Feedback candidate taxonomy addendum: because `AFS-T19 Authorized Master Merge
+ Three-End Sync` still requires explicit human authorization, the next
provider-closed product slice adds `AFS-T15f Feedback Candidate Taxonomy
Contract`. Sanitized Runtime feedback now carries bounded `feedback_taxonomy`
IDs for quality feedback, asset-graph feedback, and generic runtime feedback.
The same safe taxonomy IDs and `taxonomy_count` propagate through
`feedback_candidate`, promotion decisions, context overlays, context resolver
summaries, model-call context, and Studio-state persistence. This is a
candidate-feedback contract improvement only: no new Runtime route, OpenAPI
path, Studio fetch, provider call, generated media, durable memory, Company KB
promotion, master merge, deploy, server sync, Runtime health verification, or
human/business acceptance. Handoff:
`docs/handoff/AFS-FEEDBACK-CANDIDATE-TAXONOMY-CONTRACT-20260630.md`.

Feedback candidate scope/conflict addendum: the next provider-closed product
slice adds `AFS-T15g Feedback Candidate Scope + Conflict Contract`. Runtime
feedback candidates now carry safe `target_binding`, `scope_policy`, and
`conflict_summary` objects. These fields make project scope, no-global-promotion
policy, and single-feedback conflict signals explicit, and they propagate
through promotion decisions, context overlays, context resolver summaries,
model-call context, and Studio-state persistence. This is a feedback governance
contract only: no new Runtime route, OpenAPI path, Studio fetch, provider call,
generated media, durable memory, Company KB promotion, master merge, deploy,
server sync, Runtime health verification, or human/business acceptance.
Handoff:
`docs/handoff/AFS-FEEDBACK-CANDIDATE-SCOPE-CONFLICT-CONTRACT-20260630.md`.

Model-call feedback overlay sanitizer split addendum: because T15g pushed
`agentflow/algorithms/model_call_context/__init__.py` to 294 lines, the next
provider-closed maintenance slice adds `AFS-T18e Model Call Feedback Overlay
Sanitizer Split`. Feedback overlay summary sanitization now lives in
`agentflow/algorithms/model_call_context/feedback_context.py`, while
`model_call_context/__init__.py` returns to 228 lines. The helper receives the
existing `_sanitize_text` and `_safe_ref_list` boundaries by dependency
injection, so URL, credential, local-path, provider-raw, and safe-ref behavior
remains unchanged. This is a maintenance/contract split only: no Runtime route,
OpenAPI path, Studio fetch, provider call, generated media, durable memory,
Company KB promotion, master merge, deploy, server sync, Runtime health
verification, or human/business acceptance. Handoff:
`docs/handoff/AFS-MODEL-CALL-FEEDBACK-OVERLAY-SANITIZER-SPLIT-20260630.md`.

Studio quality feedback context-overlay UI addendum: the next provider-closed
product slice adds `AFS-T15h Studio Quality Feedback Context Overlay UI Hook`.
Studio quality feedback remains raw evidence by default, but the feedback form
now has an explicit default-off operator choice to promote the recorded
feedback candidate and write a safe Runtime context-overlay artifact for the
next local context pass. The Runtime routes already existed; this slice wires
the Studio UI to them through small helper modules, stores only a bounded
`qualityFeedbackCandidates` node summary, and adds a Runtime Studio-state
sanitizer for that summary. This is a local feedback-loop UI contract only: no
new Runtime route, OpenAPI path, provider call, generated media, durable
memory, Company KB promotion, master merge, deploy, server sync, Runtime health
verification, or human/business acceptance. Handoff:
`docs/handoff/AFS-STUDIO-QUALITY-FEEDBACK-CONTEXT-OVERLAY-UI-20260630.md`.

This file keeps only current work, blockers, and evidence entrypoints. Retired
Workbench, static memory-workbench, old Web RC, and old browser-QA threads are
not current task entrypoints.

Internal beta account/admin baseline: 2026-06-26 added the admin-only
`auth-invites` CLI on top of the existing Runtime auth store. Current
administrator entrypoint:
`docs/handoff/AFS-INTERNAL-BETA-ADMIN-20260626.md`. The CLI supports issuing,
listing, and revoking one-time invite codes; Runtime persists invite hashes and
safe metadata only. Plaintext invite codes are admin-local distribution
material and must not be copied into GitHub issues, PRs, handoffs, DEVLOG, or
TASK_TRACKER. This is an internal beta access mechanism, not a public admin UI,
SaaS role/org system, password reset system, or billing/accounting layer.
Addendum: the 2026-06-26 hardening pass adds auth failure rate limiting, safe
auth/request audit logs, weak static env invite-code skipping, atomic JSON
writes with file locks, an auth-level read-modify-write lock, and the
`runtime-backup create` administrator backup command. Maintenance ledger:
`docs/maintenance/AFS-INTERNAL-BETA-HARDENING-20260626.md`.

Studio generation/reference bugfix baseline: 2026-06-26 pass fixed the current
internal-test blockers around script import, progress percentages, asset-library
reference binding, and image relay provider naming/diagnostics. Script import
now accepts text/markdown plus Word/PPT (`.docx/.pptx` with OOXML extraction
and `.doc/.ppt` best-effort text extraction). Active image/video generation
shows percentages when available; prompt optimization, script expansion, and
storyboard breakdown write percentage state. Asset-library "用作参考" now binds
image assets to the selected node: video nodes get `firstFrameImageAssetId` and
a first-frame upload ref, image/keyframe nodes get a `reference_image` upload
ref. Current image service defaults moved from `codex_image` to external
`image_relay`; Runtime keeps a legacy alias for old ignored configs and splits
safe relay errors into reference-slot, unsupported-reference-route,
missing-service, auth, and HTTP block ids. Verification: JS syntax 122 files
passed, role-based local user simulation passed for script import, asset reuse,
progress, and provider route; focused generation/reference pytest 104 passed,
CLI help/version
passed, maintenance audit failed=0, `git diff --check` passed. Full pytest had
637 passed / 3 failed / 520 deselected / 1 warning; failures are environment or
pre-existing state (`D:/Learning materials/...` source KB absent on Linux and
untracked `ops/sub2api/*` retention review items). Maintenance ledger:
`docs/maintenance/AFS-STUDIO-GENERATION-REFERENCE-BUGFIX-20260626.md`.
Addendum: the same-day Runtime deployment guard now projects an ignored local
`codex_image` API relay service in `AFS_PROVIDER_CONFIG` into product-facing
`image_relay` in memory, including an `image_relay_pool`, `/images/edits`
default, and `reference_image_slots >= 1` for asset-reference image edits. This
lets server Runtime use current `image_relay` model plans even before a
privileged operator rewrites root-owned `/etc/afs/providers.local.json`.
The same guard pass also allows image relay artifact downloads over HTTP only
when the response host matches configured `allowed_artifact_hosts`, matching
the current relay's temporary artifact URL shape without persisting returned
URLs in Git or safe manifests. A live host probe showed Crazyrouter image
artifacts coming from `vod2.myqcloud.com`, so the code adds `.myqcloud.com` as
a Crazyrouter image relay default artifact host while keeping the allowlist
requirement.
Video relay polling also treats Seedance `not_start` as a queued/running state
instead of a terminal failure; this was found by a live 5s/480p smoke where task
submission succeeded but first poll returned `not_start`.
Verification: focused provider/Runtime/Studio regression set passed 61,
`git diff --check` passed, and a read-only loader probe against
`/etc/afs/providers.local.json` exposed `image_relay` plus `seedance_i2v` while
rejecting `codex_image`. Remaining privileged ops cleanup: physically remove
old `codex_image` keys from `/etc/afs/providers.local.json` and disable
`afs-codex-image-worker.service`; current shell lacks passwordless sudo.

Addendum: the same-day Studio front-end patch fixed two QA-found residual
entrypoint bugs. Canvas floating upload now routes both `text` and `script`
nodes to script import, preserving Word/PPT/text support instead of sending
script-node uploads through image upload. Asset-library fixed visual assets
used on video nodes now keep their visual context and synchronize the first
public `image_asset_refs` entry into `firstFrameImageAssetId` plus a
`first_frame` upload ref; drawer `设为首帧/设为尾帧` and generation-time fallback
use the same fixed-asset image resolution for already-saved projects. Handoff:
`docs/handoff/AFS-STUDIO-ASSET-VIDEO-SCRIPT-UPLOAD-FIX-20260626.md`.
Verification: Studio JS syntax 122 files passed, focused Studio/Runtime
regression set 84 passed, and `git diff --check` passed. No live provider call
or provider/config contract change occurred.

AFS+COS takeover baseline: 2026-06-26 branch cleanup completed across local,
GitHub, server `/home`, and server `/opt`. The intended clean branch state is
`master` only on all four surfaces. Merged server-local `codex/*` branches were
deleted. Stale `codex/open-source-handoff-governance` was inspected, not merged
because it was behind current video-chain work, then removed from local
worktree/local branch/GitHub after the current takeover handoff was recreated
on `master`. Current takeover entry:
`docs/handoff/AFS-COS-TAKEOVER-20260626.md`. Server `/home` still has an
untracked `ops/` directory and it remains intentionally untouched as an
ops-local artifact. Boundary: no provider call, secret read, media byte write,
or private Company OS source copy occurred.

Video node full-chain hardening follow-up: 2026-06-26 pass fixed four issues
from the robot/rooftop full-chain experiment. `扩写剧本` now requests and
falls back to formal short-video script prose before storyboard breakdown,
instead of emitting placeholder `分镜 01/02/03/04` lines. Keyframe generation
now builds an editable `keyframeAssetPlan` from connected asset cards and
writes candidate signatures/features/reference-image counts into the keyframe
prompt, with explicit constraints against unrequested stools, chairs, eaves,
extra props, new characters, text, watermarks, UI, or borders; keyframe image
nodes also expose `编辑关键帧资产约束` to open the editable generation prompt for
manual constraint revision before regeneration. The video
asset-card button now handles the `video-asset-card-draft` action and gives
visible no-video/running/success/failure feedback. Runtime video jobs now expose
safe timing fields (`provider_phase`, `elapsed_sec`, `queued_sec`,
`running_sec`) so slow 5s generation can be distinguished between provider
queue/wait and generation runtime where observable. Verification: Studio
script/assets static set 40 passed, Runtime video generation tests 12 passed
with 1 existing warning, and `npm.cmd run check:studio-js` passed for 121
files. The current robot/rooftop server job
`studio-1782460097617-ynsp23-video_generation-d5b554ffabf1` was inspected via
safe/task artifacts only and had succeeded with one MP4; old code lacked
granular timing, but safe file times indicate about 58 seconds before provider
task-state persistence and about 3 minutes 32 seconds until final candidate
write. Boundary: no new live provider call in this pass; timing is
Runtime/provider evidence, not creative quality or human acceptance.

Video timeline prompt follow-up: 2026-06-26 screenshot investigation found
Studio job `studio-1782194320739-0phdgx-video_generation-ed77c226b864` reached
the deployed `seedance_i2v` provider with first-frame image asset
`img_gen_0e4d7d2f6bbafbd2`, 5s, 720p, 16:9. The safe manifest ended
`poll_failed` with `remote_video_policy_block`, so the failure was an upstream
policy/copyright block after async provider queue/render/review, not a closed
video gate, missing first frame, Kling fallback, local timeout, credential
issue, or provider 404. Studio now generates a timeline-style keyframe-to-video
prompt with explicit 0.0s / 0.0-1.0s / 1.0-2.5s / 2.5-4.0s / 4.0-5.0s phases,
filters image-only `单张关键帧` language, and normalizes candidate asset-card
mentions so prompt-only references do not create duplicate malformed video
asset entries. Verification: Studio static set 24 passed, `npm.cmd run
check:studio-js` passed for 121 files, Runtime video generation tests 12 passed
with 1 existing warning, and `git diff --check` passed. Deployment: local
`master`, origin `master`, server `/home`, and server `/opt` were aligned at
`08dcf90`; Runtime `/health` stayed ready with video gate true, and
`/studio/src/keyframe-video-prompt.js` returned HTTP 200 from Runtime. Any live
provider smoke should use non-IP content unless the goal is explicitly to
observe provider policy blocking.

Seedance live video-node success follow-up: 2026-06-26 authorized Runtime smoke
used the deployed `/video-generations` route with `seedance_i2v`, a neutral
non-IP uploaded first frame, and a temporary authenticated server-local session.
The async task reached `succeeded` and wrote one MP4 candidate:
project `codex-video-node-smoke-189aa485`, job
`codex-video-node-smoke-189aa485-video_generation-ac869ed4d54e`,
`candidate_001.mp4`, 2,125,543 bytes, SHA-256
`a3616dccd6eae36689412f5c3525461cfeb612b03c543b4dced1ab8c95a39b27`.
Authenticated preview route returned HTTP 200 `video/mp4` after Runtime
restart. Local `master`, `origin/master`, server `/home`, and server `/opt`
are aligned at `4381b39`; `/health` is ready and video gate is true. Local
media QA from a temp copy: H.264, 1280x720, 24 fps, 5.041667 seconds, 121
frames; black/freeze events both 0. Boundary: runtime/provider/media
verification only, not human creative acceptance of the current IP storyboard;
no provider raw response, signed URL, secret, token, or media byte was written
to Git.

Current video provider addendum: 2026-06-25 pass retires the active Kling video
path and standardizes video generation/revision defaults on the Seedance relay
service `seedance_i2v` (`doubao-seedance-2-0-fast`). Server-side evidence for
the latest failed video node showed the video gate open and provider dispatch
started, but the selected service was the retired `kling_i2v`; this points to a
provider selection/config mismatch, not copyright/safety blocking. Active code,
config templates, CLI support surface, readiness scripts, and focused tests no
longer expose Kling provider entries. Verification: focused provider/Studio/API
regressions passed 105 with 5 deselected and 1 existing warning,
`npm.cmd run check:studio-js` passed for 120 files, and `git diff --check`
passed. Remaining work: deploy the cleanup to origin/server `/home` and `/opt`,
restart Runtime, confirm `/health` video gate/service alignment, then run an
authorized Seedance video smoke from a keyframe first frame.

Seedance 404 follow-up: the deployed provider config uses a shared Crazyrouter
account base URL with `/v1` plus a `seedance_i2v` service-level root base URL
for the Volc endpoint. The Seedance adapter now correctly lets the service
base URL override the account base URL, preventing `/v1/volc/v1/...` create
URLs that returned provider HTTP 404. Focused regression:
`tests/test_volc_seedance_video_adapter.py tests/test_api_runtime_video_generations.py`
passed 15 with 1 existing warning.

Seedance timeout follow-up: the next server smoke no longer returned 404 but
timed out waiting for the create response after the generic 120s request
timeout. Seedance create requests now use the video descriptor async timeout
unless the service explicitly overrides it.

Seedance safe task-state follow-up: after the async timeout fix, a live server
smoke reached the relay and got past create, but Runtime returned a generic
422 because the async provider task state attempted to persist a credential
environment variable name containing the forbidden `api_key` fragment. This is
not a copyright or safety block. Seedance submit tasks now omit credential env
names from persisted task state, and poll rehydrates auth details from provider
config at runtime. Focused regression:
`tests/test_volc_seedance_video_adapter.py tests/test_api_runtime_video_generations.py`
passed 16 with 1 existing warning.

Seedance policy-block follow-up: after the task-state fix, a deployed smoke
submitted successfully and polled the remote task, then the current
Wolverine/Sun Wukong keyframe was rejected by the upstream provider as a
copyright policy violation. The adapter now maps that provider response to a
safe policy-block reason and strips raw provider request ids before surfacing
the error. Runtime safe manifests now use `remote_video_policy_block` for this
case. This confirms the latest failure is content-policy related, not a Kling
fallback, 404, video gate, credential, or task-state persistence issue.

Current keyframe-to-video legacy-node addendum: 2026-06-25 follow-up expands
the right-click `接续视频节点` path so historical completed keyframe image nodes
whose title/prompt marks them as keyframes also get the same automation, even
when they lack newer `keyframe_generation` metadata. The created video node now
gets the keyframe image as explicit first frame plus a draft `videoAssetPlan`
assembled from keyframe visual assets, connected asset-card nodes, and any
remaining `@` references in the keyframe prompt. Prompt-only references fill
missing entries but do not duplicate connected asset cards. Verification:
focused continuation regressions passed 3, broader Studio static regressions
passed 36, `npm.cmd run check:studio-js` passed for 120 files, and
`git diff --check` passed. Residual risk: live provider video smoke and human
motion-quality acceptance remain separate claims.

Current keyframe-to-video addendum: 2026-06-25 pass adds a generic Studio
right-click continuation path from completed keyframe image nodes to video
nodes. The created video node is connected downstream of the keyframe and
stores the keyframe image asset as `firstFrameImageAssetId` with source
keyframe/asset metadata, so image-to-video submission starts from an explicit
first-frame contract instead of searching generated history. Video nodes now
also expose a right-click video asset-card recognition entry that reuses the
existing `afs:video-asset-card-draft` event and tells the user to generate the
video first when no video job exists. The regression is project-neutral and
does not special-case the Sun Wukong / Wolverine script. Verification so far:
focused red/green tests passed 2, broader Studio static regressions passed 35,
and `npm.cmd run check:studio-js` passed for 120 files. Residual risk:
provider-side video smoke and human creative review remain separate claims;
the latest keyframe screenshots still show asset drift from Wolverine wardrobe,
Sun Wukong armor exaggeration, prop-card character pollution, and loose aspect
ratio enforcement.

Current keyframe asset-reference addendum: 2026-06-25 pass inspected the live
Runtime manifests for the current Studio project and found the latest keyframe
failure reached the remote image provider before timing out. The safe blocked
manifest used `remote_image_provider_not_ready`; no copyright or safety block
was returned. Studio now carries connected asset-card image refs into keyframe
generation requests for the same storyboard tree, while fixed visual assets
remain project-wide strong references and unfixed asset cards remain local
candidate references only. Asset-card prompt-bar edits now create a conservative
`user_instruction` revision delta anchored by the prior generated/user
reference images, so typed image-adjustment instructions follow the same
low-drift route as panel field edits. A non-current-story regression
(`林晚 / 雨夜码头 / 蓝色雨伞`) guards against overfitting defaults to the
Sun Wukong / Wolverine test script, and generic prop signatures now summarize
the prop itself instead of copying unrelated shot text. Verification so far:
focused Studio regressions passed 3, broader Studio static regressions passed
33, Runtime keyframe/context regressions passed 37 with 1 existing warning,
`npm.cmd run check:studio-js` passed for 119 files, and `git diff --check`
passed. Local `master`, origin `master`, server `/home`, and server `/opt`
were fast-forwarded to the same commit, then Runtime was restarted with
`/health` ready and provider gates `image=true`, `video=true`. A server-side
keyframe provider smoke using the current storyboard intent succeeded with one
PNG output, confirming the current keyframe issue is not a copyright/safety
block. Residual risk: the smoke output dimensions did not strictly match the
requested `16:9`, so provider aspect enforcement remains a follow-up.

Current scene asset prompt isolation addendum: 2026-06-24 pass fixes the path
where a scene asset such as `山巅石台战场` could regenerate into a character
reference sheet. Scene asset-card defaults now strip story character names,
handheld weapons, and combat-summary text from reusable scene signatures and
feature-card fields; mountain stone-platform battlefields resolve to concrete
environment facts such as stone platform, cliff edge, cloud sea, distant ridges,
broken rocks, cracks, high-altitude light, and weather. Scene image prompts now
state that upstream character names are environmental-trace context only, not
permission to render characters, portraits, turnarounds, weapons, or
silhouettes. Asset-card image nodes now carry only user-uploaded reference
images into a new generation request; prior generated `scene_reference` /
`generated_keyframe_reference` outputs stay in node/history state but do not
auto-contaminate the next asset-card generation. The follow-up pass applies the
same isolation to target character cards: a `金刚狼` role card rejects unrelated
story characters, props, scene labels, shot metadata, and combat-summary text,
and the generated character prompt explicitly requests one target character
only with no second character, handheld prop, or scene background. A further
live-smoke follow-up anchors `金刚狼` away from silver-haired sci-fi armor by
specifying mature rugged male identity, dark short hair, sideburns / stubble,
stocky close-combat build, and body-integrated metal claws while rejecting
monkey traits, silver hair, sci-fi armor, cyan glow lines, and mythic armor.
Server-local image relay validation found the relay cache host was missing from
`codex_image.allowed_artifact_hosts`; the server config was updated without
writing provider key, signed URL, raw provider response, or media bytes to Git.
Verification: focused Studio regressions passed 3, broader Studio static set
passed 31, `npm.cmd run check:studio-js` passed for 119 files, and provider
control dispatch succeeded with one output after the allowlist update.
Remaining validation: GitHub/server three-end sync, Runtime health after
restart, live low-cost scene asset smoke, and browser visual acceptance.

Current asset-card adjustment/recovery addendum: 2026-06-24 pass separates the
asset-card system generation prompt from the editable prompt bar. Asset image
nodes now show only user revision instructions in the bottom input, while the
full typed asset-card prompt is assembled at generation time. Users can upload
reference images directly to an asset-card image node and those uploaded image
asset refs now carry into that asset-card generation request. Timeout recovery
now polls Runtime image assets for up to ten minutes so long provider runs that
finish after a browser timeout can still recover the node preview. Studio state
persistence prunes video media filenames such as `candidate_001.mp4` from safe
display fields before global safety scanning, while preserving safe Runtime
preview routes and asset ids. Verification: focused Studio regressions passed
2, Runtime state regression passed 1 / 1 existing warning, broader Studio
static set passed 28, Runtime Studio state set passed 16 / 1 existing warning,
`npm.cmd run check:studio-js` passed for 119 files, and `git diff --check`
passed. Remaining validation: GitHub/server three-end sync, Runtime health
after restart, and browser visual acceptance.

Current Runtime image timeout addendum: 2026-06-24 follow-up found the latest
Wolverine live smoke was failing because the remote image provider read timed
out and Runtime let the built-in `TimeoutError` escape as HTTP 500 before a
safe manifest could be written. Runtime now retries one provider timeout and,
if it still times out, returns a safe blocked image-generation manifest with
`remote_image_provider_not_ready` instead of leaving an empty run directory.
This failure evidence is provider timeout, not copyright/safety blocking.
Verification: focused Runtime timeout regression passed 1 and
`npm.cmd run check:studio-js` passed for 119 files. Remaining validation:
commit/push, server sync, Runtime restart/health, and another live smoke after
deploy.

Current Studio asset scope addendum: 2026-06-24 pass tightens Studio asset
reference scope and the material/history split. `@` suggestions now treat
ordinary generated image candidates as history, not project-fixed assets:
unconnected nodes only see fixed visual assets, while connected script trees
can also see unfixed asset-card draft nodes in that same connected tree. The
asset drawer now keeps fixed visual assets plus the latest renderable candidate
per source node, and older generated candidates move into `历史资产` with safe
Runtime previews when available. Script node context menus now expose one
`新增资产` action instead of separate role/scene/prop entries; the modal asks for
the asset name, infers the asset type from script/shot context plus conservative
local rules, and creates the same editable asset-card node path. Verification:
focused Studio static regressions passed 5 and `npm.cmd run check:studio-js`
passed for 119 files. Remaining validation: browser visual acceptance,
GitHub/server three-end sync, and Runtime health after restart.

Current Runtime-backed shot asset planning addendum: 2026-06-24 pass adds a
safe `/shot-asset-plans` Runtime route and rewires Studio right-click
`识别资产` to prefer that Runtime planning contract before falling back locally.
The route returns character / scene / prop refs with evidence text and a safe
manifest; it does not create nodes, call media providers, write provider raw
responses, store generated media bytes, or promote fixed memory. Studio now
supports manual asset-card creation from script nodes, project-wide `@`
suggestions for fixed assets, connected-tree-only suggestions for unfixed
asset-card drafts, filtering of retired assets, left-port upstream node
creation, and visible `取消固定资产` from image node menus. Generated image and
video results now support `放大查看`, and image/video export resolves Runtime
media at click time so `导出原图` / `下载视频` is an actual download action instead
of a stale link. Verification: Studio JS syntax check passed for 118 files; full
pytest passed 634 / 520 deselected / 2 existing warnings; CLI help/version
passed; `git diff --check` passed. Remaining validation: GitHub + server
three-end sync, Runtime health after restart, and browser visual acceptance.

Current asset-card fixed-asset carry addendum: 2026-06-24 pass narrows fixed
asset carry behavior for asset-card image generation. Character asset-card
generation automatically excludes unrelated fixed assets, so creating a new
character such as `金刚狼` is not constrained by another fixed character such as
`孙悟空`. Scene and prop asset-card generation treats fixed assets as optional
references: checked assets carry into that one request, unchecked fixed assets
are excluded. Ordinary image and video generation still use the stricter
fixed-asset confirmation path. Verification route: focused Studio static
regression passed 1, `npm.cmd run check:studio-js` passed for 118 files, and
`git diff --check` passed. Remaining validation: GitHub + server three-end
sync, Runtime health after restart, video gate state, and browser visual
acceptance.

Current Seedance video relay addendum: 2026-06-24 pass adds a `volc_seedance`
provider adapter and example `seedance_i2v` descriptor for the target
`doubao-seedance-2-0-fast` relay shape. Runtime now passes the optional last
frame image as a second provider reference for first/last-frame video tasks.
The adapter builds text + image reference payloads for `/volc/v1/contents/generations/tasks`,
polls the task, downloads the video into Runtime candidate storage, and keeps
provider raw responses, provider URLs, signed URLs, secrets, and generated bytes
out of Git and API payloads. Verification: Seedance adapter tests passed 4,
provider/runtime video focused tests passed 41, `npm.cmd run check:studio-js`
passed for 118 files, and `git diff --check` passed. Remaining validation:
server provider-local config alignment, live low-cost video provider smoke,
objective media QA, and human visual acceptance.

Current asset revision reference addendum: 2026-06-23 pass addresses asset-card
regeneration drift where editing a single card detail, such as changing a robot
surface from metal to plush, caused a full text-to-image reinterpretation. The
fix adds a Studio-side `assetCardRevision` plan that preserves ordered safe
image asset refs from prior generated/uploaded candidates, records changed card
fields and preserve locks, and sends only those explicit refs into keyframe
generation for asset-card drafts. Runtime adds an asset-card revision prompt
guard so provider prompts treat references as identity/layout anchors and apply
only the field delta instead of creating a new toy/chibi/mascot-style subject.
The second pass adds field-specific edit policy and prompt-priority handling:
`服装/外观` edits are constrained to outer-garment layering, `外形辨识` material
edits are constrained to surface treatment, and revision instructions are
prepended for asset-card revisions so prompt-length trimming preserves the
changed-field delta and anti-drift constraints.
The third pass upgrades this into reference-first / delta-only semantics:
reference image #1 is the primary visual source of truth for identity,
proportions, reference-sheet layout, camera distance, and non-edited details;
changed card fields are the only editable delta. Runtime avoids the generic
"reference image is only supplemental" guard for asset-card local revision.
The fourth pass upgrades provider dispatch from reference-backed regeneration
to source-image edit semantics for external APIs: asset-card revisions with a
prior image now set `image_operation=edit`, send the first prior image as
`edit_source_image_path`, carry ordered edit references, and request
`image_input_fidelity=high`. OpenAI Images-compatible API relay providers now
use multipart `/images/edits` with the source image in the `image` field for
this path while keeping ordinary generation on `/images/generations`. AFS keeps
the high-fidelity edit intent in request planning, but the OpenAI Images HTTP
payload omits `input_fidelity` unless a provider config explicitly opts in, so
the external API receives only supported default parameters. Provider
descriptors can now allow up to 16 reference image slots for multi-source edit
providers. Runtime also tolerates deployed legacy descriptors that still report
`reference_image_slots=0` by allowing the first prior image to act as the
required edit source for asset-card revisions. Studio labels the action as
`保存并局部修订生成`.
Verification: source-image edit focused regression passed 58 / 1 existing
warning; full pytest passed 626 / 520 deselected / 2 existing warnings;
`npm run check:studio-js` passed for 113 files; CLI help/version passed;
maintenance audit failed=0 with existing warnings only; `git diff --check`
passed. Follow-up provider compatibility regression passed 37 / 1 existing
warning after defaulting multipart image field to `image` and omitting
unsupported `input_fidelity`; legacy zero-slot source-edit regression passed
38 / 1 existing warning. Deployed server provider smoke then succeeded for the
robot metal-to-plush source-image edit: the output preserved multi-view
character-sheet layout, adult humanoid proportions, head shape, blue glow
details, and neutral grey background without chibi/toy drift. Boundary: no
provider raw response, signed URL, secret, local private path, generated media
byte, or Company OS private source content was written to the repo. Remaining
validation: human visual acceptance in the browser workflow.

Current keyframe timeout recovery addendum: 2026-06-23 pass fixes the browser
state mismatch where a long image/asset generation can complete in Runtime
after Nginx/browser request timeout, leaving the asset drawer populated while
the source node still displays failure. Runtime now treats an async-described
API relay result with `already_complete` as a completed image response and
returns safe previews/assets immediately. Studio sanitizes non-JSON 504 HTML,
keeps timed-out generation nodes in recovery, polls Runtime image assets by
`source_node_id`, and restores the node preview/upload refs if the saved asset
appears. Project creation also retries once on transient Runtime network
errors. Scene asset draft defaults now preserve rain-night street cues and only
select rooftop when the shot explicitly mentions rooftop/roof/terrace.
Verification: Studio JS syntax check passed for 113 files; focused timeout /
scene-asset regressions passed 4 / 1 existing warning; broader Runtime/Studio
keyframe-state suite passed 44 / 1 existing warning; `git diff --check`
passed. Maintenance follow-up: extract provider status normalization and
keyframe result recovery out of the existing 500+ line
`apps/api/runtime_keyframes.py`.

Current storyboard / asset intelligence addendum: 2026-06-23 pass upgrades the
script-to-shot and shot-to-asset contract. Local storyboard fallback now uses a
global entity pass plus per-shot resolution, keeps line-based scripts as
line-based shot units, inherits named subjects into pronoun/continuation shots,
and avoids generic `主角` / `主要场景` when concrete script labels exist. It
detects named characters such as `孙悟空`, `金刚狼`, repeated CJK actor names
such as `沈昭昭`, concrete scenes such as `暗办公室` / `山巅石台战场`, and prop
assets such as `金箍棒`. Provider storyboard prompts now explicitly require the
same real-name and prop classification behavior. Asset-card drafts now use a
more detailed typed feature card: character hair/face/build, scene palette, and
prop interaction/continuity are included by default, while character asset
generation is constrained to the fixed layout `正面半身特写 + 全身正面居中 +
左侧面全身 + 背面全身` with no weapons or background objects. Studio also
recovers nodes from reusable image asset previews when candidates are missing,
adds original-resolution image export, and prunes unsafe stale preview state
before Runtime saves. Verification: Studio JS passed for 115 files; storyboard
regressions passed 9 / 1 existing warning; web Studio static contract
regressions passed 31; full `pytest -q` passed 630 / 520 deselected / 2
existing warnings; `git diff --check` passed; added-line sensitive pattern scan
had no output. Remaining validation: deployment to GitHub + server `/home` +
server `/opt`, runtime health, and user visual acceptance in browser.
Maintenance follow-up: split storyboard local entity inference and asset-card
draft heuristics, because the two files are now just over the 300-line warning
threshold but below the 500-line hard split line.

Current Studio asset UX repair addendum: 2026-06-23 pass fixes the active
canvas issues reported from the user screenshots. Storyboard fallback and
provider-discard fallback now preserve semantic asset labels for robot/rooftop
scripts instead of producing generic `主角` / `主要场景`; right-click
`识别资产` reuses the stored structured shot and refines it before creating
candidate asset cards. Text/script/asset-card prompt input now keeps the bottom
prompt bar open while typing, all node double-clicks route to the prompt editor
instead of the create menu, blank-canvas double-click remains the only create
menu path, and node click/drag landing scale animation was removed to stop the
down-right jitter. Asset-card drafts now expose `保存资产卡` and
`保存并重新生成`, leaving final asset fixing optional after visual review.
Verification: focused Runtime/Studio tests passed 17 / 1 existing warning;
provider/static/interaction regression tests passed 33 / 1 existing warning;
`npm run check:studio-js` passed for 111 files; `git diff --check` passed;
maintenance audit failed=0 with existing warnings only; Playwright smoke on
local Runtime 8797 passed for text-node creation, prompt persistence,
storyboard split, semantic asset recognition, and asset-card save/regenerate
visibility. Boundary: no provider gate, secret, signed URL, provider raw
response, generated media byte, user account data, or Company OS private source
content was written. Remaining validation after deploy: public `/studio/`
smoke and human visual acceptance for regenerated asset images.

Current parallel feature integration addendum: 2026-06-23 pass first repaired
the server `/opt/afs/AgentFlowStudio` release checkout from dirty `b24dc57`
metadata to clean `e201346`, preserving the prior diff backup at
`/tmp/afs-opt-dirty-before-e201346-20260622-165701.patch`. It then merged the
Director Stage V2 Runtime compiler contract, TuanTuan confirmed-memory Runtime
API, and public-site social square request board into `master` with
fast-forward commits. A focused test run caught a missing social-square route
module after route registration; the missing `apps/api/runtime_social_square.py`
file was added as a follow-up commit before deployment. The AFS Debug Studio
generation repair at `e201346` was preserved: this integration did not modify
the repaired Studio generation guard, keyframe flow, asset popover, storyboard
fallback, or context resolver files. Verification: integration focused tests
passed 53 / 1 existing warning; full pytest passed 622 / 520 deselected / 2
existing warnings; `npm run check:studio-js` passed for 111 files; CLI
help/version passed; maintenance audit failed=0 with existing warnings only;
`git diff --check` passed. Boundary: no provider secret, provider raw response,
signed URL, generated media byte, user account data, or Company OS private
source content was written. Remaining validation after deploy: public social
square and Runtime health smoke, plus human review for director/sprite/social
product fit.

Current asset image prompt quality addendum: 2026-06-22 pass tightened the
storyboard-to-asset image request contract after live Crazyrouter `gpt-image-2`
outputs still looked abstract and UI-like. Provider-facing asset prompts are now
assembled in `asset-card-image-prompts.js` instead of the asset-card data module;
existing live asset nodes prefer the current structured `asset_card_draft`
prompt before stale `node.prompt`; character/scene candidates default to `16:9`
reference images and prop candidates to `1:1`. The model prompt now says
character turnaround, environment reference, or object reference, explicitly
forbids dashboards, app UI, charts, typography, labels, watermarks, and
decorative card layouts, and strips `@` asset tags before calling the image
provider. Verification: prompt static regressions passed 20; full pytest passed
600 / 520 deselected / 2 existing warnings; `npm run check:studio-js` passed for
110 files; CLI help/version passed; maintenance audit failed=0 with existing
warnings only; `git diff --check` passed; Node prompt sample confirmed no `@`
labels in provider-facing character/scene prompts. Deployment: local, GitHub,
server `/home`, and server `/opt` aligned at `1b9892e`; `afs-runtime` restarted
and health is ready. Live Crazyrouter smoke: character reference image succeeded
in 30.34s; scene reference image succeeded in 29.23s; both produced 16:9
non-UI reference images and did not collapse role/scene into the same abstract
picture. Boundary: no provider secret, provider raw response, signed URL,
generated media byte, user account data, or Company OS private source content
was written to repo records. Remaining validation: user canvas regeneration and
human visual acceptance.

Current asset reference lookup / keyframe flow addendum: 2026-06-22 pass fixed
the live-canvas failure where editing a fixed asset card and regenerating could
fail with `named_asset_not_connected_fail_closed`. Runtime context resolution
now includes fixed assets explicitly mentioned by `@label` even if they are not
connected to the target node; connected graph assets still retain distance
priority. The Studio preflight guard no longer hard-fails on unconnected named
assets and instead offers a one-run exclusion fallback. Storyboard keyframe
layers can now be created and generated without fixed candidate asset cards;
candidate cards remain editable review material until promoted. Fixed assets can
also be cancelled from the asset detail popover, which calls the Runtime retire
route and marks local refs as retired/excluded. Local storyboard fallback now
uses adaptive sentence/length distribution instead of mechanical three-sentence
chunks, reducing the apparent "always three shots" behavior when LLM breakdown
is gated off or discarded. Verification: focused Runtime/Studio regressions
passed 49 / 1 existing warning; `npm run check:studio-js` passed for 110 files;
CLI help/version passed; maintenance audit failed=0 with existing warnings
only; `git diff --check` passed; full pytest passed 602 / 520 deselected / 2
existing warnings. Boundary: no provider secret, provider raw response, signed
URL, generated media byte, user account data, or Company OS private source
content was written. Remaining validation: fresh user canvas regeneration and
human visual acceptance.

Current Crazyrouter image relay addendum: 2026-06-22 pass added
OpenAI Images-compatible `api_relay` support so `codex_image` can be switched
server-side to Crazyrouter `gpt-image-2` without changing Studio front-end
model IDs. The relay can now send `/images/generations` payloads and download
`data[0].url` provider media into local AFS candidate artifacts without
persisting provider URLs or raw responses. Server diagnosis before the switch
showed current `afs-runtime` was still loading
`/opt/afs/AgentFlowStudio/configs/providers.local.json`, had no Crazyrouter
service in the active registry, and did not have `CRAZYROUTER_API_KEY` in the
service environment; a user shell export is not sufficient for live Runtime
generation. Verification: provider registry tests passed 30; focused provider /
Studio / image-handoff regressions passed 95 with 1 existing warning; JS syntax
check passed for 109 files; `git diff --check` and provider module compile
passed. Remaining blocker: persist the Crazyrouter key and provider config into
systemd, restart Runtime, then run a real low-cost image smoke before claiming
speed or visual-quality improvement.

Current asset reference sheet addendum: 2026-06-22 pass changed the
storyboard-to-asset target from generic asset pictures to reviewable reusable
definition boards. Candidate role assets now ask for multi-view character
sheets; scene assets ask for same-space multi-angle environment boards; prop
assets ask for front/side/top/detail object sheets. Candidate asset cards and
fixed-asset review cards now carry reference-view fields, and fixing a
storyboard-derived asset image keeps the original asset-card draft defaults
instead of degrading to generic reference-image wording. Asset-tag markers such
as `@主角（角色）` are stripped before deriving short signature/mood text, and
the current robot rooftop case now gets local defaults for robot structure,
cold-blue metal palette, rooftop skyline layout, and moon/star/neon lighting.
Verification: `npm run check:studio-js` passed for 109 files; focused Studio
asset/prompt/runtime-state tests passed 48 / 1 existing warning; full pytest
passed 598 / 520 deselected / 2 existing warnings; CLI help and version
passed; maintenance audit failed=0 with existing warnings only; `git diff
--check` passed. Boundary: provider gates were not changed and no media bytes,
provider raw response, signed URL, secret, user account data, or Company OS
private source content was written. Remaining user-facing risk: final visual
quality still needs a fresh live generation and human acceptance on the canvas.

Current asset image generation audit addendum: 2026-06-22 pass fixed the
live-canvas issue where角色/场景 asset-card image nodes could generate the same
abstract picture. Root cause was request construction: asset-card nodes often
had empty `node.prompt`, so image generation fell back to a generic prompt and
the context resolver injected the same upstream storyboard text for both assets.
Asset-card image nodes now build requests from the editable asset card body and
safe `asset_card_draft` snapshot, add type-specific guards for character /
scene / prop asset images, label progress and result text as `资产图生成`, and
store generated uploads as character / scene / prop references rather than
generic keyframe references. Codex image handoff jobs now project safe
created/started/completed plus elapsed/queued/running seconds through Runtime
polling so long generation can be distinguished from queue wait. Verification:
full pytest passed 598 / 520 deselected / 2 existing warnings; `npm run
check:studio-js` passed for 108 files; CLI help and version passed; focused
image-handoff and Studio asset/front-end regressions passed; `git diff --check`
Python compile checks, and maintenance audit passed with warnings only.
Deployment: GitHub `master`, server `/home/afs-ops/AgentFlowStudio`, and
server `/opt/afs/AgentFlowStudio` aligned at `94fb9e1`; `afs-runtime` and
`afs-codex-image-worker` are active; Runtime health is ready. Boundary:
provider gates were not changed; no generated media byte, provider raw
response, signed URL, secret, invite code, session token, user account data, or
Company OS private source content was written. Remaining user-facing risk: live
image quality still depends on the active image provider/worker, but the
request now gives role-specific inputs instead of duplicated keyframe prompts.

Current Studio chain regeneration addendum: 2026-06-22 pass fixed the
internal-test chain issues found on the live canvas. Runtime Studio state now
keeps safe structured params for storyboard shots, asset-card drafts, fixed
visual assets, keyframe layers, uploads, warnings, and one-run exclusions, so
reload/server save no longer erases the reviewed production graph. Storyboard
LLM JSON parsing accepts fenced/trailing output instead of silently degrading
to coarse text splitting, and the local fallback no longer misclassifies
contextual `信号` / `灯火` as prop assets. Valid-but-sparse provider storyboard
JSON is now quality-gated for long scripts and falls back explicitly when it
lacks enough shots, visual detail, or asset refs. Candidate asset-card images remain
editable drafts and are excluded from keyframe prompt/context until human
confirmation promotes them to fixed assets; keyframe nodes show missing
candidate cards and block generation before fixed assets exist. Keyframe
polling now reduces repeated full-state saves to lower Runtime pressure during
long image jobs. Verification before merge: full pytest passed 597 / 520
deselected / 2 existing warnings; `npm run check:studio-js` passed for 107
files; CLI help and version passed; full Studio browser QA passed; maintenance
audit failed=0 with warnings only; `git diff --check` passed. Boundary: no
provider raw response, signed URL, local media byte, secret, invite code,
session token, or Company OS private source content was written. Project
lesson to retain: candidate/fixed asset separation must be enforced in
Runtime state, node UI state, and prompt assembly, not only in labels.

Current script review flow addendum: 2026-06-22 pass changed the active
text-to-storyboard chain to the reviewed sequence. Text-node `拆分为分镜` now
routes through Runtime `/storyboard-breakdowns`, uses LLM only behind the LLM
provider gate, falls back to deterministic structured splitting when the gate is
closed, and creates only editable storyboard script nodes. The canvas bottom
workflow toolbar row (`继续生成 / 保存素材 / 整理卡片 / 看过程`) is retired across
nodes. Text, script, and asset-card nodes expose editable scrollable body text,
and node double-click opens the prompt bar while blank-canvas double-click still
opens node creation. Storyboard nodes now gate downstream automation: `识别资产`
creates editable asset-card image nodes from the current reviewed storyboard
text, and `生成关键帧层` requires an existing asset layer rather than silently
creating it. Completed asset image nodes show the generated image preview while
preserving the editable asset draft in `params.assetCardDraft`. Verification:
focused storyboard/API/static regression passed 39 / 1 existing warning; full
pytest passed 592 / 520 deselected / 2 existing warnings; `npm run
check:studio-js` passed for 107
files; CLI help and version passed; full coverage browser QA passed with
console_error_count=0, response_error_count=0, provider_calls_started=false;
maintenance audit failed=0 with warnings only; `git diff --check` passed.
Boundary: provider gates were not opened; no merge, push, deployment, server
sync, generated media, raw provider response, signed URL, local media byte,
secret, invite code, session token, or Company OS private source content was
written; this is local code/runtime evidence, not human acceptance, provider
smoke, business validation, or durable memory promotion.

Current storyboard asset-card and keyframe-layer addendum: 2026-06-22 pass
connected structured storyboard nodes to editable candidate asset cards and a
fixed-asset-only keyframe layer. Script nodes now expose `识别资产` and
`生成关键帧层`; identified角色/场景/道具 become downstream image nodes with
`params.assetCardDraft`, while `params.visualAssets` remains reserved for
human-confirmed fixed assets. Keyframe nodes connect to the storyboard and
asset-card nodes, but inject only fixed visual assets into their prompt/context
and record unconfirmed candidate nodes as missing. Prop assets are now supported
across Studio panels, summaries, drawer actions, Runtime draft/promotion
contracts, context asset limits, and asset-card drafting. Verification: full
pytest passed 587 / 520 deselected / 2 existing warnings; `npm run
check:studio-js` passed for 107 files; CLI help and version passed; full
coverage browser QA passed; maintenance audit failed=0 with warnings only; `git
diff --check` passed with CRLF/LF warnings only. Boundary: provider gates were
not opened; no merge, push, deployment, server sync, raw provider response,
signed URL, local media byte, secret, invite code, session token, or Company OS
private source content was written; this is code/runtime evidence, not human
acceptance, provider smoke, business validation, or durable memory promotion.

Current prompt/template and provider cleanup addendum: 2026-06-21 pass repaired
the reference-image prompt contract that was leaking old human-edit wording into
animal image flows. Active prompt sections now use `角色/主体`; animal reference
flows preserve fur, markings, eyes, ears, tail, and body ratio while treating
old asset signatures and default locks as lower-priority context. Explicit
animal clothing/stylization requests are allowed only when the user asks for
them, preventing the previous conflict between "cat dancing" and human
short-hair/uniform constraints. Minimax image/provider paths were removed from
the active registry, CLI, posterflow provider, smoke helpers, and preflight
tools; only negative compatibility tests remain. Prompt optimization now runs
inline with shimmer feedback instead of a blocking modal, fixed assets can be
reopened for adjustment, and the Codex image worker can recover stable
candidate files from stale/running jobs. Verification: full pytest passed 582 /
520 deselected / 2 existing warnings; `npm run check:studio-js` passed for 102
files; CLI help and version passed; maintenance audit failed=0 with warnings
only; `git diff --check` passed with existing CRLF/LF warnings only. Boundary:
video provider execution remains out of scope; this is code/runtime evidence,
not human acceptance, business validation, or durable memory promotion.

Current text-to-storyboard authoring addendum: 2026-06-22 pass moved text-node
script import and idea expansion results into the node body instead of the
bottom prompt input, with a visible shimmer state while the source text is being
expanded. Text nodes now hide the selected-node workflow toolbar to remove the
`继续生成 / 保存素材 / 整理卡片 / 看过程` clutter from script drafting. Script
breakdown now creates structured storyboard script nodes with explicit `镜号 /
时长 / 画面描述 / 景别 / 光影氛围 / 运镜 / 对白/旁白 / 音效 / 资产` fields and
candidate `@` asset references, then spawns downstream image asset-prep nodes
for the identified角色/场景/道具 candidates. Verification: prompt/script
focused static tests passed 5; Studio static regression set passed 30;
`npm run check:studio-js` passed for 102 files; full coverage browser QA passed
with `provider_calls_started=false`; `git diff --check` passed with existing
CRLF/LF warnings only. Boundary: asset-prep nodes are candidates only, not
fixed assets, durable memory promotion, human acceptance, provider smoke, or
business validation; no Runtime API shape, provider gate, server state, secret,
signed URL, session token, invite code, provider raw response, local media byte,
or Company OS private source content was written.

Current authenticated media and TuanTuan stability addendum: 2026-06-21 pass
fixed broken uploaded/reference image rendering in image nodes and the asset
drawer without weakening Runtime media auth. Studio now fetches protected
`/projects/...` media with the current logged-in session and assigns blob URLs
at render boundaries for node previews, candidate grids, job thumbnails,
downloads, and asset thumbnails. TuanTuan now rejects LLM prompt/persona echo,
falls back to safe first-person replies, preserves chat scroll across rerenders,
and avoids full redraw during IME composition so Chinese input does not lose
focus. Codex image handoff polling can recover a stable generated candidate
from a job still marked running, and Studio startup/project switch now performs
a one-shot refresh for image nodes still marked `generating`, reducing stale
progress failures after a page refresh or interrupted session. Runtime poll
also now recovers a stale terminal failed/blocked state when the Codex handoff
worker has already written a completed safe candidate result. Verification:
focused regression passed 33 / 1 existing warning; Codex handoff regression
passed 9 / 1 existing warning; keyframe/frontend regression passed 22 / 1
existing warning; full pytest passed 575 / 527
deselected / 2 existing warnings; `npm run check:studio-js` passed for 99
files; CLI help and version passed; maintenance audit failed=0 with warnings
only and oversized warning count reduced from 37 to 36 after moving protected
media DOM logic into a single-purpose helper; `git diff --check` passed.
Boundary: video remains out of scope; backend media auth was not opened; no
provider raw response, signed URL, local media byte, secret, invite code,
session token, or Company OS private source content was written; not human
acceptance, business validation, or durable memory promotion.

Current non-video Codex flow and Studio feedback repair addendum: 2026-06-21
pass fixed the image handoff worker's Codex CLI resolution for service
environments, restored readable prompt optimizer retry instructions, tightened
TuanTuan's first-person persona prompt, hard-limited TuanTuan LLM replies to
two sentences / 220 characters, added a visible TuanTuan pending state, moved
media quality feedback to the node right-click menu, made completed image nodes
fill their node body, and adjusted prompt bar placement to avoid the selected
node. Verification: full pytest passed 562 / 527 deselected / 2
existing warnings; `npm run check:studio-js` passed for 96 files; CLI help and
version passed; local Playwright smoke on 8797 passed image fill, right-click
feedback, prompt-bar avoidance, TuanTuan pending state, and no internal
Codex/server wording; `git diff --check` passed. Boundary: video remains out
of scope; no provider raw response, signed URL, local media byte, secret,
invite code, session token, or Company OS private source content was written;
browser smoke used intercepted Studio state and sprite response, not human
acceptance or business validation.

Current public edge and TuanTuan usability addendum: 2026-06-21 pass reduced
the default TuanTuan canvas footprint from 260 x 238 to 232 x 212 and lowered
the default scale to 0.9. The sprite settings panel now supports `关闭团团`,
persisted through `afs_studio_sprite_hidden`, and a small `显示团团` restore
chip keeps the feature reversible without clearing browser storage.
Verification: focused sprite/runtime tests passed 6 / 1 existing warning;
`npm run check:studio-js` passed for 96 files. Public edge status remains
`blocked_by_edge_basic_auth`; server dry-run for
`tools.afs_public_edge_nginx_fix --config /etc/nginx/sites-available/afs-runtime`
returned `ready_to_apply` and `target_line_count=2`, but the file is root-owned
and the current SSH user lacks passwordless sudo, so the Nginx removal still
needs one interactive sudo application. Boundary: no Runtime API shape changed,
no provider gate/config/call, no invite code/session token/provider raw
response/signed URL/local media byte/secret was written; not invite-login
acceptance, human acceptance, business validation, or durable memory promotion.

Current server Codex LLM path addendum: 2026-06-21 pass verified local
`master`, `origin/master`, server `/home`, and server `/opt` were aligned at
`0205148`. The deployed TuanTuan fallback was traced to the Runtime systemd
environment not resolving the local `codex` executable, even though the sprite
route already used the unified LLM dispatch. Server-local `codex_local`
provider services were pointed at `/home/afs-ops/.local/bin/codex`, then
provider-level and Runtime route smoke checks for `sprite_chat` passed with
`provider_calls_started=true` and `mode=llm`. Local code now wraps a missing
Codex CLI as `ModelGatewayError` with a regression test. Verification:
provider/sprite/registry focused tests passed 37 / 1 existing warning.
Boundary: video remains disabled; no ASR or external-download gate was opened;
no provider raw response, invite code, session token, signed URL, local media
byte, secret, or Company OS private source content was written; public
authenticated browser UI chat remains a separate human-session check.

Current TuanTuan reference-shape lock addendum: 2026-06-20 pass fixed,
calibrated, and then reset the Studio `story-cat` visual baseline around the
latest user-approved dark TuanTuan reference. The default canvas companion is
now a low-profile dark tabby story cat with a wider resting body, larger
triangular ears, brighter inner ear rims, black pupils with blue-white
highlights, a quiet sprout, forepaws, rear paw, closed curled tail, body tabby
marks, whiskers, and a cyan story orbit. The story belly panel remains a
low-opacity internal symbol so TuanTuan reads as a canvas-native story cat
rather than a robot or sticker. The implementation remains DOM/SVG/CSS instead
of raster pose swaps, preserving a path toward continuous interaction.
Verification: focused sprite static test passed; `npm run check:studio-js`
passed for 96 files; in-app browser render smoke confirmed viewBox `0 0 390
230`, ears=2, innerEars=2, eyes=2, pupils=2, tailShapes=1, tabbyMarks=4,
orbitNodes=5, state=observe, and no old PNG/sticker sprite path.
Boundary: no Runtime API shape changed, no provider gate/config/call, no local
reference image, provider raw response, signed URL, media byte, invite code, or
secret was exposed; not final IP acceptance, human acceptance, business
validation, or durable memory promotion.

Current Studio mascot and edge disconnect addendum: 2026-06-19 pass made two
front-end interaction improvements requested during Studio polish. The movable
`AFS 小精灵` now uses a cartoon mascot skin through
`apps/studio/styles/studio-sprite-avatar-mascot.css`, opens a small settings
panel on right-click, and persists local size choices through
`afs_studio_sprite_scale`. Canvas connections now support natural removal:
clicking an edge selects it, a compact inline disconnect control appears on the
line, and Delete / Backspace removes the selected connection through the same
store mutation path. Verification: sprite and edge tests first failed on the
missing mascot skin and missing edge-action module, then passed after
implementation; focused Studio/sprite regression passed 28 / 1 existing warning;
`npm run check:studio-js` passed for 94 files; browser smoke confirmed the
mascot rendered, size persisted, old mechanical body stayed hidden, and the
real render-chain edge disconnect removed edge `e1`; maintenance audit
failed=0 with warnings only; `git diff --check` passed with one CRLF
normalization warning for `apps/studio/src/nodes.js`. Boundary: no Runtime API
shape changed, no provider gate changed, no provider config changed, no
provider call was made, and no provider raw response, signed URL, local media
byte, local path, invite code, or secret was exposed; not human acceptance or
business validation.

Current Studio generation action module split addendum: 2026-06-19 pass split
`apps/studio/src/node-actions.js` from a 446-line mixed action/generation module
into an 80-line top-level node action router plus focused generation helpers:
`node-keyframe-actions.js` for keyframe submit/poll/result persistence and
`node-video-actions.js` for video first-frame setup, video submit/poll/cancel,
and experimental video revision state. Existing public imports remain available
through `node-actions.js`, so prompt bar, node menu, and canvas action handlers
do not change their call surface. Verification: structure tests first failed on
missing `node-keyframe-actions.js` and then on missing `node-video-actions.js`;
after implementation Studio static regression passed 43; wider Studio/runtime
focused regression passed 60 / 1 existing warning; `npm run check:studio-js`
passed for 90 files; full pytest passed 536 / 527 deselected / 2 existing
warnings; maintenance audit failed=0 with warnings only and oversized warning
count dropped from 34 to 33, with `node-actions.js` removed from oversized
findings; local HTTP static checks returned 200 for `/studio/`,
`/studio/src/node-keyframe-actions.js`, and `/studio/src/node-video-actions.js`;
`git diff --check` passed. Boundary: no Runtime API shape changed, no provider
gate changed, no provider config changed, no provider call was made, no Studio
UI behavior was intentionally changed, and no provider raw response, signed
URL, local media byte, local path, invite code, or secret was exposed; not human
acceptance or business validation.

Current LLM enhancement module split addendum: 2026-06-19 pass split
`apps/api/runtime_llm_enhancement.py` from a 600+ line prompt optimization
runtime module into a 181-line orchestration surface plus focused helpers:
`runtime_llm_enhancement_constants.py`, `runtime_llm_enhancement_gate.py`,
`runtime_llm_enhancement_safety.py`, `runtime_llm_enhancement_instructions.py`,
`runtime_llm_enhancement_fallback.py`, and
`runtime_llm_enhancement_dispatch.py`. The route-facing module keeps existing
compatibility exports and monkeypatch seams, including `load_provider_registry`,
`llm_provider_gate`, `provider_text_requested`, `sanitize_enhanced_prompt`, and
`deterministic_chinese_fallback_prompt`, while the helper modules keep provider
selection, safety parsing, fallback prompt construction, instruction assembly,
and dispatch fallback under separate maintenance thresholds. Verification:
structural split test first failed on missing helper modules, then passed after
implementation; UTF-8 label guard was added to prevent Chinese prompt contract
drift; LLM prompt-memory regression passed 18 / 1 existing warning; wider
focused Runtime set passed 59 / 1 existing warning; full pytest passed 536 /
527 deselected / 2 existing warnings; CLI help and version passed; maintenance
audit failed=0 with warnings only; `git diff --check` passed. Boundary: no
Runtime API shape changed, no provider gate changed, no provider config changed,
no provider call was made, and no provider raw response, signed URL, local media
byte, local path, or secret was added to API payloads or reports; not human
acceptance or business validation.

Current sprite companion personality polish addendum: 2026-06-19 pass refined
the movable `AFS 小精灵` from a parts-heavy helper into a clearer Studio
navigator character. The widget now declares `data-sprite-character="navigator"`
and adds a halo crown, glass helmet, face window, small wand, and personality
tag, with the final silhouette isolated in
`apps/studio/styles/studio-sprite-avatar-personality.css` so existing sprite
CSS files stay below the maintenance threshold. Verification: sprite static
test first failed on the missing character-shape contract, then passed after
the implementation; `npm run check:studio-js` passed for 88 files; browser QA
on `127.0.0.1:8797/studio/` confirmed the new parts rendered, cursor was
`grab`, drag moved the sprite from `(558, 191)` to `(478, 151)`, opening the
panel kept the moved position, and console warn/error count was 0. Boundary:
no Runtime API shape changed, no provider gate changed, no provider call, no
provider raw response, signed URL, local media byte, or secret exposure; not
human acceptance or business validation.

Current video routes module split addendum: 2026-06-19 pass split
`apps/api/runtime_video_routes.py` from a 739-line route/orchestration module
into a 105-line route assembly surface plus focused helpers:
`runtime_video_constants.py`, `runtime_video_gate.py`,
`runtime_video_prompt.py`, `runtime_video_candidates.py`,
`runtime_video_manifest.py`, `runtime_video_task_state.py`, and
`runtime_video_dispatch.py`. The route module keeps the compatibility exports
used by existing tests, including `VideoGenerationRequest`,
`load_provider_registry`, and `_video_provider_prompt`, while dispatch receives
the registry loader by dependency injection so existing monkeypatch tests keep
covering provider-gate behavior. Verification: structural split test first
failed on missing helper modules, then passed after the split; video/runtime
focused regression passed 17 / 1 existing warning; wider video, manifest,
ModelCallContext, internal-beta, and three-end focused set passed 34 / 1
existing warning; maintenance audit failed=0 with warnings only and oversized
warning count dropped from 36 to 35; `git diff --check` passed. Boundary: no
Runtime API shape changed, no provider gate changed, no provider call, no
provider config, local media byte, local path, signed URL, provider raw
response, invite code, or session token was added to API payloads or reports;
not human acceptance or business validation.

Current sprite companion redesign addendum: 2026-06-19 pass reworked the
movable `AFS 小精灵` visual layer from a subtle component cluster into a more
recognizable Studio companion. The avatar footprint was expanded to 180 x 206,
with a stronger silhouette, visible drag handle, clearer eyes/visor, arms,
feet, scarf, status light, and docking label. Position clamping now uses the
larger character bounds while preserving viewport-only local persistence and
the existing Runtime `sprite/chat` boundary. Verification: sprite/Studio
focused regression passed 16 / 1 existing warning; `npm run check:studio-js`
passed for 88 files; browser QA on `127.0.0.1:8797/studio/` confirmed role
parts rendered, cursor=grab, drag moved the sprite from `(628, 228)` to
`(558, 191)`, opening the panel kept the same position, panel docked below in
the top half of the viewport, and console warn/error count was 0; maintenance
audit failed=0 with warnings only and the new CSS file stayed under the
maintenance line threshold; `git diff --check` passed. Boundary: no provider
gate changed, no provider call, no provider raw response, signed URL, local
media bytes, or secret exposure; not human acceptance or business validation.

Current Studio state module split addendum: 2026-06-19 pass split
`apps/api/runtime_studio_state.py` from a route plus sanitizer file into a thin
route module and focused safe-state helpers:
`runtime_studio_state_sanitizer.py`, `runtime_studio_state_context.py`,
`runtime_studio_state_assets.py`, and `runtime_studio_state_preview.py`.
The public `sanitize_studio_state` compatibility export remains available
from the route module, while preview URL allow-listing, context bundle
projection, and asset-list sanitization now have separate regression coverage.
Verification: Studio state focused regression passed 10 / 1 existing warning;
Runtime/internal-beta focused set passed 32 / 1 existing warning; full pytest
passed 534 / 527 deselected / 2 existing warnings; maintenance audit failed=0
with warnings only and oversized warning count dropped from 37 to 36;
`git diff --check` passed. Boundary: no Runtime API shape changed, no auth
policy changed, no provider gate changed, no provider call, no local path,
signed URL, provider raw response, media byte, invite code, or session token
was added to persisted Studio state; not human acceptance or business
validation.

Current internal beta acceptance split addendum: 2026-06-19 pass split HTTP
preflight readiness logic out of `tools/afs_internal_beta_acceptance.py` into
`tools/afs_internal_beta_acceptance_preflight.py`, and moved the shared
configuration error into `tools/afs_internal_beta_acceptance_errors.py`. The
runner now remains a thin CLI/in-process/HTTP acceptance wrapper while
continuing to export `run_http_preflight` for existing callers. The preflight
contract still reports Runtime `/health`, `/auth/status`, Studio static
readiness, provider gate projection, and optional safe three-end status without
requiring invite codes or starting provider calls. Verification: red/green
split test added; internal beta plus three-end focused regression passed 16 /
1 existing warning; full pytest passed 531 / 527 deselected / 2 existing
warnings; maintenance audit failed=0 with warnings only and oversized warning
count dropped from 40 to 39; `git diff --check` passed. Boundary: no provider
gate changed, no provider call, no invite code/session token/base URL/local
path/signed URL/provider raw/media byte added to reports; not human acceptance
or business validation.

Current sprite companion design addendum: 2026-06-19 pass strengthened the
decorative `AFS 小精灵` from a floating helper into a clearer movable companion.
The avatar now declares `data-sprite-role="movable-companion"` and adds a hood,
explicit left/right eyes, torso panel, nameplate, and visible drag hint while
preserving the existing Runtime `sprite/chat` boundary. Pointer capture is now
defensive so browser automation or synthetic pointer events cannot break drag
startup. Verification: sprite static test passed; Runtime sprite regression
passed 6 / 1 existing warning; Studio JS syntax check passed for 88 files;
full pytest passed 530 / 527 deselected / 2 existing warnings; maintenance
audit failed=0 with warnings only; `git diff --check` passed; Chrome
automation on `127.0.0.1:8797/studio/` confirmed character parts rendered,
drag moved and persisted viewport position, panel open kept position stable,
green open status light, and zero console warn/error. Boundary: no provider
gate changed, no provider call, no provider raw response, no signed URL, no
local media bytes, no secret exposure; not human acceptance or business
validation.

Current sprite draggable character addendum: 2026-06-19 pass made the
decorative `AFS 小精灵` more clearly movable and character-shaped. The avatar
now includes a dedicated character silhouette layer, visible move handle,
left/right ear fins, scarf accent, and keyboard arrow-key nudging in addition
to pointer dragging. The visual shell was split into
`apps/studio/styles/studio-sprite-avatar-character.css` to keep existing
sprite files under the project maintenance warning line. Verification:
sprite static test passed; Studio JS syntax check passed for 87 files; focused
Runtime sprite tests passed; in-app browser on `127.0.0.1:8797/studio/`
confirmed role parts rendered, pointer drag movement, arrow-key movement,
panel-open position stability, green open status light, and zero console
warn/error. Boundary: no provider gate changed, no provider call, no provider
raw response, no signed URL, no local media bytes, no secret exposure; not
human acceptance or business validation.

Current HTTP preflight three-end addendum: 2026-06-19 pass connected the safe
three-end status reporter into `tools/afs_internal_beta_acceptance.py
--preflight-only` through explicit `--three-end-status`,
`--three-end-repo-root`, and `--three-end-server` parameters. The resulting
preflight report can now include local/GitHub/server drift state alongside
Runtime `/health`, `/auth/status`, Studio static readiness, and provider gate
projection. If three-end status is not `aligned`, the report becomes
`needs_attention` even when Runtime health passes. The collection and
whitelist projection live in `tools/afs_internal_beta_preflight_three_end.py`
so the new safety projection stays isolated from the acceptance runner; the
runner itself remains an existing maintenance split candidate. Verification:
preflight tests 10 passed / 1 warning; three-end plus preflight focused tests
15 passed / 1 warning; CLI help exposes the new flags. Boundary: no provider
gate changed, no provider call, no invite code/session token/base URL/local
path/signed URL/provider raw/media byte in the report; not human acceptance or
business validation.

Current sprite character design addendum: 2026-06-19 pass reworked the
decorative `AFS 小精灵` from a button-like floating helper into a clearer
movable canvas companion. It now has a larger fixed footprint, visible drag
chip, cockpit glass, canopy highlight, scanner visor, cheek/mouth detail,
status light, shoulders, arms, mittens, wings, feet, tail fin, dock ring, glow
trail, and thruster. Dragging remains available from the avatar and panel
header, the position clamp separates width and height, and only viewport
coordinates are persisted in local storage. Limb and propulsion styles live in
`apps/studio/styles/studio-sprite-avatar-parts.css` so sprite files remain
under the project maintenance warning line. Verification: sprite static plus
Runtime sprite tests 6 passed / 1 warning; Studio JS syntax check passed for 87
files; `git diff --check` passed; browser check on `127.0.0.1:8799/studio`
confirmed character parts=8, avatar drag movement, panel-header drag movement,
position storage, panel open state, viewport clamp, green open status light,
and console warn/error count=0. Boundary: no provider gate changed, no provider
call, no provider raw response, signed URL, local media bytes, or secret
exposure; not human acceptance or business validation.

Current three-end status addendum: 2026-06-19 pass added
`tools/afs_three_end_status.py` as a safe local/GitHub/server status reporter.
It checks the local checkout, optional server `/home` checkout, optional server
`/opt` checkout, and Runtime `/health` using safe fields only. The report
captures commit alignment, dirty state, Studio static readiness, auth
readiness, and provider gate booleans without recording provider config,
server-local runtime paths, signed URLs, session tokens, provider raw
responses, media bytes, or secrets. Empty or failed checked health is now
treated as `needs_attention` rather than silent success. Verification:
three-end status tests 5 passed; three-end plus beta acceptance focused tests
13 passed / 1 warning; full pytest passed 528 / 527 deselected / 2 warnings;
maintenance audit failed=0 with warnings only; `git diff --check` passed.
Boundary: ops/readiness report only, not git pull/deploy/restart automation,
not provider smoke, not human acceptance, not business validation, not
durable-memory promotion.

Current HTTP internal beta preflight addendum: 2026-06-19 pass added
`--preflight-only` to `tools/afs_internal_beta_acceptance.py`. This mode checks
deployed Runtime readiness through `/health` and `/auth/status` without
requiring disposable invite codes and without executing the full acceptance
contract. The safe report covers runtime health, auth surface, Studio static
readiness, provider gate projection, and non-claims while excluding base URLs,
invite codes, session tokens, signed URLs, provider raw responses, media bytes,
and local paths. Verification: preflight tests 8 passed / 1 warning; local dev
preflight against `127.0.0.1:8797` returned `needs_attention` because
`auth_required=false`, with `provider_calls_started=false`; CLI help/version
passed; full pytest passed 523 / 527 deselected / 2 warnings; maintenance audit
failed=0 with warnings only; `git diff --check` passed. Boundary: readiness
inspection only, not full HTTP beta acceptance, not provider smoke, not human
acceptance, not business validation, not durable-memory promotion.

Current HTTP internal beta acceptance addendum: 2026-06-19 pass extended
`tools/afs_internal_beta_acceptance.py` from in-process deterministic contract
verification to deployed Runtime HTTP contract verification. The tool now
accepts `--base-url` and disposable invite codes via CLI flags or
`AFS_INTERNAL_BETA_ACCEPTANCE_INVITE_CODE` /
`AFS_INTERNAL_BETA_ACCEPTANCE_INVITE_CODE_BETA`, generates isolated project
IDs and emails per run, and keeps reports free of invite codes, session tokens,
passwords, base URLs, local paths, provider raw responses, signed URLs, and
media bytes. HTTP mode requires two disposable invite codes so the alpha/beta
project-isolation checks exercise separate users. The HTTP client disables system proxy inheritance with
`trust_env=False` to connect directly to the target Runtime. Verification:
acceptance tests 6 passed / 1 warning; default in-process runner returned
`contract_verified_pending_human_acceptance`; HTTP missing-invite mode returned
safe `configuration_error`; temporary local Runtime HTTP smoke returned
`deployed_http_runtime`, 12 steps, 0 failed, provider_calls_started=false; full
pytest passed 521 / 527 deselected / 2 warnings; maintenance audit failed=0
with warnings only; `git diff --check` passed.
Boundary: deployed Runtime contract verification only, not live provider smoke,
not human acceptance, not business validation, not durable-memory promotion.

Current sprite avatar polish addendum: 2026-06-19 pass strengthened the
decorative `AFS 小精灵` into a more recognizable movable canvas companion. The
avatar now has an explicit drag halo, larger body shell, head shell, visor, core
light, side wings, feet, and bottom thruster; the fixed layer sits above modal
level so the sprite remains reachable while Studio panels are open. The drag
state now remembers the current DOM position before re-rendering, preventing a
post-drag panel-open click from jumping the sprite back to an older stored
position. Verification: focused sprite static test passed; Studio static plus
Runtime sprite regression 16 passed / 1 warning; Studio JS syntax check passed
for 87 files; `git diff --check` passed; browser check on
`127.0.0.1:8797/studio` confirmed avatar parts, z-index=81, avatar drag,
open-panel position delta=0, panel-header drag, and console warn/error count=0.
Boundary: no provider gate changed, no provider call, no generated media byte
persistence, no human acceptance, no business validation, no durable-memory
promotion.

Current sprite character follow-up: 2026-06-19 pass reworked the decorative
`AFS 小精灵` into a fixed-viewport micro-assistant character instead of a
generic floating control. The avatar now has a recognizable visor, glowing
core, side stabilizers, feet, antenna, shadow, and docking label; it can be
moved by dragging the avatar or the open panel header. The idle breathing
motion now runs on the inner body rather than the clickable shell, keeping the
hit target stable for browser automation. Verification: browser check on
`127.0.0.1:8797/studio` confirmed fixed layer, avatar drag, panel-header drag,
character parts present, and console warn/error count=0; Studio static
regression 11 passed; sprite Runtime regression 5 passed / 1 warning; Studio
JS syntax check passed for 87 files; `git diff --check` passed. Boundary: no
provider gate changed, no provider call, no generated media byte persistence,
no human acceptance, no business validation, no durable-memory promotion.

Current Studio panels and sprite assistant addendum: 2026-06-19 pass fixed the
remaining persistent-edge gap by anchoring saved edges to the node frame
boundary while keeping drag previews tied to the plus port. The Studio shell now
has a draggable left drawer width, collapsible right inspector, and
non-selectable chrome with form fields still selectable. A decorative `AFS
小精灵` was added through Runtime endpoint
`/projects/{project_id}/sprite/chat`; it uses the unified LLM dispatch only
when the LLM gate is ready, otherwise returns local safe rule replies. The
sprite can be dragged around the viewport, persists its local position, adapts
its panel to left/right and top/bottom docking, and now has a recognizable
micro-assistant body/visor/side-fin/antenna silhouette instead of a generic
floating button. It does not execute actions, expose local paths, return
provider raw responses, bypass project-owner auth scope, or write durable
memory. A deterministic internal beta acceptance runner now covers auth scope,
project isolation, image assets, draft-vs-fixed asset lifecycle, context reuse,
feedback evidence, artifact scope, and video gate-closed behavior without
opening providers; it is split across small tool modules to avoid new oversized
maintenance debt. Verification: focused Studio/Runtime regression 26 passed / 1
warning; internal beta acceptance runner reports
`contract_verified_pending_human_acceptance`; full pytest 517 passed / 527
deselected / 2 warnings; `npm run
check:studio-js` passed for 87 files; CLI help/version passed; maintenance
audit failed=0 with warnings only; `git diff --check` passed with Windows CRLF
notice only. In-app browser automation was blocked by Browser URL policy for
the local Studio URL in this pass, so movable-avatar visual acceptance is not
claimed. Remaining non-blocking warnings are existing maintenance-audit
warnings for legacy frozen surfaces, Chinese-doc coverage, secret-like
test/config fragments, and oversized files.

Current deep hardening addendum: 2026-06-19 pass completed and was merged to
`master` through `fda2dcafb3a5609deddc9e4ad664b6be060cb053`, then aligned
across GitHub, server `/home`, and server `/opt`. The work strengthened
internal beta usability, homepage product framing, Studio operation feel, and
frontend structure while preserving provider gates. Implemented: `/health`
runtime-root persistence is a safe boolean projection; cross-user auth tests now
cover Studio state, image assets, image previews, jobs, and artifact manifests;
homepage first viewport is more directly positioned as a professional AI video
creation entry; inspector defaults to next action and current reference summary
with details folded; edge anchors use visible port centers; selected edge flow
is lighter/slower; port magnet vertical range is tighter; generating text
shimmer is slower; `main.js` project lifecycle logic moved into
`studio-project-controller.js`; `npm run check:studio-js` added. Verification:
Studio/Site JS syntax check passed for 86 files; focused Runtime/Studio
regression passed 69 / 1 warning; Runtime CLI now maps `AFS_RUNTIME_ROOT` into
`--runtime-root`; full pytest passed 508 / 527 deselected / 2 warnings; CLI
help/version passed with version 0.1.0 and runtime-service help shows
`AFS_RUNTIME_ROOT`; maintenance audit failed=0 with warnings only; `git diff
--check` passed. Boundary: no video gate opened, no new provider introduced, no
provider raw/signed URL/secret/media byte persistence, no human acceptance or
business validation claimed. Maintenance ledger:
`docs/maintenance/AFS-DEEP-UX-RUNTIME-HARDENING-20260619.md`. Closeout:
`docs/handoff/AFS-DEEP-UX-RUNTIME-HARDENING-CLOSEOUT-20260619.md`.

Current frontend hardening addendum: 2026-06-19 pass continued Studio UX
hardening after edge and homepage review. Root `/` now leads with the AI video
creation entry and keeps the six core algorithms behind a folded technical
boundary instead of a primary section. `/studio/` now separates asset lifecycle
states in the asset drawer, redraws on asset search/filter state changes, and
shows right-inspector summaries for included context, excluded context, and
asset confirmation state; object-shaped context warnings are rendered through
safe summary fields rather than raw objects. Canvas edges are thinner by default
and selected-node related edges now render a directional spark overlay: upstream
selection flows forward, downstream selection reverses; the selected-edge spark
was slowed and generating/optimizing/running text now has a subtle shimmer with
reduced-motion fallback. Verification so far:
browser QA on
`127.0.0.1:8797` confirmed homepage entry/no horizontal overflow/no console
warn-error, selected edge forward/reverse spark, `1.35px` default edge width,
`1.75px` associated edge width, lifecycle filter redraw, and inspector context
copy. Current-scope maintainability risks from this pass were closed by
splitting edge SVG styles into `canvas-edges.css` and splitting the broad Studio
static regression file into focused asset/generation and mature-shell test
files; focused Studio/Site static and interaction regression 46 passed;
post-split focused Studio static and edge regression 33 passed; changed
Studio/Site JS `node --check` passed; generating-feedback and mature-shell
regression 20 passed; browser style verification confirmed
`generation-feedback.css` loaded, selected-edge spark duration 2.6s,
generating-text shimmer duration 3.2s, and console warn/error count=0; full
default pytest passed 493 / 527 deselected / 2 warnings; maintenance audit
failed=0 with warnings only; `git diff --check` passed with the existing CRLF
notice on `apps/studio/styles/assets.css`. Boundary: no provider call, no
generated media bytes, no human acceptance, no business validation, no
durable-memory promotion.

Current frontend closeout addendum: 2026-06-19 pass fixed Studio port geometry
and homepage entry. Root `/` now serves the new professional AI video creation
homepage; `/studio/` inspector is reduced to next action, current reference
summary, drawer links, and collapsed trace/details. Pending drag lines originate
from visible plus ports, persisted connection paths anchor to node frame
boundaries with port-aligned vertical placement, default stable edges are solid
round-capped lines, left/right magnet states are distinct, and vertical magnet
range is bounded. Verification: browser QA on `127.0.0.1:8797` confirmed
homepage/cards/no horizontal overflow, inspector declutter, frame-attached edge
alignment, drag-follow with edge opacity=1, left/right magnet behavior, far-y
magnet clearing, and zero console warn/error; focused frontend/runtime tests 46
passed; Studio/Site JS `node --check` passed for 82 files; full `pytest -q` 491
passed / 527 deselected / 2 warnings; CLI help/version passed; maintenance audit
failed=0 with warnings only; `git diff --check` passed with the existing CRLF
notice. Boundary: no provider call, no human acceptance, no business validation,
no durable-memory promotion.

Current closeout note: Loop 005 baseline is green after moving local input
Markdown files out of the repository root and generalizing retention review for
root-level untracked Markdown inputs. Studio pages opened on local static/dev
ports now fall back to Runtime Service `http://127.0.0.1:8790`, fixing the
`Failed to fetch` path seen on stale `8796/studio` sessions. Verification:
`pytest -q` 386 passed / 527 deselected; `pytest -m legacy -q` 527 passed / 386
deselected; Studio JS `node --check` 37 files passed; maintenance audit
failed=0; `git diff --check` exit 0.

Current browser acceptance addendum: The 2026-06-15 Browser drill used an
isolated branch and external evidence root, opened only LLM/image/video gates,
and kept ASR plus external download closed. Browser/runtime coverage passed
project persistence, T2I, fixed assets, Kling I2V, safe preview, and responsive
checks. The initial Path 3 gap was closed after explicit user approval for one
additional MiniMax image call: the Browser rerun completed true reference-backed
I2I with `reference_image_count=1`, `candidate_count=1`, and no provider
raw/media-byte persistence in the safe manifest. The drill is now AI/browser
pre-acceptance `recommended`, pending the user's human acceptance and creative
quality scoring.

Final verification passed on the browser-drill branch: default pytest 406
passed / 527 deselected; legacy pytest 527 passed / 406 deselected; Studio JS
`node --check` 37 files passed; maintenance audit failed=0 with warnings only;
`git diff --check` exit 0.

Continuation verification after the authorized Path 3 rerun: focused readiness
and reference-asset tests 11 passed / 1 warning; readiness audit reports
`recommended`, provider_blocker_count=0, passed_role_count=7; maintenance audit
failed=0 with warnings only; `git diff --check` exit 0.

## Current Work

| ID | Owner role | Scope | Status | Evidence |
|---|---|---|---|---|
| AFS-STUDIO-VISUAL-ASSET-PANEL-SPLIT-20260619 | Studio Interaction Designer + Frontend Maintainability Steward + QA Gatekeeper | Split visual asset confirmation rendering out of the asset review workflow so the panel stays under the 300-line threshold while preserving draft-card, fixed/rejected review, and safe store projection behavior. | Local verification completed. Focused Studio static tests passed; Studio JS syntax check passed; browser load check passed with no console warn/error; full pytest passed; maintenance audit failed=0 and oversized warning count dropped from 33 to 32. Boundary: no provider gate opened, no provider call, no generated media bytes, no human acceptance, no business validation. | `apps/studio/src/panels/visual-asset-panel.js`, `apps/studio/src/panels/visual-asset-panel-render.js`, `tests/test_web_studio_assets_generation_static.py`, `tests/test_web_studio_loop003_static.py`, `DEVLOG.md` |
| AFS-STUDIO-SPRITE-MOVABLE-POLISH-20260619 | Studio Interaction Designer + Frontend UI Reviewer + QA Gatekeeper | Polish the decorative `AFS 小精灵` so it is visibly draggable, keeps a designed companion silhouette, avoids inspector/dock default overlap, and remains on the existing safe Runtime chat boundary. | Local verification completed. Focused sprite static test passed; Studio static + sprite regression passed; Studio JS syntax check passed; full pytest passed; maintenance audit failed=0. Browser check on `127.0.0.1:8797/studio/` confirmed default inspector/dock avoidance and drag movement from `(768,414)` to `(598,315)`. Boundary: no provider gate opened, no provider call, no generated media bytes, no human acceptance, no business validation. | `apps/studio/src/sprite-widget.js`, `apps/studio/src/sprite-position.js`, `apps/studio/styles/studio-sprite-avatar-personality.css`, `tests/test_web_studio_sprite_static.py`, `DEVLOG.md` |
| AFS-COS-GFR-DISPLAY-PACKAGE-V01-20260619 | AI-Native Operating Architect + Product Narrative Editor + QA Gatekeeper + Rule Steward | Source-KB display-package slice: freeze current COS/GFR TaskRun flow map as versioned bilingual SVG/PNG/PDF, rewrite one-page and mechanism HTML toward a restrained evidence-bound narrative, and add a concrete TaskRun example. | Structure/render verification completed. Source JSON parse passed; versioned SVG XML parse passed at 2600x2860; HTML local href/src check passed; Playwright desktop/mobile render check passed with no horizontal overflow, no broken images, and no console warn/error; Company OS contract validator passed; GFR audit passed with checked_paths=41, checked_packets=5, errors=0, warnings=0. Boundary: no Runtime API or Studio code changed in this slice, no provider gate opened, no provider call, no generated media bytes, no human acceptance, no business validation, no durable memory promotion. | Source KB: `03-one-page-html.html`, `08-cos-gfr-deep-dive.html`, `assets/cos-gfr-taskrun-flow-map.v0.1.*`, `taskrun-examples/2026-06-19-cos-gfr-display-package-v0.1.*`, `TASKRUN-LEDGER-V0.json`; AFS repo: `DEVLOG.md`, `TASK_TRACKER.md` |
| AFS-STUDIO-INTERACTION-DETAIL-FIXES-20260619 | Studio Interaction Designer + Frontend UI Reviewer + QA Gatekeeper | Focused follow-up for `/studio/` operation feel: prevent dragged-node edge visual detachment, add side-port magnetic plus feedback, compact the add-node menu, clamp expanded popovers inside the viewport, and bound generated media previews. | Local implementation completed on `master`. Focused interaction tests passed: 7 passed. Studio static + interaction regression passed: 37 passed. Studio JS syntax check passed for 76 files. Browser QA on `127.0.0.1:8797/studio/?project=frontend-fix-overlap-browser` passed right-side port magnet, default compact add menu, expanded scroll-safe menu bounds, drag cleanup with preserved edge count, prompt-bar non-overlap, and console warn/error count=0. Full default pytest passed: 487 passed / 527 deselected / 2 warnings. CLI help/version passed. Maintenance audit failed=0 with warnings only. `git diff --check` exit 0 with Windows CRLF notice on `apps/studio/src/overlay.js` only. Boundary: no Runtime API change, no provider gate opened, no provider call, no generated media bytes, no human acceptance, no business validation, no durable memory promotion. | `apps/studio/src/interaction/port-magnet.js`, `apps/studio/src/interaction/feedback-layer.js`, `apps/studio/src/canvas-input.js`, `apps/studio/src/overlay.js`, `apps/studio/src/panels/add-node-menu.js`, `apps/studio/styles/interaction-motion.css`, `apps/studio/styles/studio-interactions.css`, `apps/studio/styles/node-result.css`, `tests/test_studio_interaction_layer.py`, `DEVLOG.md` |
| AFS-STUDIO-INTERACTION-LAYER-20260619 | Studio Interaction Designer + Frontend UI Reviewer + QA Gatekeeper | First operation-feel slice for `/studio/`: modular interaction layer, drag lift/landing feedback, visible grid/alignment snap guides, edge-follow nudging, bounded inertial pan, and connection-source feedback while keeping Runtime/provider boundaries unchanged. | Local implementation completed on `master`. New interaction tests passed: 4 passed. Studio static + interaction regression passed: 34 passed. Studio JS syntax check passed for 75 files. Browser QA on `127.0.0.1:8797/studio/` passed node drag feedback creation, align snap state, landing feedback, feedback-layer auto-clear, and console warn/error count=0. Full default pytest passed: 484 passed / 527 deselected / 2 warnings. CLI help/version passed. Maintenance audit failed=0 with warnings only. Boundary: no Runtime API change, no provider gate opened, no provider call, no generated media bytes, no human acceptance, no business validation, no durable memory promotion. | `apps/studio/src/interaction/motion-tokens.js`, `apps/studio/src/interaction/pointer-kinematics.js`, `apps/studio/src/interaction/auto-pan.js`, `apps/studio/src/interaction/snap-engine.js`, `apps/studio/src/interaction/feedback-layer.js`, `apps/studio/src/canvas-input.js`, `apps/studio/src/canvas-connection.js`, `apps/studio/styles/interaction-motion.css`, `apps/studio/index.html`, `tests/test_studio_interaction_layer.py`, `DEVLOG.md` |
| AFS-COS-GFR-LOOP-ENGINEERING-V0-20260619 | AI-Native Operating Architect + Rule Steward + QA Gatekeeper | Source-KB loop-engineering slice: LoopSpec v0 schema, TaskRun Ledger v0 schema/object, GFR templates updated to require loop planning, and bilingual SVG distribution diagram for the learning Agent production control system. | Structure verification completed. Company OS contract validator passed including `loop_spec_v0` and `taskrun_ledger_v0`; GFR audit passed with checked_paths=41, checked_packets=5, errors=0, warnings=0; source JSON parse passed; bilingual SVG UTF-8 XML parse passed at 2400x1500; Chrome render check completed with final screenshots reviewed; full default pytest passed 484 / 527 deselected / 2 warnings; maintenance audit failed=0 with warnings only; `git diff --check` passed. Boundary: candidate loop-control structure and distribution asset only; not runtime COS enforcement, provider smoke, human acceptance, business validation, or durable memory promotion. | Source KB: `loop_spec_v0.schema.json`, `taskrun_ledger_v0.schema.json`, `TASKRUN-LEDGER-V0.json`, `2026-06-19-cos-gfr-loop-engineering-v0.*`, `cos-learning-agent-production-loop.zh-CN.svg`, `cos-learning-agent-production-loop.en.svg`; AFS repo: `docs/GFR_EXECUTION_PROJECTION.md`, `DEVLOG.md`, `TASK_TRACKER.md` |
| AFS-INTERNAL-BETA-ENTRY-CONFLICT-GUARD-20260618 | Runtime/API Integrator + Studio Interaction Designer + QA Gatekeeper + Security Boundary Steward | Next internal-test hardening slice: session TTL for invite-gated accounts, optimistic `studio-state` version conflict guard, homepage auth-aware Studio entry, and focused browser QA with provider gates explicitly closed. | Local implementation completed on `codex/cos-gfr-v0-control-layer-20260618`. Focused auth/state/site/studio/OpenAPI regression passed: 63 passed / 1 warning. Changed Studio/site JS syntax checks passed. Browser QA on `127.0.0.1:8810` passed anonymous homepage auth entry, invite registration, account-scoped default project creation/save, authenticated homepage entry, homepage-to-Studio navigation, and console warn/error count=0. Full default pytest passed: 480 passed / 527 deselected / 2 warnings. CLI help/version passed. Maintenance audit failed=0 with warnings only; `git diff --check` passed with Windows CRLF notice only. Boundary: no provider gate opened, no provider call, no local secret provider config edited, no human acceptance, no business validation, no durable memory promotion. | `apps/api/runtime_auth.py`, `apps/api/runtime_studio_state.py`, `apps/api/runtime_service.py`, `apps/site/index.html`, `apps/site/site.js`, `apps/site/styles/site.css`, `apps/studio/src/runtime-client.js`, `apps/studio/src/store.js`, `apps/studio/src/main.js`, `docs/openapi/afs-runtime-service.openapi.json`, `tests/test_api_runtime_auth.py`, `tests/test_api_runtime_studio_state.py`, `tests/test_api_runtime_studio_state_persistence.py`, `tests/test_site_homepage_static.py`, `tests/test_web_studio_static.py`, `.env.example`, `DEVLOG.md` |
| AFS-COS-GFR-V0-CONTROL-LAYER-20260618 | AI-Native Operating Architect + Engineering Delivery Lead + Rule Steward + QA Gatekeeper | First COS/GFR operationalization slice: source-KB COS Registry v0, GFR Packet v0 schema and real task packet, Evidence Ledger v0, candidate feedback packet, plus AFS Runtime safe `GET /company-os/gfr-projection` endpoint and tests. | Local implementation completed on `codex/cos-gfr-v0-control-layer-20260618`. Company OS contract validator passed for new registry/packet/ledger fixtures; GFR audit passed with checked_paths=41, checked_packets=4, errors=0, warnings=0. Focused Runtime tests passed: 13 passed / 1 warning; post-OpenAPI focused Runtime/OpenAPI tests passed: 17 passed / 2 warnings. Full default pytest passed: 476 passed / 527 deselected / 2 warnings. CLI help/version and `git diff --check` passed. Boundary: candidate control-layer slice only, not full COS runtime enforcement, provider smoke, human acceptance, business validation, or durable memory promotion. | Source KB: `COS-REGISTRY-V0.json`, `EVIDENCE-LEDGER-V0.json`, `gfr_packet_v0.schema.json`, `2026-06-18-cos-gfr-v0-control-layer.*`, `2026-06-18-cos-gfr-v0-control-layer.md`; AFS repo: `apps/api/runtime_company_os.py`, `apps/api/runtime_service.py`, `apps/api/runtime_info.py`, `docs/openapi/afs-runtime-service.openapi.json`, `tests/test_api_runtime_company_os.py`, `tests/test_api_runtime_service.py`, `docs/GFR_EXECUTION_PROJECTION.md`, `DEVLOG.md` |
| AFS-INTERNAL-AUTH-INVITE-ISOLATION-20260618 | Runtime/API Integrator + Studio Interaction Designer + QA Gatekeeper + Security Boundary Steward | Add first internal-test account gate: invite-code registration, login sessions, user-owned project filtering, Studio auth gate, account-scoped default project creation, explicit Studio-to-homepage navigation, and non-dismissible auth gate when auth is required. | Local implementation completed on `master`. Auth-focused pytest passed: 3 passed / 1 warning. Focused Runtime/Auth/Studio/Site regression passed: 54 passed / 1 warning. Auth gate/site focused regression after backdrop-lock fix passed: 7 passed / 1 warning. Full default pytest passed: 474 passed / 527 deselected / 2 warnings. CLI help/version, Studio JS syntax check for 70 files, maintenance audit failed=0 with warnings only, and `git diff --check` passed. Runtime HTTP auth smoke on `127.0.0.1:8802` passed for homepage, Studio static, health auth projection, anonymous project rejection, invite registration, project creation, and owned project list. Boundary: internal-test auth only, not full SaaS accounts/roles/sharing; no provider gate opened, no provider call, no human acceptance, no business validation. | `apps/api/runtime_auth.py`, `apps/api/runtime_service.py`, `apps/api/runtime_info.py`, `apps/studio/src/auth-gate.js`, `apps/studio/src/runtime-client.js`, `apps/studio/src/main.js`, `apps/studio/src/studio-topbar.js`, `apps/studio/src/overlay.js`, `apps/studio/styles/modals.css`, `tests/test_api_runtime_auth.py`, `tests/test_web_studio_static.py`, `.env.example`, `DEVLOG.md` |
| AFS-SITE-STUDIO-UX-CONSOLIDATION-20260618 | Frontend Product Designer + Studio Interaction Designer + Runtime/API Integrator + QA Gatekeeper | Consolidate the next-step UX after the site/studio audit: fix homepage product-preview overlap, make the homepage preview a bounded creation-chain layout, and reframe the Studio empty inspector around user creation decisions while keeping algorithm trace available as a folded safe audit surface. | Local implementation completed on `master`. Focused Runtime/site/Studio static regression passed: 42 passed / 1 warning. Full default pytest passed: 470 passed / 527 deselected / 2 warnings. Studio JS syntax check, Runtime HTTP smoke on `127.0.0.1:8801` for `/`, `/studio/`, `/health`, in-app Browser QA, maintenance audit failed=0, and `git diff --check` passed. Boundary: no provider gate opened, no provider call, no local secret provider config edited, no human acceptance, no business validation. | `apps/site/index.html`, `apps/site/styles/site.css`, `apps/site/styles/site-preview.css`, `apps/site/styles/site-responsive.css`, `apps/studio/src/panels/inspector-panel.js`, `apps/studio/src/panels/algorithm-context-panel.js`, `tests/test_site_homepage_static.py`, `tests/test_web_studio_static.py`, `DEVLOG.md` |
| AFS-MODEL-ROUTE-SURFACE-20260618 | Runtime/API Integrator + Studio Product Surface Owner + Provider Gate Steward + QA Gatekeeper | Consolidate current model-route surface: Image/keyframe product path uses Image2 via `codex_image`; prompt optimization uses server-configured `prompt_optimizer` without exposing model identity; visual understanding is split into `vision_image` and `vision_video`; example provider config reflects only current execution projection. | Local implementation completed on `codex/afs-studio-mature-shell-20260618`. Focused model route/runtime/static regression passed: 100 passed / 1 warning. Full default pytest passed: 469 passed / 527 deselected / 2 warnings. Studio JS syntax check, provider example JSON parse, maintenance audit failed=0, and `git diff --check` passed. Boundary: no provider gate opened, no live provider call, no local secret provider config edited, no human acceptance, no business validation. | `apps/studio/src/presets/models.js`, `apps/studio/src/optimizer-contract.js`, `apps/studio/src/panels/visual-asset-panel.js`, `apps/studio/src/main.js`, `apps/api/runtime_models.py`, `apps/api/runtime_llm_enhancement.py`, `apps/api/runtime_asset_card_drafts.py`, `apps/api/runtime_creative_agent.py`, `configs/providers.example.json`, `tests/test_web_studio_static.py`, `tests/test_api_runtime_prompt_memory_loop.py`, `tests/test_provider_adapter_registry.py`, `DEVLOG.md` |
| AFS-SITE-HOMEPAGE-ROOT-20260618 | Frontend Product Designer + Runtime/API Integrator + QA Gatekeeper | Add a real website homepage at Runtime root `/` while keeping `/studio/` as the creative workspace. Homepage introduces AFS Studio, the product preview, workflow, six core algorithms, and direct Studio entry without exposing internal provider/runtime details. | Local implementation completed on `codex/afs-studio-mature-shell-20260618`. Focused Runtime/static regression passed: `tests/test_api_runtime_service.py`, `tests/test_site_homepage_static.py`, and `tests/test_web_studio_static.py` report 41 passed / 1 warning. Boundary: no provider gate opened, no provider call, no human acceptance, no business validation. | `apps/site/index.html`, `apps/site/styles/site.css`, `apps/site/styles/site-preview.css`, `apps/site/styles/site-responsive.css`, `apps/api/runtime_studio_static.py`, `apps/api/runtime_service.py`, `tests/test_api_runtime_service.py`, `tests/test_site_homepage_static.py`, `DEVLOG.md` |
| AFS-STUDIO-DECLUTTER-FOLLOWUP-20260618 | Studio Interaction Designer + Frontend UI Reviewer + QA Gatekeeper | Frontend-only declutter after design review: shrink the top-left workbench into a compact project menu, return creative entry to the canvas starter rail, collapse six-core-algorithm details behind a system-process disclosure, and reduce right-inspector card density. | Local implementation completed on `codex/afs-studio-mature-shell-20260618`. Static Studio regression passed, changed Studio JS syntax checks passed, `git diff --check` passed, and touched/new frontend files remain below the 300-line maintenance warning threshold. In-app browser automation for the local `/studio/` URL was blocked by Browser URL policy in this pass, so this is not a fresh visual/human acceptance claim. Boundary: no Runtime API contract change, no provider call, no human acceptance, no business validation, no durable memory promotion. | `apps/studio/src/project-hub.js`, `apps/studio/src/studio-topbar.js`, `apps/studio/src/panels/inspector-panel.js`, `apps/studio/src/panels/algorithm-context-panel.js`, `apps/studio/styles/studio-workbench.css`, `apps/studio/styles/studio-mature-shell.css`, `apps/studio/styles/studio-inspector-declutter.css`, `tests/test_web_studio_static.py`, `DEVLOG.md` |
| AFS-STUDIO-MATURE-SHELL-20260618 | Studio Interaction Designer + Frontend UI Reviewer + QA Gatekeeper | Frontend-only desktop polish for `/studio/`: mature workbench shell, quick-start workflow rail, right-side six-algorithm production console, and follow-up fixes for inspector overlap plus workbench modal vertical scrolling. | Local implementation completed on `codex/afs-studio-mature-shell-20260618`. Studio static tests passed, all Studio JS files passed `node --check`, `git diff --check` passed, and in-app browser verification on `127.0.0.1:8797/studio/` confirmed starter-flow inspector sections had zero detected overlaps, the workbench modal accepted real wheel scroll to lower content, and console error/warning count was 0. Boundary: no Runtime API contract change, no provider call, no human acceptance, no business validation, no durable memory promotion. | `apps/studio/src/panels/algorithm-context-panel.js`, `apps/studio/src/canvas-starter-rail.js`, `apps/studio/src/panels/inspector-panel.js`, `apps/studio/src/canvas-view.js`, `apps/studio/styles/studio-mature-shell.css`, `apps/studio/styles/studio-workbench.css`, `tests/test_web_studio_static.py`, `DEVLOG.md` |
| AFS-MODEL-CALL-CONTEXT-CONTRACT-20260618 | Engineering Delivery Lead + Runtime/API Integrator + Rule Steward + QA Gatekeeper | First algorithm-contract slice for the six-core-algorithm plan: define `ModelCallContext`, separate core/auxiliary algorithm taxonomy, add request projection and visual-understanding normalization, and wire prompt/keyframe, video generation, visual inspect / asset-card draft, and video revision Runtime artifacts to the same context id discipline. | Local implementation completed on `codex/afs-model-call-context-contract`. Prompt, image/keyframe, video, visual inspect, and revision entrypoints now emit safe algorithm artifacts without opening providers. Full default pytest passed: `464 passed, 527 deselected, 2 warnings`; maintenance audit failed=0 with warnings only; `git diff --check` passed with CRLF notices only; final closeout HTTP smoke passed on `127.0.0.1:8797` with `/health` ready, `/studio/` 200, and runtime client 200. Boundary: no live provider smoke, no human acceptance, no business validation, no durable memory promotion. | `agentflow/algorithms/model_call_context/`, `agentflow/algorithms/request_projection/`, `agentflow/algorithms/visual_understanding/`, `agentflow/algorithms/revision_drift_control/`, `apps/api/runtime_model_call_context.py`, `apps/api/runtime_video_routes.py`, `apps/api/runtime_asset_card_drafts.py`, `apps/api/runtime_video_revision_context.py`, `apps/api/runtime_video_revision_routes.py`, `tests/test_model_call_context_contract.py`, `tests/test_model_call_context_runtime_routes.py`, `docs/architecture/AFS_MODEL_CALL_CONTEXT_CONTRACT.zh-CN.md`, `docs/architecture/AFS_ALGORITHM_LIBRARY.zh-CN.md`, `docs/architecture/AFS_CORE_ALGORITHM_AND_OPERATION_MAP.zh-CN.md`, `docs/handoff/AFS-MODEL-CALL-CONTEXT-CONTRACT-20260618.md` |
| AFS-ALGORITHM-CORE-WAVE2-20260617 | Engineering Delivery Lead + Runtime/API Integrator + QA Gatekeeper | Second algorithm-library migration after provider-flow intake: move i2v/t2v creative-intent logic, video-safe provider prompt projection, reference-asset merge rules, and Studio video first-frame/auto-poll helper logic out of oversized Runtime/Studio files. | Local Wave 2 migration completed with focused and wider Runtime/Studio tests passing. Maintenance audit remains failed=0 with existing warning classes; oversized files remain a tracked maintenance debt, but `node-actions.js` is reduced and new video helper is single-purpose. Boundary: no live provider smoke, no human acceptance, no business validation, no durable memory promotion. | `agentflow/algorithms/creative_intent_control/video_prompt.py`, `agentflow/algorithms/provider_gate_manifest/video_prompt.py`, `agentflow/algorithms/context_resolver/references.py`, `apps/studio/src/video-node-flow.js`, `tests/test_algorithm_library_contracts.py`, `docs/handoff/AFS-ALGORITHM-CORE-WAVE2-20260617.md` |
| AFS-PROVIDER-FLOW-INTAKE-20260617 | Engineering Delivery Lead + Runtime/API Integrator + QA Gatekeeper + Provider Gate Steward | Integrate server-side PR #87 video provider-flow fixes after the GFR baseline: keep reference assets attached, use i2v/t2v prompt semantics, project video-safe Kling prompts, infer upstream keyframes as first frames, auto-poll video jobs, and refresh no-cost readiness. | Local integration completed without conflicts on the Wave 1 branch. Focused Studio JS and Runtime tests passed; no live provider call was started locally. Readiness report is `ready_for_provider_smoke`, but still requires explicit human authorization before spending provider calls. Boundary: server-side Kling smoke is provider-smoke evidence only, not human acceptance or business validation. | `apps/api/runtime_keyframes.py`, `apps/api/runtime_llm_enhancement.py`, `apps/api/runtime_video_routes.py`, `apps/studio/src/node-actions.js`, `apps/studio/src/node-result-view.js`, `apps/studio/src/optimizer-contract.js`, `docs/handoff/AFS-PROVIDER-FLOW-INTAKE-20260617.md`, `docs/handoff/AFS-PROVIDER-FLOW-INTAKE-READINESS-20260617.json` |
| AFS-PROVIDER-CONNECTED-VALIDATION-READINESS-20260617 | QA Gatekeeper + Provider Gate Steward + Engineering Delivery Lead | No-cost readiness gate before the first post-algorithm provider-connected validation: check GFR packet, Runtime action surface, provider config source, gate projection, and next required human authorization. | Ready for human authorization. Tool reports `ready_for_provider_smoke` with LLM/image gates currently projected open and video/vision closed, but also reports `human_approval_required=true` and `current_session_approval_inferred_from_env=false`; no provider call was started. Focused readiness tests and full default pytest now pass. Boundary: live smoke still requires explicit user approval for exact capability and candidate count. | `tools/afs_provider_connected_validation_readiness.py`, `tests/test_afs_provider_connected_validation_readiness.py`, `docs/handoff/AFS-PROVIDER-CONNECTED-VALIDATION-READINESS-20260617.md` |
| AFS-ALGORITHM-LIBRARY-HARD-REFACTOR-20260617 | Engineering Delivery Lead + Rule Steward + Runtime/API Integrator | First executable algorithm-library slice: asset-card drafts, fixed-asset context boundary, provider safe manifest, independent vision gate, video asset promotion, and external feedback boundary. | Required local smoke passed for visual assets, provider registry, Studio static, context resolver, video revisions, creative keyframes, prompt loop, algorithm contracts, asset-card drafts, Runtime service, changed Studio JS, OpenAPI export, CLI help/version, maintenance audit, and diff check. Boundary: no real provider smoke, no human acceptance, no business validation, no automatic COS rule promotion. | `agentflow/algorithms/`, `apps/api/runtime_asset_card_drafts.py`, `agentflow_studio/model_gateway/provider_adapter.py`, `agentflow_studio/model_gateway/provider_fake_vision.py`, `tests/test_algorithm_library_contracts.py`, `tests/test_api_runtime_asset_card_drafts.py`, `docs/architecture/AFS_ALGORITHM_LIBRARY.zh-CN.md`, `docs/openapi/afs-runtime-service.openapi.json`, `docs/handoff/AFS-ALGORITHM-LIBRARY-HARD-REFACTOR-20260617.md`, `docs/maintenance/AFS-ALGORITHM-LIBRARY-HARD-REFACTOR-20260617.md` |
| AFS-CODEX-IMAGE-HANDOFF-WORKER-20260617 | Runtime/API Integrator + Provider Gate Steward + Studio Interaction Designer + QA Gatekeeper | Add automated async image provider path: Runtime keyframe submit writes safe job package, background worker consumes it, Runtime poll returns safe preview/reusable image asset, and Studio auto-polls without exposing internal worker/provider jargon. | Implemented with fake executor contract verification and `codex exec` executor shell. Focused provider/runtime/static tests passed. Boundary: fake executor proves file contract only; server `codex exec` real image smoke remains required before human test. | `agentflow_studio/model_gateway/codex_image_handoff.py`, `agentflow_studio/model_gateway/codex_image_worker.py`, `agentflow_studio/model_gateway/provider_codex_handoff.py`, `tools/codex_image_worker.py`, `apps/api/runtime_keyframes.py`, `apps/api/runtime_keyframe_async.py`, `apps/api/runtime_keyframe_routes.py`, `apps/studio/src/runtime-client.js`, `apps/studio/src/node-actions.js`, `tests/test_codex_image_handoff.py`, `docs/handoff/AFS-CODEX-IMAGE-HANDOFF-WORKER-20260617.md` |
| AFS-FULL-CHAIN-LOCALIZED-QA-20260615 | QA Gatekeeper + Runtime/API Integrator + Provider Gate Steward + Studio Interaction Designer | Full-chain browser/runtime/live-provider QA focused on end-to-end flow and localized image/video adjustment through the current prompt/asset/context/runtime architecture. | Safe summary merged into mainline from the isolated QA branch. Deterministic full suite passed before live calls; MiniMax T2I, MiniMax reference-backed I2I, and Kling I2V completed in that run. Localized image quality failed in the first paid sample, then a deterministic prompt-ordering fix was added; paid retest remains pending. Video localized editing remains experimental and not productized. | `docs/handoff/AFS-FULL-CHAIN-LOCALIZED-QA-20260615.md`, external evidence root `20260615-afs-full-chain-localized-qa`, `apps/api/runtime_context_text.py`, `tests/test_runtime_context_text.py` |
| AFS-MVP-EXPERIENCE-HARDENING-20260615 | Runtime/API Integrator + Studio Interaction Designer + QA Gatekeeper + Provider Gate Steward | Harden internal-test readiness after latest Studio feedback: Runtime health self-check, safe internal launcher, node-level asset carry visibility, shared asset-reference inspector, explicit video local-cancel boundary, server-sanitized structured quality feedback capture, and explicit external-download closure. | Focused tests passed; Runtime `/health` smoke ready with Studio static ready and all provider gates closed. Claude closeout review approved with no must-fix blockers after follow-up hardening. In-app Browser localhost smoke was blocked by Browser URL policy and recorded as blocked evidence; no alternate browser was used to bypass policy. Boundary: no live provider calls, no ASR/external download, no human acceptance, and no claim that video localized editing is productized. | `docs/handoff/AFS-MVP-EXPERIENCE-HARDENING-20260615.md`, external evidence root `20260615-afs-mvp-experience-hardening`, `tools/run_studio_internal_test.ps1`, `apps/api/runtime_info.py`, `apps/studio/src/asset-reference-summary.js`, `apps/studio/src/asset-reference-inspector.js`, `apps/studio/src/quality-feedback.js`, `tests/test_api_runtime_service.py`, `tests/test_web_studio_static.py`, `tests/test_studio_internal_launcher.py` |
| AFS-VIDEO-LOCALIZED-REGEN-001 | Product Framing + Studio Interaction Designer + Runtime/API Integrator + QA Gatekeeper | Define the next video MVP requirement: accepted video as a base clip, prompt-driven targeted revision, explicit preserve/change controls, temporal scope, and A/B drift scoring. | Experimental contract/UI skeleton implemented. Runtime now has `VideoRevisionRequest`, `/video-revisions/preflight`, `/video-revisions`, safe manifest, feature flag, base lineage, and best-effort preserve/change taxonomy. Studio has revision draft entrypoint and fail-closed unconnected fixed-asset submit guard. Boundary: no provider video-revision submit yet; current Kling path is still I2V, not guaranteed localized editing. | `apps/api/runtime_video_revision_routes.py`, `tests/test_api_runtime_video_revisions.py`, `tests/test_web_studio_static.py`, `docs/handoff/AFS-VIDEO-LOCALIZED-REGEN-20260615.md`, `BACKLOG.md` |
| AFS-BROWSER-ACCEPTANCE-DRILL-20260615 | QA Gatekeeper + Runtime/API Integrator + Studio Interaction Designer + Provider Gate Steward + Frontend UI Reviewer | Browser-led near-human acceptance drill on Runtime-hosted `/studio/`: Runbook paths 1-6, seven role lenses, micro full-chain provider smoke, responsive UI screenshots, safety scan, and readiness audit compatibility for browser-drill evidence. | AI/browser pre-acceptance `recommended`, not human acceptance. Paths 1-6 passed; Path 5 passed by auxiliary browser QA; Path 3 was closed by an explicitly authorized MiniMax reference-backed I2I rerun with `reference_image_count=1`. LLM optimize smoke passed, MiniMax T2I and reference-backed I2I succeeded, Kling I2V submit/poll/preview/reload passed with one submit, seven role checks passed, and provider blockers are zero in the readiness audit. Remaining action is user-run human acceptance plus creative quality scoring; I2I optimizer explicit-edit preservation is a non-blocking follow-up before relying on optimized I2I text. | `docs/handoff/AFS-BROWSER-ACCEPTANCE-DRILL-20260615.md`, external evidence root `20260615-afs-browser-acceptance-drill`, `tools/afs_mvp_joint_qa_readiness_audit.py`, `tests/test_afs_mvp_joint_qa_readiness_audit.py` |
| AFS-MVP-JOINT-QA-CLOSEOUT-20260614 | QA Gatekeeper + Runtime/API Integrator + Studio Interaction Designer + Frontend UI Reviewer + Provider Gate Steward | Codex + Claude joint closeout lane: gate-closed verification, LLM/MiniMax/Kling provider smoke attempt, seven-role AI pre-acceptance, frontend UI audit, P0/P1 repair loop, and safe evidence handoff. | AI recommended / pending human acceptance. Stale Runtime preflight 404 now reports a restart-specific Studio error; image and video gates were opened on Runtime 8790 per user direction while ASR stayed closed. MiniMax image live smoke succeeded with `candidate_count=1`; Kling I2V preflight, submit, poll, preview, and offline inspection succeeded with `candidate_count=1`; MiniMax B-only live retry succeeded and cleared `P1-IMAGE-B-PROVIDER-READINESS`. Final readiness audit reports `recommended`, seven role checks passed, zero provider blockers, and `human_acceptance_claim=not_claimed`. Final verification passed: default pytest 404 passed / 527 deselected; legacy pytest 527 passed / 404 deselected; Studio JS 37 files passed; maintenance audit failed=0; `git diff --check` exit 0. One post-fix asset-context browser QA rerun with explicit live LLM reached the first optimize and then hit an upstream SSL EOF on second re-optimize; no image/video provider call was started by that QA path and it was not retried further. This is not human acceptance or business validation. | `docs/handoff/AFS-MVP-JOINT-QA-CLOSEOUT-20260614.md`, external evidence root `20260614-afs-mvp-joint-qa`, `tools/afs_mvp_joint_qa_readiness_audit.py`, `tests/test_afs_mvp_joint_qa_readiness_audit.py`, `tools/minimax_image_provider_preflight.py`, `tests/test_minimax_image_provider_preflight_tool.py`, `tools/kling_provider_preflight.py`, `tools/studio_asset_context_live_comparison.py`, `tests/test_kling_provider_preflight_tool.py`, `tests/test_api_runtime_generation_comparison.py`, `agentflow_studio/model_gateway/kling_video_smoke.py`, `tests/test_kling_video_task_recovery.py`, `tools/studio_asset_context_browser_qa.py`, `tests/test_studio_asset_context_browser_qa_tool.py`, `apps/studio/src/runtime-client.js`, `apps/studio/src/node-actions.js`, `tests/test_web_studio_static.py` |
| AFS-BROWSER-REPAIR-LOOP-005 | QA Gatekeeper + Runtime/API Integrator + Studio Interaction Designer | Continue the north-star browser takeover loop toward human-acceptance readiness: Loop 003 red baseline, known-issue regressions, generation manifest leak assertions, live provider/browser role-matrix rounds, and current human acceptance runbook. | Runtime/browser verification closed for tested MVP paths. Round A fixed live LLM formatting 422, legacy provider gate drift, duplicate excluded-asset trace rows, and a P0 Kling task-state path leak. Round B fixed tiny reference media reaching paid providers. Round C fixed Studio image-model selection masking LLM provider fields. Round D and Round E were consecutive clean role-matrix rounds with remote LLM optimize, T2I, upload/I2I, fixed asset detail, fixed carry, one-run exclusion, Kling I2V, and Studio load; no new P0/P1. Remaining boundary: user must run human acceptance runbook and score MiniMax/Kling creative quality. | `docs/maintenance/AFS-AGENT-BROWSER-QA-LOOP-003.md`, `docs/maintenance/AFS-BROWSER-QA-LOOP-005-GAP-AUDIT.md`, `docs/handoff/AFS-HUMAN-ACCEPTANCE-RUNBOOK-005.md`, `tests/test_web_studio_static.py`, `tests/test_api_runtime_generation_manifest_safety.py`, `tests/test_api_runtime_prompt_memory_loop.py`, `tests/test_api_runtime_video_generations.py`, `tests/test_api_runtime_keyframe_reference_assets.py`, `runs/agent_browser_qa_loop_005/` |
| AFS-BROWSER-REPAIR-LOOP-004 | Runtime/API Integrator + Studio Interaction Designer + QA Gatekeeper | Request-level fixed asset exclusion, keyframe/video preflight consistency, Runtime-backed asset detail, Studio carry confirmation, one-run exclusion UX, and agent-led browser QA evidence/runbook. | Track A Runtime contract merged; Track B browser loop verified carry confirmation, one-run exclusion reset, cancel persistence, asset detail popover, and Kling no-sound spec UI. Focused Runtime tests 27 passed; Studio static 14 passed; changed JS `node --check` passed. Remaining boundary: human acceptance must be executed by user with the runbook; image/video creative quality still requires human scoring. | `apps/api/runtime_generation_preflight.py`, `apps/api/runtime_context_resolver.py`, `apps/api/runtime_keyframe_routes.py`, `apps/api/runtime_video_routes.py`, `apps/studio/src/node-actions.js`, `apps/studio/src/panels/asset-detail-popover.js`, `docs/maintenance/AFS-BROWSER-QA-LOOP-004.md`, `docs/handoff/AFS-HUMAN-ACCEPTANCE-RUNBOOK-004.md`, `runs/agent_browser_qa_loop_004/` |
| AFS-LEGACY-FREEZE-20260613 | Maintenance Steward + QA Gatekeeper + Provider Gate Steward | Freeze Production Memory and distribution-chain legacy tests behind `pytest -m legacy`, normalize repo line-ending policy, retire stale v0.2 handoff and old `NARRATOCUT_ALLOW_REMOTE_*` gate compatibility, and keep current Runtime/Studio gate as default. | `legacy-frozen-20260613` tag pushed; default pytest 363 passed / 527 deselected; legacy pytest 527 passed / 363 deselected; focused provider/schema/runtime/static tests 66 passed; maintenance audit failed=0 with legacy-frozen warning segment; no provider gates opened. | `.gitattributes`, `pyproject.toml`, `tests/conftest.py`, `tools/maintenance_audit.py`, `agentflow_studio/model_gateway/provider_adapter.py`, `docs/maintenance/AFS-LEGACY-FREEZE-20260613.md` |
| AFS-RUNTIME-LEGACY-ROUTE-REMOVAL-001 | Runtime/API Integrator + Maintenance Steward + QA Gatekeeper | Remove Production Memory HTTP routes from Runtime Service, align default OpenAPI with legacy v02 gate closed, harden current-route error projection, and keep production-memory CLI/harness as non-HTTP compatibility. | Focused Runtime contract set 31 passed; default OpenAPI export regenerated and parsed without retired routes or v02 paths; maintenance audit failed=0; CLI help/version passed; full pytest 886 passed; `git diff --check` exit 0 with CRLF notices only. Provider gates not opened. | `apps/api/runtime_service.py`, `apps/api/runtime_models.py`, `apps/api/runtime_errors.py`, `docs/openapi/afs-runtime-service.openapi.json`, `tests/test_api_runtime_service.py`, `tests/test_api_runtime_service_v02.py`, `tests/test_cli_command_registry_boundaries.py`, `tests/test_studio_mainline_cleanup.py`, `tests/test_maintenance_audit.py`, `docs/maintenance/AFS-RUNTIME-LEGACY-ROUTE-REMOVAL-20260613.md` |
| AFS-BROWSER-QA-HARDENING-002 | Studio Interaction Designer + Runtime/API Integrator + QA Gatekeeper | Fix Claude walkthrough P0/P1 findings and continue agent-led browser QA: project isolation, modal removal, provider gate normalization, T2I/I2I optimizer split, refresh preview persistence, asset drawer/detail restore, I2I guardrail quality gate, video dead-control cleanup, and Kling video resume UI. | Focused prompt/state/static paths passed; browser loops covered project isolation, asset drawer/detail restore, live MiniMax T2I/I2I optimize/generate, asset attach-to-node semantics, video first-frame guard, and live Kling I2V submit/poll/preview. Kling now returns `submitted`, polls through `running` to `succeeded`, survives refresh through `lastVideoJobId`, and renders a safe `<video controls>` preview. Loop 5 fixed drawer fixed-asset labels/thumbnails, node placement avoidance, and `用于当前节点 -> visualAssets -> 本次携带` continuity. Remaining risks: image identity similarity and video first-frame quality need human scoring. | `apps/studio/src/store.js`, `apps/studio/src/main.js`, `apps/studio/src/optimizer-contract.js`, `apps/studio/src/prompt-bar.js`, `apps/studio/src/canvas-view.js`, `apps/studio/src/node-actions.js`, `apps/studio/src/node-result-view.js`, `apps/studio/src/panels/drawer.js`, `apps/studio/src/panels/add-node-menu.js`, `apps/api/runtime_llm_enhancement.py`, `apps/api/runtime_studio_state.py`, `agentflow_studio/model_gateway/kling_video_smoke.py`, `docs/maintenance/AFS-BROWSER-QA-HARDENING-20260613.md`, `runs/i2i-gen-studio-loop-i2igen-1781307999.png`, `runs/kling-poll-ui-video-preview-20260613.png`, `runs/loop-attached-asset-generation-20260613.png` |
| AFS-KLING-PREFLIGHT-001 | Runtime/API Integrator + Provider Gate Steward + Studio Interaction Designer | Kling I2V preflight: project list/new project, safe preview persistence, ProviderDescriptor v0.2, Kling registry adapter, Runtime video submit/poll/cancel/preview, Studio explicit first-frame flow. | Live Kling I2V is now connected through the registry with local ignored provider config: browser submit returned `submitted`, API poll returned `running` then `succeeded`, preview endpoint returned `video/mp4`, and safe manifest stored no provider raw/URLs. Focused provider/video set 44 passed after async adapter fix. | `apps/api/runtime_video_routes.py`, `apps/api/runtime_models.py`, `agentflow_studio/model_gateway/provider_adapter.py`, `agentflow_studio/model_gateway/provider_adapter_impl.py`, `agentflow_studio/model_gateway/kling_video_smoke.py`, `apps/studio/src/`, `tools/kling_provider_preflight.py`, `tests/test_api_runtime_video_generations.py`, `tests/test_provider_adapter_registry.py`, `docs/handoff/AFS-KLING-PREFLIGHT-001.md`, `docs/provider_adapter_v02_video_addendum.md`, `runs/kling-async-081724-first.png`, `runs/kling-async-081724-last.png` |
| AFS-MVP-HARDENING-001 | Runtime/API Integrator + Studio Interaction Designer + QA Gatekeeper | Dynamic-stage preflight hardening: section-header-free provider prompt, bounded generate asset injection, reference-edge hop semantics, visual asset version arbitration, reproducible bundle metadata, provider retry manifest, and Studio dead-control cleanup. | Backend focused hardening set 33 passed; Studio static 12 passed; full pytest 855 passed; changed Studio JS `node --check` passed; maintenance audit failed=0 with existing warnings. Browser light QA passed for `/studio/` load, no console errors, removed local-preview/cost/internal wording, and Chinese fixed-asset action title; current browser state had no asset badge, so readonly asset-detail click remains covered by static tests only. | `apps/api/runtime_context_resolver.py`, `apps/api/runtime_keyframes.py`, `apps/api/runtime_prompt_text.py`, `apps/api/runtime_visual_assets.py`, `apps/studio/src/`, `tests/test_api_runtime_context_resolver.py`, `tests/test_api_runtime_creative_agent_keyframes.py`, `tests/test_web_studio_static.py`, `docs/handoff/AFS-MVP-HARDENING-001.md` |
| AFS-STUDIO-MVP-USABILITY-P0 | Studio Interaction Designer + Runtime/API Integrator + QA Gatekeeper | Remove user-facing deterministic prompt optimization fallback; require remote LLM for Studio optimization; improve provider/gate errors; fix failed-generation state persistence; make canvas nodes direct asset-marking entrypoints. | Focused prompt/state/static tests 4 passed; related prompt/state/static suite 21 passed; changed Studio JS passed `node --check`; full pytest 844 passed; user-env image/LLM gates opened locally for this machine only. | `apps/api/runtime_prompt_memory.py`, `apps/api/runtime_studio_state.py`, `apps/studio/src/optimizer.js`, `apps/studio/src/optimizer-contract.js`, `apps/studio/src/runtime-client.js`, `apps/studio/src/node-actions.js`, `apps/studio/src/panels/node-menu.js`, `tests/test_api_runtime_prompt_memory_loop.py`, `tests/test_api_runtime_studio_state_persistence.py`, `docs/handoff/AFS-STUDIO-MVP-USABILITY-P0.md` |
| AFS-PROJECT-INVENTORY-001 | Maintenance Steward + QA / Release Gatekeeper | 全量项目 inventory、ignored 本地产物审计、直接删减无用 tracked 入口、provider gateway 前维护债基线。 | Inventory/cleanup 工具 focused tests 3 passed；低风险清理累计删除 14,452 个缓存目标、约 30.24MB；直接删除 `asset_manager` 空壳和 6 份旧 production-memory asset handoff；production-memory CLI 短别名已退出默认产品面；本地重复媒体证据 80 组、约 827MB 理论可回收但需 canonical evidence retention；`data/processed/pytest-basetemp` 仍有 Windows 所有权/ACL 阻塞。 | `tools/project_inventory.py`, `tools/project_inventory_core.py`, `tests/test_project_inventory_cleanup.py`, `tests/test_cli_command_registry_boundaries.py`, `docs/maintenance/AFS-PROJECT-INVENTORY-20260612.md`, `docs/maintenance/AFS-DEEP-LOCAL-REVIEW-20260612.md`, `docs/handoff/AFS-PROJECT-INVENTORY-001.md` |
| AFS-STUDIO-MAINLINE-CLEANUP-001 | Runtime/API Integrator + Maintenance Steward | Studio 主线口径收敛; legacy Runtime v02 默认隐藏; `agentflow/memory` 标记只读遗产; tracked `*_sop` 空壳审计和最小删除。 | Focused cleanup/static tests 15 passed; full pytest 828 passed; Studio JS `node --check` 35 files passed; maintenance audit has 0 failed checks and 1 oversized-files warning; `git diff --check` clean except CRLF notices; provider gates not opened. | `AGENTS.md`, `docs/current_architecture.md`, `apps/api/runtime_service.py`, `tests/test_api_runtime_service_v02.py`, `tests/test_studio_mainline_cleanup.py`, `docs/maintenance/AFS-STUDIO-MAINLINE-CLEANUP-001.md` |
| AFS-DIRECTOR-COMPILER-V1 | Runtime/API Integrator + Studio Interaction Designer | Director Compiler v1 deterministic backend compiler; blank-stage director defaults; active camera/subjects; subject visual asset id binding; Studio confirmed prompt append. | Focused compiler/API/context/static set 24 passed; changed director JS passed `node --check`; provider gates not opened. | `apps/api/runtime_director_compiler.py`, `apps/api/runtime_prompt_memory_user_prompt.py`, `apps/api/runtime_context_resolver.py`, `apps/studio/src/director-data.js`, `apps/studio/src/panels/director-shell.js`, `docs/director_compiler_v1.md`, `tests/test_runtime_director_compiler.py`, `tests/test_api_runtime_director_setup_prompt.py`, `tests/test_web_studio_static.py` |
| AFS-PROVIDER-ADAPTER-V0-1 | Runtime/API Integrator + Provider Gate Steward | Provider Gateway v0.1: service descriptor registry, account pool selection, MiniMax image dispatch, OpenAI-compatible LLM dispatch, fake async video lifecycle contract, descriptor-driven prompt budget/reference slots. | Focused provider/keyframe/resolver/prompt tests 42 passed; provider registry tests 11 passed; provider gates remain closed except mocked dispatch paths; no live provider smoke. | `agentflow_studio/model_gateway/provider_adapter.py`, `agentflow_studio/model_gateway/provider_account_pool.py`, `configs/providers.example.json`, `apps/api/runtime_keyframes.py`, `apps/api/runtime_llm_enhancement.py`, `apps/api/runtime_context_resolver.py`, `docs/provider_adapter_contract.md`, `tests/test_provider_adapter_registry.py`, `tests/test_api_runtime_prompt_memory_loop.py`, `tests/test_api_runtime_creative_agent_keyframes.py` |
| AFS-ASSET-CONTEXT-S1-FOLLOWUP-001 | Runtime/API Integrator + QA Gatekeeper | S1 完成审计三缺口收尾:预算分段裁剪真执行(锁定永不裁/可见保底 550/分隔符余量)、冲突检测属性词表化、上游摘要与偏好段补填;交付特征卡模板、A/B/C runbook、内测手册。 | Focused pytest `tests/test_runtime_attribute_vocabulary_and_budget.py tests/test_api_runtime_context_resolver.py` 16 passed; changed Studio JS passed `node --check`; `git diff --check` clean except CRLF warnings. | `apps/api/runtime_attribute_vocabulary.py`, `apps/api/runtime_context_budget.py`, `apps/api/runtime_context_resolver.py`, `tests/test_runtime_attribute_vocabulary_and_budget.py`, `docs/handoff/AFS-ASSET-CONTEXT-S1-FOLLOWUP-001.md`, `docs/visual_asset_feature_card_template.zh-CN.md`, `docs/abc_comparison_runbook.zh-CN.md`, `docs/afs_studio_internal_test_handbook.zh-CN.md` |
| AFS-ASSET-CONTEXT-S1 | Runtime/API Integrator + Studio Interaction Designer + Provider Gate Steward | Fixed visual assets, graph-scoped context resolver, dual prompt/model channels, and A/B/C comparison report. | Gate-closed Runtime/Web implementation, browser QA, live-comparison readiness runner, sample reference generator, and completion audit passed on `codex/afs-asset-context-s1`; no-call readiness has used the ignored provider config path, and live provider evidence now requires explicit `AFS_ALLOW_REMOTE_IMAGE=true` plus `--allow-live-provider`. | `apps/api/runtime_visual_assets.py`, `apps/api/runtime_context_resolver.py`, `apps/api/runtime_generation_comparisons.py`, `apps/studio/`, `tools/studio_asset_context_browser_qa.py`, `tools/studio_asset_context_live_comparison.py`, `tools/studio_asset_context_sample_reference.py`, `tests/test_api_runtime_visual_assets.py`, `tests/test_api_runtime_context_resolver.py`, `tests/test_api_runtime_generation_comparison.py`, `tests/test_studio_asset_context_live_comparison_tool.py`, `docs/handoff/AFS-ASSET-CONTEXT-S1.md`, `docs/handoff/AFS-ASSET-CONTEXT-S1-COMPLETION-AUDIT.md`, `docs/maintenance/AFS-ASSET-CONTEXT-S1.md` |
| AFS-STUDIO-V02-DELIVERY-POLISH-001 | Frontend Interaction Designer + Runtime/API Integrator + QA Gatekeeper | AFS Studio v0.2 internal delivery polish: flow-native starter, safe Studio state save/restore, visible asset drawer actions, semantic edges, prompt copilot feedback, mobile overflow guard. | Verified on `codex/afs-studio-v02-delivery-polish-001`; provider gates remain closed. | `apps/studio/`, `apps/api/runtime_studio_state.py`, `tests/test_api_runtime_studio_state.py`, `tests/test_web_studio_static.py`, `docs/handoff/AFS-STUDIO-V02-DELIVERY-POLISH-001.md` |
| AFS-STUDIO-UI-POLISH-DIRECTOR-002 | Frontend Interaction Designer + Runtime/API Integrator | 修复 Studio 左上角布局；落地二维导演台；将导演台结构化布置接入节点提示词优化；修复 dock 添加节点安全区。 | 已验证：全量 pytest 和浏览器 QA 通过；provider 仍关闭。 | `apps/studio/`, `apps/api/runtime_prompt_memory_user_prompt.py`, `tests/test_api_runtime_director_setup_prompt.py`, `docs/maintenance/AFS-STUDIO-HARD-CLEANUP-001.zh-CN.md` |
| AFS-STUDIO-HARD-CLEANUP-001 | Frontend Contract Steward + Maintainability Steward + QA / Release Gatekeeper | Delete retired Workbench/static memory-workbench user surfaces; make `/studio/` the only frontend entry. | In integration verification on `codex/afs-studio-hard-cleanup-001` | `docs/maintenance/AFS-STUDIO-HARD-CLEANUP-001.zh-CN.md` |
| AFS-CREATIVE-INTENT-AGENT-V1 | Runtime/API Integrator + Creative Agent Architect | Add deterministic creative intent control agent trace: constraint layers, candidate scoring, selected prompt, provider translation. | Focused tests passing | `docs/architecture/AFS_CREATIVE_INTENT_CONTROL_AGENT_ENGINEERING_SUMMARY.zh-CN.md` |
| AFS-KEYFRAME-GENERATION-GATE-001 | Runtime/API Integrator + Provider Gate Steward | Add `POST /projects/{project_id}/keyframe-generations`; gate closed path returns blocked safe manifest without network. | Focused tests passing | `tests/test_api_runtime_creative_agent_keyframes.py` |
| AFS-PROFESSIONAL-KNOWLEDGEBASE-PROMPT-ASSEMBLY-001 | Runtime/API Integrator + Knowledgebase Steward | Professional rules, hidden background context, prompt assembly, trace and safe manifest. | Baseline active; now feeds creative agent | `agentflow/knowledge/`, `docs/handoff/AFS-PROFESSIONAL-KNOWLEDGEBASE-PROMPT-ASSEMBLY-001.md` |

## Current Baseline

### Current Verification Addendum - AFS-BROWSER-QA-HARDENING-002

- 2026-06-13 最终浏览器 QA 加固回合已收口 runtime/browser verification。
- 新增覆盖：`lastContextBundle` 安全摘要刷新持久化、生成后主动保存最终状态、资产抽屉把现有 image asset 显式设为视频首帧/尾帧、视频节点只恢复 Runtime video preview、prompt bar 对生成中的视频执行继续轮询而不是重复 submit。
- 最终验证：focused pytest 72 passed；Studio JS `node --check` 37 files passed；full pytest 886 passed；maintenance audit failed=0；`git diff --check` exit 0；浏览器最终检查显示 safe video preview 存在、发送按钮为“生成”、console warn/error 为空。
- 剩余边界：MiniMax 人物身份相似度和 Kling 首帧创意质量仍需要人工评分；本条不是 human acceptance 或 business validation。

| Area | Path | Notes |
|---|---|---|
| Frontend | `apps/studio/` | Served through `/studio/`; only current user-facing Web product. |
| Runtime API | `apps/api/` | Frontend boundary; no CLI internals, provider secrets, local private paths, signed URLs, provider raw, or media bytes. |
| Prompt optimizer contract | `docs/architecture/AFS_NODE_PROMPT_OPTIMIZER_CONTRACT.zh-CN.md` | Node prompt optimization only; no memory review UI. |
| Creative agent summary | `docs/architecture/AFS_CREATIVE_INTENT_CONTROL_AGENT_ENGINEERING_SUMMARY.zh-CN.md` | Repo-safe engineering summary; detailed algorithm note is private in `10-Startup`. |
| Maintenance ledger | `docs/maintenance/AFS-STUDIO-HARD-CLEANUP-001.zh-CN.md` | Deletion decisions and verification plan. |

## Boundaries

- Provider gates are closed unless a task explicitly opens one capability.
- Image/keyframe authorization does not authorize video, LLM, ASR, or downloads.
- Browser/runtime verification, provider smoke, human acceptance, business validation, and durable-memory promotion are separate claim levels.
- Feedback and extracted context remain evidence/background unless explicitly promoted by a human workflow.

## Next Queue

| ID | Scope | Trigger |
|---|---|---|
| AFS-STUDIO-BROWSER-QA-001 | Runtime-hosted `/studio/` browser QA: create nodes, move nodes, connect ports, optimize prompt, open director panel, check mobile layout. | Before merging/pushing this branch. |
| AFS-IMAGE-PROVIDER-SMOKE-001 | Open `AFS_ALLOW_REMOTE_IMAGE=true` and run explicit MiniMax keyframe smoke with safe artifacts. | After branch is clean and user confirms real image provider smoke. |
| AFS-KEYFRAME-QA-001 | Add visual QA for generated keyframes: subject count, text/watermark, black/blank, composition, reference consistency. | After first real keyframe provider output exists. |
| AFS-STUDIO-SPRITE-V2-S0 | v2 画布小精灵首迭代前置：undo/redo 命令栈、Action Registry（L0-L3 白名单 + schema 校验）、`#sprite-layer`。规划见 `docs/architecture/AFS_STUDIO_SPRITE_V2_PLAN.zh-CN.md`（S0-S5 全里程碑、三工作模式、LLM gate 降级策略、lottie vendored 例外）。 | After MVP v1 联合验收（AFS-STUDIO-BROWSER-QA-001）收口。 |

## Current Addendum - MiniMax Provider Smoke Prep

| ID | Owner role | Scope | Status | Evidence |
|---|---|---|---|---|
| AFS-MINIMAX-TEXT-IMAGE-INTEGRATION-001 | Runtime/API Integrator + Provider Gate Steward | Add gated MiniMax-M3 prompt enhancement and MiniMax `image-01` keyframe path; keep video/audio off. | Local live smoke passed on `127.0.0.1:8793`; manual comparison pending. | `docs/handoff/AFS-MINIMAX-TEXT-IMAGE-INTEGRATION-001.md`, `configs/models.example.yaml`, `configs/providers.example.json` |
| AFS-MINIMAX-MANUAL-COMPARISON-001 | QA / Release Gatekeeper + Creative Director | Run A/B/C keyframe comparison: raw prompt, deterministic agent prompt, MiniMax-M3 enhanced prompt. | Ready for manual operation; latest provider output shows text/watermark risk to score. | `docs/handoff/AFS-MINIMAX-TEXT-IMAGE-INTEGRATION-001.md` |
| AFS-CONNECTED-REFERENCE-KEYFRAME-001 | Runtime/API Integrator + Studio Interaction Designer | Upload images on any Studio node; collect connected upstream reference images and prompt notes for keyframe generation. | Focused tests and Runtime upload smoke passed; live creative comparison pending. | `apps/api/runtime_image_assets.py`, `apps/studio/src/optimizer-contract.js`, `tests/test_api_runtime_creative_agent_keyframes.py` |

## Current Addendum - MVP Follow-up Live Comparisons

| ID | Owner role | Scope | Status | Evidence |
|---|---|---|---|---|
| AFS-MVP-FOLLOWUP-LIVE-COMPARISONS-20260612 | Runtime/API Integrator + Provider Gate Steward + QA Gatekeeper | Run the pre-internal-test Group 2 character+scene asset comparison and Group 3 lock-conflict locked/unlocked live MiniMax image checks. | Implemented follow-up runner and focused tests. Group 2 first run succeeded for A/B/C; Group 3 retry succeeded for locked and temporary-unlocked runs. One later Group 2 rerun hit provider/CLI readiness block and is preserved as intermittency evidence. | `tools/studio_asset_context_followup_comparisons.py`, `tests/test_studio_asset_context_followup_comparisons.py`, `docs/handoff/AFS-MVP-FOLLOWUP-LIVE-COMPARISONS-20260612.md`, `runs/studio_asset_context_followup_20260612_group2_success/`, `runs/studio_asset_context_followup_20260612_group3_retry/` |

## Current Addendum - Asset Card Draft Module Split

| ID | Owner role | Scope | Status | Evidence |
|---|---|---|---|---|
| AFS-ASSET-CARD-DRAFT-MODULE-SPLIT-20260619 | Runtime/API Integrator + Maintainability Steward | Split asset-card draft route helpers for visual inspection dispatch/provider observation and safe artifact writing into focused modules. | Local verification passed; provider gates unchanged; no live provider call. Oversized warning count dropped from 39 to 38. | `apps/api/runtime_asset_card_drafts.py`, `apps/api/runtime_asset_card_observation.py`, `apps/api/runtime_asset_card_artifacts.py`, `tests/test_api_runtime_asset_card_modules.py`; pytest 532 passed / 527 deselected / 2 existing warnings; maintenance audit failed=0; `git diff --check` passed. |

## Current Addendum - Auth Module Split

| ID | Owner role | Scope | Status | Evidence |
|---|---|---|---|---|
| AFS-AUTH-MODULE-SPLIT-20260619 | Runtime/API Integrator + Internal Beta Steward | Split auth route/middleware assembly and password/session/token helpers out of `runtime_auth.py` while preserving invite registration, session auth, and project-owner isolation. | Local verification passed; auth policy unchanged; provider gates unchanged. Oversized warning count dropped from 38 to 37. | `apps/api/runtime_auth.py`, `apps/api/runtime_auth_routes.py`, `apps/api/runtime_auth_security.py`, `apps/api/runtime_service.py`, `tests/test_api_runtime_auth_modules.py`; auth/internal-beta focused tests 17 passed; pytest 533 passed / 527 deselected / 2 existing warnings; maintenance audit failed=0; `git diff --check` passed. |
| AFS-STUDIO-DIRECTOR-SHELL-RENDER-SPLIT-20260619 | Studio Interaction Designer + Maintainability Steward | Split Director Shell rendering and default object construction out of the interactive shell so the director node remains easier to evolve with prompt/context workflows. | Local verification passed; provider gates unchanged; no live provider call. Oversized warning count dropped from 32 to 31. | `apps/studio/src/panels/director-shell.js`, `apps/studio/src/panels/director-shell-render.js`, `apps/studio/src/panels/director-object-factory.js`, `tests/test_web_studio_mature_shell_static.py`; red/green static test; Studio static set 32 passed; JS check 93 files passed; browser load console warn/error=0; pytest 536 passed / 527 deselected / 2 existing warnings; maintenance audit failed=0; `git diff --check` passed. |
| AFS-INTERNAL-BETA-HUMAN-REVIEW-PACKET-20260619 | QA Gatekeeper + Internal Beta Steward | Add a safe human-review packet to deterministic internal beta acceptance reports so machine verification hands off to operator scoring without claiming human acceptance. | Local verification passed; provider gates unchanged; no live provider call; no Company OS or long-term memory write. | `tools/afs_internal_beta_acceptance_review.py`, `tools/afs_internal_beta_acceptance_contract.py`, `tests/test_afs_internal_beta_acceptance.py`; red/green acceptance tests; Acceptance CLI smoke status `contract_verified_pending_human_acceptance` with `pending_human_review`; acceptance/three-end focused tests 17 passed; pytest 537 passed / 527 deselected / 2 warnings; maintenance audit failed=0; `git diff --check` passed. |
| AFS-INTERNAL-BETA-HUMAN-REVIEW-MARKDOWN-20260619 | QA Gatekeeper + Internal Beta Steward | Add optional Markdown output for the human-review packet so internal beta operators can score and decide the next beta round from a safe checklist. | Local verification passed; provider gates unchanged; no live provider call; no Company OS or long-term memory write. | `tools/afs_internal_beta_acceptance.py`, `tools/afs_internal_beta_acceptance_review.py`, `tests/test_afs_internal_beta_acceptance_review.py`; red/green CLI/output tests; Acceptance CLI smoke with `--human-review-md`; acceptance focused tests 18 passed; pytest 538 passed / 527 deselected / 2 warnings; maintenance audit failed=0; `git diff --check` passed. |
| AFS-STUDIO-SPRITE-NAVIGATOR-POLISH-20260619 | Studio Interaction Designer + Frontend QA Gatekeeper | Refine the movable `AFS 小精灵` into a clearer Studio navigator character with stronger silhouette, facial expression, and drag affordance. | Local verification passed; Runtime sprite boundary unchanged; provider gates unchanged; no live provider call. | `apps/studio/src/sprite-widget.js`, `apps/studio/styles/studio-sprite-avatar-personality.css`, `tests/test_web_studio_sprite_static.py`; red/green sprite static test; sprite/API focused tests 6 passed / 1 existing warning; JS check 93 files passed; browser drag/open verification passed with console warn/error=0; maintenance audit failed=0; `git diff --check` passed. |
| AFS-STUDIO-SPRITE-TUANTUAN-MULTIPOSE-20260619 | Studio Interaction Designer + Frontend QA Gatekeeper | Convert `AFS 小精灵` from a single reference sticker into a multi-pose `团团` companion using reference-derived idle/happy/curious/thinking/surprised/sleepy/working/celebrate PNG assets and state-driven pose switching. | Local focused verification passed; Runtime sprite boundary unchanged; provider gates unchanged; no live provider call. | `apps/studio/assets/tuantuan-*.png`, `apps/studio/src/sprite-widget.js`, `apps/studio/src/sprite-position.js`, `apps/studio/styles/studio-sprite-avatar-mascot.css`, `tests/test_web_studio_sprite_static.py`; sprite/API tests 6 passed / 1 existing warning; JS check 94 files passed; browser smoke confirmed initial=idle, hover/drag=happy, settings=thinking, open=curious, 8 assets loaded, console warn/error=0. |
| AFS-STUDIO-SPRITE-TUANTUAN-MOTION-20260619 | Studio Interaction Designer + Frontend QA Gatekeeper | Add a lossless continuous motion layer for TuanTuan so pointer attention, hover, drag, working, success, and error states change character transform and shadow rather than only swapping pose images. | Local focused verification passed; Runtime sprite boundary unchanged; provider gates unchanged; no live provider call; full skeletal rig remains future work pending layered source art or animation assets. | `apps/studio/src/sprite-character.js`, `apps/studio/src/sprite-motion.js`, `apps/studio/src/sprite-widget.js`, `apps/studio/styles/studio-sprite-avatar-mascot.css`, `tests/test_web_studio_sprite_static.py`; JS check 96 files passed; sprite/API focused tests 16 passed / 1 existing warning; browser smoke confirmed pointer/hover/drag changed shift, tilt, squash, and shadow variables; screenshot `runs/tuantuan-sprite-motion-smoke-20260619.png`. |
| AFS-STUDIO-SPRITE-TUANTUAN-V1-CANVAS-AGENT-20260619 | Studio Interaction Designer + Frontend QA Gatekeeper + Product Intent Steward | Reframe TuanTuan as the embodied AFS Agent projection inside the canvas, not a mascot, desktop pet, or chatbot avatar. Implement a resting story-cat DOM rig with story orbit and Observe / Suggest / Execute state semantics. | Local focused verification passed; Runtime sprite boundary unchanged; provider gates unchanged; no live provider call. Public server still needs the review branch merged/deployed; the current login loop is caused by Nginx Basic Auth in front of Runtime app auth and requires sudo-side Nginx adjustment. | `apps/studio/src/sprite-character.js`, `apps/studio/src/sprite-motion.js`, `apps/studio/src/sprite-widget.js`, `apps/studio/styles/studio-sprite-avatar-story-cat.css`, `apps/studio/styles/studio-sprite-avatar-story-cat-details.css`, `apps/studio/styles/studio-sprite-avatar-story-states.css`, `tests/test_web_studio_sprite_static.py`, `docs/handoff/AFS-STUDIO-TUANTUAN-V1-CANVAS-AGENT-20260619.md`; retired old `apps/studio/assets/tuantuan-*.png` sticker poses; added reference-shape anchors: inner ears, tabby face marks, whiskers, nose/mouth, story belly panel, front paws, segmented tail; JS check 96 files passed; sprite/API focused tests 16 passed / 1 existing warning; browser smoke confirmed role=embodied-agent, character=story-cat, observe->think->suggest state path, no old image-asset sprite, console warn/error=0. |
| AFS-STUDIO-SPRITE-TUANTUAN-REFERENCE-SHAPE-20260620 | Studio Interaction Designer + Frontend QA Gatekeeper + Product Intent Steward | Reset TuanTuan's V1 visual baseline to the user-approved reference direction: dark low resting tabby story cat, large ears/eyes, sprout, cyan story orbit, body tabby marks, paws, whiskers, and story belly panel. Keep the implementation as animatable SVG/DOM, not a sticker. | Local focused verification passed; Runtime sprite boundary unchanged; provider gates unchanged; no live provider call. This is a more faithful V1 visual baseline, not final IP illustration acceptance or full animation rig. | `apps/studio/src/sprite-character.js`, `apps/studio/src/sprite-position.js`, `apps/studio/styles/studio-sprite.css`, `apps/studio/styles/studio-sprite-avatar-story-cat.css`, `apps/studio/styles/studio-sprite-avatar-story-cat-details.css`, `tests/test_web_studio_sprite_static.py`; JS check 96 files passed; sprite/API focused tests 6 passed / 1 existing warning; browser smoke confirmed `catTag=svg`, eyes=2, ears=2, tabbyMarks=3, orbitNodes=5, state=observe; screenshot `runs/tuantuan-reference-shape-20260620/tuantuan-reference-shape-avatar-v2.png`. |
| AFS-STUDIO-SPRITE-TUANTUAN-REFERENCE-CALIBRATION-20260620 | Studio Interaction Designer + Frontend QA Gatekeeper | Calibrate the V1 SVG rig closer to the latest dark resting TuanTuan reference: lower body, clearer tabby silhouette, calmer eyes, smaller sprout, quieter story panel, and canvas-native orbit. | Local focused verification passed; Runtime sprite boundary unchanged; provider gates unchanged; no live provider call; not final IP acceptance. | `apps/studio/src/sprite-character.js`, `apps/studio/styles/studio-sprite-avatar-story-cat.css`, `apps/studio/styles/studio-sprite-avatar-story-cat-details.css`, `DEVLOG.md`; sprite/API tests 6 passed / 1 existing warning; JS check 96 files passed; `git diff --check` passed; Chrome render smoke inspected at `/studio/?project=tuantuan-local-preview-2`. |
| AFS-STUDIO-RUNTIME-UI-FIXES-20260621 | Runtime/API Integrator + Studio Interaction Designer + Frontend QA Gatekeeper | Fix non-video model-flow UI gaps before internal test: honest image job progress, long keyframe polling, stale Codex image worker recovery, render-safe media URLs for reference images, image asset deletion, TuanTuan focus/pending shimmer/rotating copy, and Works library drawer layout. | Local full verification passed on `codex/studio-runtime-ui-fixes`; provider gates unchanged; no live provider call; browser/runtime smoke passed. | `apps/api/runtime_jobs.py`, `apps/api/runtime_image_assets.py`, `agentflow_studio/model_gateway/codex_image_worker.py`, `apps/studio/src/`, `tests/test_api_runtime_jobs.py`, `tests/test_web_studio_frontend_wave.py`, `tests/test_web_studio_sprite_static.py`; pytest 569 passed / 527 deselected / 2 warnings; JS check 98 files passed; browser smoke `runs/studio_runtime_ui_fixes_browser_smoke.json`. |
| AFS-STUDIO-FULL-COVERAGE-QA-20260621 | QA Gatekeeper + Studio Interaction Designer + Runtime/API Integrator + Release Gatekeeper | Run a multi-role internal-test replacement pass across Studio browser UX, Runtime contracts, non-video model paths, public edge, and three-end state. Fix QA proxy handling, stale browser selectors, TuanTuan modal overlap, image asset detail 404, and add reusable browser QA coverage. | Final local browser/API verification passed; server non-video LLM/image/vision smoke passed; video gate remained closed. Commit/deploy synchronization is handled as the release step for this addendum. | `docs/maintenance/AFS-STUDIO-FULL-COVERAGE-TEST-PLAN-20260621.md`, `docs/maintenance/AFS-STUDIO-FULL-COVERAGE-TEST-RUN-20260621.md`, `tools/studio_full_coverage_browser_qa.py`, `tools/studio_asset_context_browser_qa.py`, `tools/studio_asset_context_browser_qa_support.py`, `apps/studio/src/panels/asset-detail-popover.js`, `apps/studio/styles/studio-sprite.css`; final browser reports `runs/final_existing_browser_qa_stub_20260621.json`, `runs/final_full_coverage_browser_qa_20260621.json`; server reports `runs/full_coverage_three_end_status_20260621.json`, `runs/full_coverage_public_edge_preflight_20260621.json`. |
| AFS-STUDIO-CONCURRENCY-PROMPT-RENDER-FIXES-20260621 | Runtime/API Integrator + Studio Interaction Designer + Frontend QA Gatekeeper | Finish current internal-test blocker set: real Codex image queue states, worker claim isolation, job-scoped Codex home, deterministic generated image assets, style-vs-subject reference prompt optimization, cached Runtime media rendering, full-bleed image nodes, asset context-menu delete, and TuanTuan focused-input/prompt-leak guards. | Local full verification passed on `codex/studio-concurrency-hardening`; local `master`, `origin/master`, server `/home`, and server `/opt` synchronized and deployed; server queue audit shows no active pending/running image jobs. | `agentflow_studio/model_gateway/codex_image_handoff.py`, `agentflow_studio/model_gateway/codex_image_worker.py`, `apps/api/runtime_llm_enhancement_*`, `apps/studio/src/runtime-media-source.js`, `apps/studio/src/sprite-widget.js`, `apps/studio/src/canvas-node-body.js`, `tests/test_codex_image_handoff.py`, `tests/test_api_runtime_prompt_memory_loop.py`, `tests/test_web_studio_frontend_wave.py`; pytest 585 passed / 527 deselected / 2 warnings; JS check 99 files passed; Browser plugin smoke passed; `tools/studio_full_coverage_browser_qa.py` passed; server queue pending=0/running=0; Runtime active with image/LLM gates true and video gate false. |
| AFS-STUDIO-WEB-DIRECTOR-POLISH-20260623 | Studio Interaction Designer + Runtime/API Integrator + Frontend QA Gatekeeper | Fix current Studio interaction blockers, asset-card regeneration/persistence, standalone Social Square, homepage polish, and Director Stage production package. | Merged to `master`, pushed, deployed to server `/home` and `/opt`, Runtime/worker restarted, three-end status aligned at `53a0f17`; provider gates unchanged; live provider calls not started. | `apps/studio/src/canvas-input.js`, `apps/studio/src/store.js`, `apps/studio/src/optimizer-contract.js`, `apps/api/runtime_image_assets.py`, `apps/site/index.html`, `apps/site/social-square.html`, `apps/site/social-square.js`, `apps/studio/src/panels/director-shell-render.js`, `tests/test_site_homepage_static.py`, `tests/test_site_social_square_static.py`, `tests/test_web_studio_prompt_script_static.py`, `tests/test_api_runtime_keyframe_reference_assets.py`; JS check 112 files passed; focused pytest 42 passed; social/runtime/state pytest 52 passed; local Runtime/browser smoke passed for homepage, Social Square, image-node double-click, and asset-card homepage roundtrip persistence; public `/site/` and `/site/social-square.html` returned 200; final three-end report `runs/three_end_status_20260623_web_director_polish_final_after_restart.json` aligned. |
| AFS-INTERNAL-BETA-PUBLIC-EDGE-ACCEPTANCE-GATE-20260620 | Internal Beta Steward + Release Gatekeeper | Gate deployed HTTP internal-beta acceptance on public Studio edge readiness before invite codes or auth/project writes start. | Local and live gate verification passed; current public edge still returns `public_edge_not_ready` because Nginx Basic Auth remains active; provider gates unchanged; no live provider call. | `tools/afs_internal_beta_acceptance.py`, `tools/afs_internal_beta_acceptance_args.py`, `tools/afs_internal_beta_acceptance_edge_gate.py`, `tests/test_afs_internal_beta_preflight_public_edge.py`, `docs/maintenance/AFS-PUBLIC-EDGE-AUTH-PREFLIGHT-20260620.md`, `DEVLOG.md`; focused public-edge/acceptance tests 23 passed / 1 existing warning; live HTTP acceptance edge gate without invite codes returned `public_edge_not_ready`, exit_code=2, edge_basic_auth=true, runtime_status=ready. |
| AFS-INTERNAL-BETA-THREE-END-STATUS-CLI-20260620 | QA Gatekeeper + Release Gatekeeper | Fix standalone `tools/afs_internal_beta_acceptance.py --three-end-status` so three-end drift checks produce the safe status report instead of accidentally running deterministic acceptance. | Local focused verification passed; provider gates unchanged; no live provider call; not human acceptance or business validation. | `tools/afs_internal_beta_acceptance.py`, `tests/test_afs_internal_beta_acceptance_cli.py`, `tests/test_afs_internal_beta_acceptance.py`, `DEVLOG.md`; red/green regression for standalone three-end status; focused acceptance/preflight/three-end tests 17 passed / 1 existing warning. |
| AFS-PUBLIC-EDGE-NGINX-BASIC-AUTH-FIX-TOOL-20260620 | Release Gatekeeper + Internal Beta Steward | Add a tested server-side Nginx repair command for the public Studio edge so old Basic Auth can be removed safely when an interactive sudo session is available. | Local diagnosis and tooling completed; live edge still reports `blocked_by_edge_basic_auth` because current SSH session has no passwordless sudo; provider gates unchanged; no live provider call. | `tools/afs_public_edge_nginx_fix.py`, `tools/afs_public_edge_preflight.py`, `tests/test_afs_public_edge_nginx_fix.py`, `tests/test_afs_public_edge_preflight.py`, `tests/test_afs_internal_beta_preflight_public_edge.py`, `docs/maintenance/AFS-PUBLIC-EDGE-AUTH-PREFLIGHT-20260620.md`, `DEVLOG.md`; live preflight before fix blocked by Basic Auth; three-end status aligned; server Runtime health ready; focused public-edge tests 11 passed / 1 existing warning. |
| AFS-PUBLIC-EDGE-AUTH-PREFLIGHT-20260620 | Internal Beta Steward + QA Gatekeeper + Release Gatekeeper | Add a safe public-edge preflight and runbook to distinguish Nginx Basic Auth blocking from Runtime app auth, so deployed `/studio/` login loops are diagnosed consistently. | Local tests passed; live preflight currently reports `blocked_by_edge_basic_auth` because the public edge returns 401 Basic Auth while Runtime health is ready. Sudo-side Nginx change is still required. | `tools/afs_public_edge_preflight.py`, `tests/test_afs_public_edge_preflight.py`, `docs/maintenance/AFS-PUBLIC-EDGE-AUTH-PREFLIGHT-20260620.md`; focused tests 3 passed; live report `runs/public_edge_preflight_20260620.json`; provider calls not started. |
| AFS-INTERNAL-BETA-PREFLIGHT-PUBLIC-EDGE-GATE-20260620 | Internal Beta Steward + QA Gatekeeper | Wire public edge auth status into deployed HTTP internal-beta preflight, so acceptance reports fail explicitly on `public_edge_auth` when Nginx Basic Auth blocks Runtime auth. | Local focused tests passed; live deployed preflight currently reports `needs_attention` with `public_edge_auth=failed` and `blocked_by_edge_basic_auth`; provider calls not started. | `tools/afs_internal_beta_acceptance.py`, `tools/afs_internal_beta_acceptance_preflight.py`, `tools/afs_internal_beta_preflight_public_edge.py`, `tests/test_afs_internal_beta_acceptance.py`; focused tests 16 passed / 1 existing warning; live report `runs/internal_beta_preflight_public_edge_latest_20260620.json`. |
| AFS-INTERNAL-BETA-HUMAN-REVIEW-RECORD-20260619 | QA Gatekeeper + Internal Beta Steward | Add a safe human-review record step so completed operator scores and decisions can become a bounded internal-beta evidence artifact after the Markdown checklist. | Local verification passed; provider gates unchanged; no live provider call; no Company OS or long-term memory write. | `tools/afs_internal_beta_human_review_record.py`, `tests/test_afs_internal_beta_human_review_record.py`; red/green record tests; PowerShell UTF-8 BOM regression; CLI smoke generated `accepted_for_next_beta_round` while keeping business/durable claims not claimed; acceptance focused tests 22 passed; `git diff --check` passed. |
