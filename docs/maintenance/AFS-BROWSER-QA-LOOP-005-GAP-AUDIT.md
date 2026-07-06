# AFS Browser QA Loop 005 Gap Audit

Date: 2026-06-14
Branch: `codex/afs-agent-browser-repair-loop-005`
Claim level: runtime/browser verification planning and evidence audit only. This is not human acceptance.

## North Star

Internal testers should be able to finish the core creative path without being blocked, and "what they see" before submit should match "what is sent" to the provider. The target is ready for human acceptance, not zero defects.

## L0 Evidence

Loop 003 red baseline is now present in the active line:

- `docs/maintenance/AFS-AGENT-BROWSER-QA-LOOP-003.md`

Known Loop 003 issues:

| ID | Severity | Status in current line | Evidence |
|---|---|---|---|
| QAL003-001 fixed asset conflict submit without confirmation | P1 | Fixed, needs continued browser matrix verification | preflight token tests, carry confirmation UI, `test_loop003_qal003_001_fixed_asset_submit_interlock_has_regression_markers` |
| QAL003-002 generated image lacks fixed-asset promotion entry | P1 | Fixed, needs browser matrix verification from generated candidate card/drawer | reusable image asset plumbing, drawer promotion actions, `test_loop003_qal003_002_generated_image_promotion_entries_have_regression_markers` |
| QAL003-003 asset detail reads stale cache and lacks remove/exclude | P1 | Fixed, needs browser matrix verification | Runtime `GET /visual-assets/{asset_id}`, popover Runtime fetch, `test_loop003_qal003_003_asset_detail_reads_runtime_and_exposes_node_actions` |
| QAL003-004 current/recent QA projects hidden by dropdown filter | P2 | Fixed | recent project static regression |
| QAL003-005 Kling UI implies audio for silent output | P2 | Fixed | no-sound static regression |

Track A contract is present in the active line:

- request-level `temporary_asset_exclusions`
- keyframe/video preflight endpoints
- preflight token consistency checks
- Runtime visual asset detail endpoint

## L1 Gap Audit

| Requirement | Current evidence | Status |
|---|---|---|
| 5 known P1 all closed with automated regressions | QAL003 has 3 P1 and 2 P2. Explicit QAL003 regression tests added in Loop 005. | Partially proven; focused tests must pass. |
| Two full role-matrix rounds with zero new P0/P1 | Loop 004 only covered a narrower verification slice. | Missing. Must run browser matrix rounds after tests. |
| Core 5 paths each run once: T2I / I2I / fixed carry / conflict exclusion / Kling I2V | Prior hardening docs contain evidence, but not yet rerun after Loop 004 preflight changes. | Missing for current acceptance cycle. |
| "What is seen is what is generated" | Preflight token tests exist; carry confirmation UI exists. | Needs focused test pass and browser confirmation. |
| Zero leak: every generation manifest passes leak assertions | Existing fields are safe; Loop 005 adds dedicated keyframe/video manifest safety tests. | Partially proven; focused tests must pass. |
| Baseline green | Previous branch was green. | Missing after Loop 005 edits. |
| Human acceptance runbook | `docs/handoff/AFS-HUMAN-ACCEPTANCE-RUNBOOK-005.md` is the current entrypoint. | Present, but human acceptance not claimed. |

## Next Evidence To Collect

1. Focused tests for Loop 003 regressions and generation manifest safety.
2. Studio JS syntax check after static-test marker changes.
3. Browser role-matrix Round A:
   - small user path
   - creator T2I/I2I
   - asset admin fixed/detail/retire
   - graph user carry/exclusion
   - video user Kling I2V
   - destructive project switching/cancel/retry
   - safety manifest spot checks
4. Browser role-matrix Round B after any P0/P1 fixes.

## Boundaries

- MiniMax identity similarity and Kling first-frame quality remain human-scored.
- Browser screenshots are exploration evidence. Regression protection must come from tests or deterministic route checks.
- Keep Kling live usage to 3 per round unless the user explicitly approves more.

## Round A Evidence - 2026-06-14

Runtime: `http://127.0.0.1:8796/studio/`
Runtime root: `runs/agent_browser_qa_loop_005/iab_runtime`
Project ids:

- `loop005-iab-round-a`
- `loop005-iab-empty-b`

Live provider usage in this round:

- MiniMax image: 2 calls.
- Kling I2V: 2 submits. This stays under the hard round cap of 3.

### Passed Paths

| Path | Evidence | Result |
|---|---|---|
| T2I optimize through live LLM | In-app browser modal reached `已优化`; `prompt_optimization_safe_manifest.json` status `succeeded`, `optimization_mode=t2i`, `format_retry_count=0`, `format_salvage_used=false`. | Passed. The prior 422 optimizer failure is fixed for this path. |
| T2I live MiniMax image generation | `loop005-iab-round-a-keyframe_generation-505d609f8469`; node completed with preview; `provider_prompt` contains no human section labels or internal gate terms. | Passed. |
| Generated image fixed as character asset | Node toolbar `固定为资产` opened the review panel; signature and feature-card fields were prefilled; confirm created node `1资产` badge. | Passed. |
| Runtime-backed asset detail | Clicking `1资产` showed signature, feature card, lock list, source node, `从当前节点移除`, and `本次不携带`. | Passed. |
| Carry confirmation | Submitting with one fixed asset opened `生成前确认`, always listed carried assets, and displayed “未检测到明显冲突，但固定资产仍会约束结果.” Cancel did not submit a provider job. | Passed. |
| One-run asset exclusion | `本次不携带选中项` submitted a new generation with no included asset, no reference image, no subject reference, and no asset signature in provider prompt. | Passed, with trace duplicate noted below and fixed in code. |
| Refresh persistence | Browser reload preserved image preview and `1资产` badge. | Passed. |
| Project isolation | Switching to `loop005-iab-empty-b` showed zero nodes and no old node/asset; switching back restored the original project. | Passed. |
| Video no-first-frame guard | Video node with no explicit first frame returned user-facing failure text and did not submit. | Passed. |
| Kling UI no-sound control | Video node showed Kling I2V controls and no `声音`/audio option. | Passed. |
| Kling I2V live submit/poll/preview | After the Runtime fix below, `loop005-iab-round-a-video_generation-3cd1d507b20d` returned `submitted`, then `running`, then `succeeded`; preview route returned MP4 bytes; safe manifest stored no provider raw, URL, secret, or local path. | Passed. |

### Issues Found And Fixed In This Branch

| ID | Severity | Finding | Fix | Regression |
|---|---|---|---|---|
| QAL005-001 | P1 | Live LLM optimizer could still return chatty article/tutorial prose, causing Studio 422 instead of usable sections. | Added prompt-enhancement formatter system message, strict retry, and salvage from repeated LLM article output without reintroducing the old local deterministic optimizer path. | `tests/test_api_runtime_prompt_memory_loop.py` prompt format/retry/salvage cases; `tests/test_openai_compatible_provider.py`. |
| QAL005-002 | P1 | External provider config still used legacy `NARRATOCUT_ALLOW_REMOTE_*` gates, causing “service not ready” despite AFS gates being open. | Provider descriptor gate defaults now normalize legacy gate names to `AFS_ALLOW_REMOTE_*` in the registry path. | `tests/test_provider_adapter_registry.py`. |
| QAL005-003 | P2 | A temporarily excluded asset appeared twice in `context_bundle.excluded_assets`: `temporary_asset_excluded_by_user` and `not_connected_to_target`. | Resolver now suppresses generic excluded reasons for asset ids that already have explicit exclusions. | `tests/test_api_runtime_context_resolver.py::test_temporary_asset_exclusion_removes_asset_from_prompt_reference_and_subject`. |
| QAL005-004 | P0 | Kling submit could succeed remotely but Runtime returned 422 before writing `video_generation_safe_manifest.json`, because `output_dir` from the adapter task was persisted into `video_task_state.json` and rejected by safe payload checks. | Runtime strips adapter `output_dir` before persisting task state and injects it only transiently during poll. | `tests/test_api_runtime_video_generations.py::test_video_generation_strips_adapter_output_dir_from_persisted_task_state`. |

### Issues Still Open Or Deferred

| ID | Severity | Finding | Status |
|---|---|---|---|
| QAL005-005 | P2 | Empty project shows zero nodes and no contamination, but did not show the explicit “当前画布为空” phrase in the in-app snapshot. | Defer as copy/empty-state polish; not data pollution. |
| QAL005-006 | P2 | The in-app browser automation surface cannot reliably bulk-type text because the virtual clipboard is unavailable. | Testing limitation, not product behavior. Use existing Playwright QA scripts for text-heavy paths. |
| QAL005-007 | P2 | `本次不携带选中项` immediately re-preflights and submits. This is contract-compatible but gives no second final confirmation after exclusion. | Defer for UX review; no evidence of wrong provider payload. |
| QAL005-008 | P2 | Hidden Kling CLI resume still uses old `NARRATOCUT_ALLOW_REMOTE_VIDEO` gate text. Runtime registry path is normalized; CLI smoke path remains legacy. | Defer unless CLI smoke becomes an internal-test entrypoint. |

### Evidence Paths

- `runs/agent_browser_qa_loop_005/studio_asset_context_browser_qa_report_llm_external_1.json`
- `runs/agent_browser_qa_loop_005/iab_runtime/runs/loop005-iab-round-a/loop005-iab-round-a-prompt_optimization-f7e28182d188/`
- `runs/agent_browser_qa_loop_005/iab_runtime/runs/loop005-iab-round-a/loop005-iab-round-a-keyframe_generation-505d609f8469/`
- `runs/agent_browser_qa_loop_005/iab_runtime/runs/loop005-iab-round-a/loop005-iab-round-a-keyframe_generation-4f6afdab87de/`
- `runs/agent_browser_qa_loop_005/iab_runtime/runs/loop005-iab-round-a/loop005-iab-round-a-video_generation-77e4744b5a16/`
- `runs/agent_browser_qa_loop_005/iab_runtime/runs/loop005-iab-round-a/loop005-iab-round-a-video_generation-3cd1d507b20d/`

### Round A Boundary

Round A is not a full closeout. It found one P0 and two P1 issues and fixed them with regression tests. The formal Loop 005 close condition still requires another complete role-matrix round after the new fixes, with zero new P0/P1, plus baseline tests.

## Round B Valid-Media Evidence - 2026-06-14

Runtime: `http://127.0.0.1:8796/studio/`
Runtime root: `runs/agent_browser_qa_loop_005/iab_runtime_round_b`
Project id: `loop005-round-b-valid-2`

Live provider usage in this round:

- MiniMax image: 3 submits.
- Kling I2V: 1 submit. Combined with the earlier invalid-media attempt, this round used 2 of the hard cap of 3 Kling submits.

### Passed Paths

| Path | Evidence | Result |
|---|---|---|
| Real-size image upload | `img_0bf144d8cf4c`, 1672x941, 1.86MB public metadata only. | Passed. |
| I2I with real reference | `loop005-round-b-valid-2-keyframe_generation-ba137b5b4b02`; MiniMax returned one preview and one reusable image asset. | Passed. |
| Fixed visual asset promote | `vas_92e1bc9ecea1`; feature card and locks stored through Runtime visual asset API. | Passed. |
| Fixed asset carry preflight + submit | Preflight returned one included asset, subject reference `vas_92e1bc9ecea1`, stable token; submit succeeded with one preview and one included asset. | Passed. |
| Current-run asset exclusion | Preflight returned zero included assets, no subject reference, excluded reason `temporary_asset_excluded_by_user`; submit succeeded with no included asset. | Passed. |
| Kling I2V with valid first frame | `loop005-round-b-valid-2-video_generation-7aafc4cd3d91`; submit returned `submitted`, polls 1-5 were `running`, poll 6 returned `succeeded` with one preview. | Passed. |
| Studio visible load check | In-app browser loaded `?project=loop005-round-b-valid-2`; title `AFS Studio 创作图谱`; project id visible; Studio controls visible; no `声音`/`audio`; console warn/error count 0. | Passed. |

### New Issue Found And Fixed

| ID | Severity | Finding | Fix | Regression |
|---|---|---|---|---|
| QAL005-009 | P1 | Round B first used a 64x64/104-byte placeholder PNG as I2I reference and Kling first frame. Both provider calls started and then failed remotely. This is a cost/UX guardrail gap: invalid reference media should be blocked before a paid provider submit. | Added descriptor-driven `min_reference_image_edge_px`; MiniMax image and Kling video default to 256px minimum edge. Runtime now blocks too-small reference/first-frame images before dispatch/submit with safe manifest `provider_calls_started=false`. Fake providers keep default 0 and are not affected. | `tests/test_api_runtime_keyframe_reference_assets.py::test_tiny_keyframe_reference_blocks_before_remote_provider_dispatch`; `tests/test_api_runtime_video_generations.py::test_tiny_video_first_frame_blocks_before_provider_submit`; focused provider/video/reference set 37 passed. |

### Evidence Paths

- `runs/agent_browser_qa_loop_005/round_b_runtime_summary.json`
- `runs/agent_browser_qa_loop_005/round_b_valid_runtime_summary.json`
- `runs/agent_browser_qa_loop_005/round_b_valid_studio_load.png`
- `runs/agent_browser_qa_loop_005/iab_runtime_round_b/runs/loop005-round-b-runtime/`
- `runs/agent_browser_qa_loop_005/iab_runtime_round_b/runs/loop005-round-b-valid-2/`

### Round B Boundary

Round B valid-media paths closed the live I2I, fixed asset carry, current-run exclusion, and Kling I2V runtime paths with no new product P0. It did find one P1 guardrail gap for tiny reference media, now fixed with automated regressions. Because a new P1 was found during this round, Loop 005 still needs another clean browser/runtime matrix round with zero new P0/P1 before closeout.

## Round C Evidence - 2026-06-14

Runtime: `http://127.0.0.1:8796/studio/`
Runtime root: `runs/agent_browser_qa_loop_005/iab_runtime_round_c`
Project id: `loop005-round-c-clean-1`

Live provider usage in this round:

- MiniMax image: 4 submits.
- Kling I2V: 1 submit.
- Remote LLM prompt optimization: 1 blocked probe, then 1 successful retry after the fix.

### Passed Paths

| Path | Evidence | Result |
|---|---|---|
| T2I / upload / I2I / fixed asset / detail | `round_c_runtime_summary.json` records successful T2I, upload metadata, I2I, promote `vas_3b0d5bace6b1`, and Runtime asset detail. | Passed. |
| Fixed asset carry | Preflight included 1 asset, selected subject reference asset, returned a token; submit produced one image preview. | Passed. |
| One-run exclusion | Preflight included 0 assets, recorded `temporary_asset_excluded_by_user`, cleared subject reference, and submit produced one image preview. | Passed. |
| Kling I2V recovery | Submit reached `submitted`/`running`; first poll sequence hit `poll_failed`, immediate recovery poll reached `succeeded` with one preview. | Passed as recoverable provider poll intermittency. |
| Browser load | In-app browser loaded `?project=loop005-round-c-clean-1`, project id visible, Studio shell visible, no `audio`/sound entry, console warn/error count 0. | Passed. |

### New Issue Found And Fixed

| ID | Severity | Finding | Fix | Regression |
|---|---|---|---|---|
| QAL005-010 | P1 | Studio-style prompt optimization request included `node_parameters.model=minimax_image` plus `llm_provider=minimax_m3`; the image model value masked the LLM fields and returned 422 `not_requested`. | `minimax_text_requested()` now checks `llm_provider`, then `llm_model`, then `model`, so Studio image model selection no longer suppresses remote LLM optimization. | `tests/test_api_runtime_prompt_memory_loop.py::test_studio_prompt_optimizer_uses_llm_fields_even_when_image_model_is_selected`. |

### Evidence Paths

- `runs/agent_browser_qa_loop_005/round_c_runtime_summary.json`
- `runs/agent_browser_qa_loop_005/round_c_studio_load.png`

### Round C Boundary

Round C found and fixed one new P1, so it is not a clean round.

## Round D Clean Evidence - 2026-06-14

Runtime: `http://127.0.0.1:8796/studio/`
Project id: `loop005-round-d-clean-3`

Live provider usage:

- Remote LLM prompt optimization: 1.
- MiniMax image: 4 submits.
- Kling I2V: 1 submit, under the hard cap of 3.

### Passed Paths

| Path | Evidence | Result |
|---|---|---|
| Remote LLM optimization | `round_d3_runtime_summary.json` shows provider call started, requested true, status `applied`, model `MiniMax-M2.7-highspeed`. | Passed. |
| T2I | One reusable image asset and one candidate preview returned. | Passed. |
| Upload / I2I | Uploaded generated reference metadata is 720x1280 with safe preview URL; I2I returned one candidate and one reusable asset. | Passed. |
| Fixed asset / detail | Fixed visual asset created; Runtime detail returned status, feature keys, and locks. | Passed. |
| Carry preflight + submit | Included 1 fixed asset, subject reference set, token present, submit returned one preview. | Passed. |
| One-run exclusion | Included 0 assets, excluded reason `temporary_asset_excluded_by_user`, no subject reference, submit returned one preview. | Passed. |
| Kling I2V | Status sequence reached `succeeded`; one preview returned through safe video route. | Passed; one transient `poll_failed` recovered in the same round. |
| Browser load | In-app browser loaded `?project=loop005-round-d-clean-3`, project id visible, Studio shell visible, no `audio`/sound entry, console warn/error count 0. | Passed. |

### Harness Notes

Two earlier Round D attempts failed because the QA driver changed `generated_at` between preflight and submit, then passed video `motion` as an object instead of the contract string. These were harness errors, not product defects; the clean Round D reran the same product paths with correct request contracts.

### Evidence Paths

- `runs/agent_browser_qa_loop_005/round_d3_runtime_summary.json`
- `runs/agent_browser_qa_loop_005/round_d3_studio_load.png`

### Round D Boundary

Round D is clean: no new product P0/P1.

## Round E Clean Evidence - 2026-06-14

Runtime: `http://127.0.0.1:8796/studio/`
Project id: `loop005-round-e-clean-1`

Live provider usage:

- Remote LLM prompt optimization: 1.
- MiniMax image: 4 submits.
- Kling I2V: 1 submit, under the hard cap of 3.

### Passed Paths

| Path | Evidence | Result |
|---|---|---|
| Remote LLM optimization | `loop005-round-e-clean-1_runtime_summary.json` shows provider call started, requested true, status `applied`, model `MiniMax-M2.7-highspeed`. | Passed. |
| T2I | One reusable image asset and one candidate preview returned. | Passed. |
| Upload / I2I | Uploaded generated reference metadata is 720x1280 with safe preview URL; I2I returned one candidate and one reusable asset. | Passed. |
| Fixed asset / detail | Fixed visual asset created; Runtime detail returned status, feature keys, and locks. | Passed. |
| Carry preflight + submit | Included 1 fixed asset, subject reference set, token present, submit returned one preview. | Passed. |
| One-run exclusion | Included 0 assets, excluded reason `temporary_asset_excluded_by_user`, no subject reference, submit returned one preview. | Passed. |
| Kling I2V | Status sequence reached `succeeded`; one preview returned through safe video route. | Passed. |
| Browser load | In-app browser loaded `?project=loop005-round-e-clean-1`, project id visible, Studio shell visible, no `audio`/sound entry, console warn/error count 0. | Passed. |

### Evidence Paths

- `runs/agent_browser_qa_loop_005/loop005-round-e-clean-1_runtime_summary.json`
- `runs/agent_browser_qa_loop_005/round_e_studio_load.png`

### Round E Boundary

Round E is clean: no new product P0/P1. Together with Round D, Loop 005 satisfies the "two consecutive clean role-matrix rounds" criterion at runtime/browser verification level.

## Loop 005 Closeout Boundary

Runtime/browser verification is now complete for the tested MVP paths. This is still not human acceptance. Human acceptance starts only when the user runs `docs/handoff/AFS-HUMAN-ACCEPTANCE-RUNBOOK-005.md` and records pass/fail plus creative-quality scores.
