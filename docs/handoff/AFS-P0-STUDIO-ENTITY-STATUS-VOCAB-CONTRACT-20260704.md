# AFS P0 Studio Entity Status Vocabulary Contract - 2026-07-04

Status: `draft / p0_contract_baseline`

Close state: `studio_entity_status_vocab_contract_baseline_added`

This is the P0 shared vocabulary baseline for Studio UI and Owner acceptance
surfaces. It defines entity labels, status mappings, actions, user-facing copy
rules, and non-claims before later P0 lanes for asset auto-binding, node
reference stack, and multi-candidate retry behavior.

It is a contract and routing aid only. It does not implement graph auto-binding,
reference stack UI, multi-candidate retry engine, local keyframe editing, video
adherence review, provider calls, generated-media QA, human acceptance, product
readiness, business validation, public readiness, legal readiness, or
CompanyOS/COS promotion.

## Dispatch

| Field | Value |
|---|---|
| Source thread | `019f25c8-37c9-7e30-8c57-279e40a3a1fc` |
| Lane | `IMPL-P0-STUDIO-ENTITY-STATUS-VOCAB-CONTRACT` |
| Top-down dispatch | `TD-AFS-V02-IMPL-P0-STUDIO-ENTITY-STATUS-VOCAB-CONTRACT-20260704-001` |
| Expected BU | `BU-AFS-V02-IMPL-P0-STUDIO-ENTITY-STATUS-VOCAB-CONTRACT-20260704-001` |
| Route basis | CTO disposition `accept_PM_synthesis_authorize_P0_sequence_preparation` |
| Task class | `Standard` contract-first Studio/docs slice |
| Branch | `codex/p0-studio-entity-status-vocab-contract-20260704` |
| Write scope | This handoff, small Studio vocabulary constants, focused static test, `docs/handoff/INDEX.md`, `TASK_TRACKER.md`, `DEVLOG.md` |
| Provider gate | Closed for LLM, ASR, image, video, external download, live provider calls, provider smoke, and generated-media QA |

Startup protocol:

- `project-development-workflow` was not exposed; fallback startup scan used
  `AGENTS.md`, `docs/company_operating_model.md`, `TASK_TRACKER.md`, and
  `docs/handoff/INDEX.md`.
- Initial status in this isolated worktree was clean detached `HEAD`; the lane
  created branch `codex/p0-studio-entity-status-vocab-contract-20260704`.
- The dispatch was still fresh at startup: `2026-07-03T16:34:43Z`, before
  stale cutoff `2026-07-03T19:05:00Z` (`2026-07-04T03:05:00+08:00`).

## Dirty Ownership Ledger

Pre-write status observed in this worktree:

```text
## HEAD (no branch)
```

| Path | Pre-existing state | Lane action |
|---|---|---|
| Worktree tracked files | Clean before branch creation | Edited only the bounded contract, Studio vocabulary, test, and routing records listed below |
| Untracked files | None visible in initial `git status --short --branch` | No cleanup, delete, archive, move, or source-sync action |

Maintenance ledger: this is an additive contract baseline, not a cleanup,
Chinese-localization, refactor, archive, deletion, runtime migration, provider
operation, or source-sync task.

## Existing Surfaces Used

| Surface | Existing vocabulary observed | Contract use |
|---|---|---|
| `apps/studio/src/generation-status-policy.js` | `submitted`, `pending`, `running`, `complete`, `partially_complete`, `failed`, `retrying`, `needs_attention`, `blocked`, `cancelled_local_only` | Do not replace the status policy; map canonical P0 status labels onto it |
| `apps/studio/src/node-generation-progress.js` | Chinese progress copy for submitted, queued/pending, running, completed, local cancellation | Reuse as UI wording source for active generation progress |
| `apps/studio/src/node-generation-results.js` | `complete`, `partially_complete`, `needs_attention`, `failed`, retry failed items copy | Reuse as result/review wording source |
| `apps/studio/src/asset-lifecycle.js` | asset lifecycle `fixed`, `draft`, `rejected`, `retired` with Chinese labels | Keep as entity-local Project Asset lifecycle, not Runtime job status |
| `docs/handoff/AFS-PROJECT-BOOK-OWNER-ACCEPTANCE-MATRIX-REDISPATCH-20260703.md` | Owner-facing review/decision matrix and non-claim style | Use this contract as a future matrix input, not as acceptance completion |

## Status Vocabulary

Canonical status ids are contract ids. Studio and Runtime may continue to use
their existing equivalent values; UI copy must map through this table instead
of inventing mismatched labels.

| Canonical status | Chinese UI label | Existing equivalents / source values | User meaning | Copy guardrail |
|---|---|---|---|---|
| `queued` | `排队中` | `job.progress.mode=queued`, `job.status=pending`, Studio progress label `排队中` | Request is waiting before active provider/runtime work | Do not imply provider work has started |
| `submitted` | `已提交` | `job.status=submitted`, `setSubmittingGenerationState()` | Runtime accepted a request and created a job identity | Do not imply output exists |
| `running` | `生成中` | `job.status=running`, Studio node `generating`, progress mode `indeterminate` | Work is active or being polled | Do not imply completion time, cost stop, or acceptance |
| `succeeded` | `已完成` | `job.status=succeeded`, Studio policy `complete`, node `complete` | Reviewable output exists | Must say ready for review, not accepted |
| `failed` | `失败` | `job.status=failed`, Runtime `error/failure/timeout`, Studio node `error` | Requested output did not complete | Must show safe blocked reason when available |
| `retryable` | `可重试` | Derived from `failed`, `partially_complete`, `needs_attention`, `shouldRetryFailedItemsOnly()` | User may retry a bounded failed scope | Must state retry may use provider quota when gate is open |
| `cancelled` | `已停止刷新` | `cancelled`, `cancelled_local_only`, Studio node `cancelled` | Local polling or local UI continuation stopped | Must say this does not prove provider-side cancellation or cost stop |
| `blocked` | `已阻断` | Runtime `blocked`, safe manifest `blocks[]`, provider gate closed | Work is blocked before or during execution by a known gate/reason | Must show next requirement, not generic failure only |
| `needs_attention` | `需要检查` | Studio policy `needs_attention`, blocked/cancelled/skipped mapping | User must resolve a reason or review a condition before next step | Must include next action |
| `partial` | `部分完成` | Runtime `partially_complete`, Studio node `partial`, safe manifest `output_count>0` on non-success | Some output is preserved while some requested items failed or are missing | Must preserve visible outputs and retry failed items only by default |

Entity-local states already in use may appear beside these statuses when scoped:

- Project Asset lifecycle: `draft`, `fixed`, `rejected`, `retired`.
- Binding state: `bound`, `unbound`, `replaced`.
- Review decision state: `accepted`, `rejected`, `needs_more_evidence`.

These local states are not provider/runtime job statuses.

## Entity Contract

| Entity | Canonical label | Chinese UI label | User meaning | Allowed states | Next actions | Non-claims |
|---|---|---|---|---|---|---|
| `project_asset` | Project Asset | `项目素材` | A safe project-scoped asset record that can be reviewed, referenced, or reused by Studio | `draft`, `fixed`, `rejected`, `retired`, plus `blocked` / `needs_attention` when evidence is unsafe or unavailable | `reference`, `bind`, `replace`, `reject`, `view evidence`, `view lineage` | Not durable memory, not CompanyOS knowledge, not proof of identity match, not human acceptance |
| `reference_input` | Reference Input | `参考输入` | A user-selected or node-derived visual/text reference candidate for a generation request | `draft`, `bound`, `unbound`, `blocked`, `needs_attention`, `rejected` | `reference`, `bind`, `unbind`, `replace`, `view evidence` | Not guaranteed to be sent to provider until preflight/submit contract includes it; not provider auth |
| `generation_candidate` | Generation Candidate | `生成候选` | A single reviewable output candidate or missing/failed candidate slot from image/keyframe/video generation | `queued`, `submitted`, `running`, `succeeded`, `partial`, `failed`, `retryable`, `cancelled`, `blocked`, `needs_attention`, `accepted`, `rejected` | `retry`, `accept`, `reject`, `view evidence`, `view lineage`, `continue to video` when image/keyframe-compatible | Not final media QA, not selected output unless accepted, not business/legal/public readiness |
| `keyframe_version` | Keyframe Version | `关键帧版本` | A reviewable version of a keyframe tied to a node, candidate, prompt, references, and safe evidence | `draft`, `succeeded`, `partial`, `failed`, `retryable`, `blocked`, `needs_attention`, `accepted`, `rejected` | `accept`, `reject`, `retry`, `edit keyframe`, `continue to video`, `view evidence`, `view lineage` | Local edit is not implemented by this contract; accepted here is not human creative acceptance |
| `video_revision` | Video Revision | `视频修订` | A video attempt or revision tied to a video node and first/last frame or prompt evidence | `queued`, `submitted`, `running`, `succeeded`, `partial`, `failed`, `retryable`, `cancelled`, `blocked`, `needs_attention`, `accepted`, `rejected` | `retry`, `accept`, `reject`, `replace`, `view evidence`, `view lineage` | Not generated-media QA, not adherence score, not public-ready video |
| `binding` | Binding | `绑定` | A safe relationship between a node/request and an asset/reference/candidate | `bound`, `unbound`, `replaced`, `blocked`, `needs_attention` | `bind`, `unbind`, `replace`, `view lineage`, `view evidence` | Not auto-binding behavior, not proof the provider used the reference, not permanent memory |
| `lineage` | Lineage | `来源链路` | A traceable chain of safe refs connecting source inputs, assets, candidates, versions, revisions, jobs, and artifacts | `available`, `partial`, `blocked`, `needs_attention` | `view lineage`, `view evidence`, `reference`, `replace` when source is wrong | Not raw provider response, not local private path, not signed URL, not full provenance certification |

## Action Vocabulary

| Action id | Chinese UI label | Applies to | Preconditions | Resulting contract effect | Non-claims |
|---|---|---|---|---|---|
| `bind` | `绑定` | Project Asset, Reference Input, Binding | Safe project id and reviewable target ref exist | Creates or marks a scoped `binding` relation | Does not implement auto-binding graph behavior |
| `unbind` | `取消绑定` | Reference Input, Binding | Existing binding exists | Marks relation `unbound` for current scope | Does not delete source asset or evidence |
| `replace` | `替换` | Project Asset, Reference Input, Keyframe Version, Video Revision, Binding, Lineage | Replacement target is safe and project-scoped | Supersedes current target for the scoped workflow | Does not erase lineage; previous evidence remains traceable |
| `reference` | `用作参考` | Project Asset, Reference Input, Lineage | Safe reference can be carried to preflight/submit | Adds reference intent to next request surface | Does not guarantee provider call or provider use |
| `retry` | `重试` | Generation Candidate, Keyframe Version, Video Revision | `retryable`, `failed`, `partial`, or `needs_attention` state with retry scope | Starts or prepares bounded retry, failed items only by default | May use provider quota if gate is open; does not guarantee same output |
| `accept` | `采纳` | Generation Candidate, Keyframe Version, Video Revision | Reviewable output exists | Marks output accepted for the next local Studio step | Not human creative acceptance, generated-media QA, or public readiness |
| `reject` | `拒绝` | Project Asset, Generation Candidate, Keyframe Version, Video Revision, Reference Input | User or reviewer chooses not to use target | Prevents target from default carry-forward in that scope | Not deletion; not durable negative memory |
| `view_lineage` | `查看来源链路` | All entities | Safe refs or partial lineage exist | Opens/points to lineage summary | Does not expose raw provider response, private paths, signed URLs, or media bytes |
| `view_evidence` | `查看证据` | All entities | Safe artifact/ref exists | Shows safe manifest, safe summary, or evidence pointer | Not a claim that evidence is complete or accepted |
| `continue_to_video` | `继续生成视频` | Generation Candidate, Keyframe Version | Accepted/reviewable image or keyframe exists | Carries safe first-frame/reference intent to video lane | Does not authorize video provider gate |
| `edit_keyframe` | `编辑关键帧` | Keyframe Version | Reviewable keyframe exists | Enters a future local edit/revision flow when implemented | Local edit behavior is out of scope for this lane |

## Copy Rules

- Use the Chinese UI labels above for user-visible Studio copy; preserve
  canonical ids in tests, traces, docs, and machine-readable constants.
- `已完成` always means reviewable output exists. It must be paired with
  "ready for review / not yet accepted" semantics.
- `采纳` means accepted for the next local Studio step. It must not be used as
  a substitute for human creative acceptance, business validation, or legal
  readiness.
- `已停止刷新` must warn that local cancellation does not prove provider-side
  cancellation or cost stop.
- `部分完成` must keep preserved outputs visible and default retries to failed
  items only.
- `查看来源链路` and `查看证据` must only expose safe refs, safe summaries, and
  safe manifests. They must not expose provider raw response, local private
  paths, signed URLs, secrets, cookies, or media bytes.

## Owner Acceptance Matrix Use

The Owner acceptance matrix may use this contract to ask whether a future Studio
surface uses consistent entity/status/action/copy vocabulary. Passing that check
would only mean vocabulary alignment. It would not mean the feature is accepted,
provider-capable, media-quality-approved, human-reviewed, product-ready,
business-ready, public-ready, legal-ready, or promoted to durable memory/COS.

## Validation

Observed validation for this lane:

```text
git status --short --branch
# before branch:
# ## HEAD (no branch)
#
# after implementation:
# ## codex/p0-studio-entity-status-vocab-contract-20260704
#  M DEVLOG.md
#  M TASK_TRACKER.md
#  M docs/handoff/INDEX.md
# ?? apps/studio/src/studio-entity-status-vocabulary.js
# ?? docs/handoff/AFS-P0-STUDIO-ENTITY-STATUS-VOCAB-CONTRACT-20260704.md
# ?? tests/test_web_studio_entity_status_vocabulary_static.py

git diff --check
# passed; no output

npm run check:studio-js
# JS syntax check passed: 139 files

python3 -m py_compile tests/test_web_studio_entity_status_vocabulary_static.py
# passed; no output

node --input-type=module -e '<import vocabulary and assert required ids>'
# passed; no output

python3 - <<'PY' '<assert contract doc, Studio vocabulary, tracker, devlog, and index markers>'
# passed; no output

git diff --check --no-index /dev/null docs/handoff/AFS-P0-STUDIO-ENTITY-STATUS-VOCAB-CONTRACT-20260704.md
git diff --check --no-index /dev/null apps/studio/src/studio-entity-status-vocabulary.js
git diff --check --no-index /dev/null tests/test_web_studio_entity_status_vocabulary_static.py
# no whitespace output for new files; wrapper recorded each as passed

python3 -m pytest tests/test_web_studio_entity_status_vocabulary_static.py -q
# blocked: /usr/bin/python3: No module named pytest

.venv/bin/python -m pytest tests/test_web_studio_entity_status_vocabulary_static.py -q
# blocked: .venv/bin/python not found or not executable
```

Recovery validation addendum for
`FIX-P0-STUDIO-ENTITY-STATUS-ACTION-CONSISTENCY`:

```text
git diff --check
# passed; no output

npm run check:studio-js
# JS syntax check passed: 139 files

python3 -m py_compile tests/test_web_studio_entity_status_vocabulary_static.py
# passed; no output

node --input-type=module '<assert every entity nextAction is allowed by action.appliesTo>'
# checked 39 entity nextAction/applyTo pairs

python3 -m pytest tests/test_web_studio_entity_status_vocabulary_static.py -q
# blocked: /usr/bin/python3: No module named pytest

.venv/bin/python -m pytest tests/test_web_studio_entity_status_vocabulary_static.py -q
# blocked: /bin/bash: line 1: .venv/bin/python: No such file or directory
```

Provider, Runtime server, browser QA, OpenAPI, source-sync, deploy/restart,
generated-media QA, and full pytest are intentionally out of scope for this P0
docs/constants contract slice.

## Archive Policy

| Field | Value |
|---|---|
| `archive_after_ack_delivery_confirmed` | `true` |
| `owner_manual_archive_excluded` | `no` |
| `thread_archive_policy` | `agent_created_archive_when_useless` |

This lane must not self-archive. Archive requires ACK delivery confirmation.

## Post-Closeout Next Action

CEO should ACK/register this BU and route to CTO/PM/CPO/COO. CTO should decide
whether to open evaluator lane
`EVAL-P0-STUDIO-ENTITY-STATUS-VOCAB-CONTRACT` before starting the next P0
implementation lanes for asset auto-binding, node reference stack, or
multi-candidate retry.
