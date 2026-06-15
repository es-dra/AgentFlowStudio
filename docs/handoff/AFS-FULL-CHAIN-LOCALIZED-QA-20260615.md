# AFS Full-Chain Localized QA - 2026-06-15

## Scope

This handoff records the Codex + Claude checkpoint run for two goals:

1. Prove the current AFS Studio MVP full chain can run end to end.
2. Evaluate whether the current architecture can support localized image/video changes where the requested element changes and unrelated areas stay roughly stable.

Evidence root: `20260615-afs-full-chain-localized-qa` outside the repository.

## Gate Boundary

- Runtime was restarted from the current worktree after a stale 8790 service was detected.
- Runtime `/health` reported Studio static ready and provider gates:
  - LLM: open
  - image: open
  - video: open
  - ASR: closed
  - external download: closed
- Existing untracked `tools/run_studio_all_gates.ps1` was not used because it opens ASR and points at repo-local provider config.
- Repository records do not include provider config paths, provider secrets, signed URLs, provider raw responses, or media bytes.

## Deterministic Verification

Before live calls:

```text
pytest -q -> 417 passed, 527 deselected, 2 warnings
pytest -m legacy -q -> 527 passed, 417 deselected, 1 warning
Studio JS node --check -> passed
maintenance_audit.py -> failed=0, warnings only
git diff --check -> passed
```

After the prompt-contract fix:

```text
tests/test_runtime_context_text.py -> 3 passed
tests/test_api_runtime_context_resolver.py tests/test_api_runtime_creative_agent_keyframes.py -> 26 passed, 1 warning
```

Final closeout after records were updated:

```text
pytest -q -> 420 passed, 527 deselected, 2 warnings
pytest -m legacy -q -> 527 passed, 420 deselected, 1 warning
Studio JS node --check -> passed
maintenance_audit.py -> failed=0, warnings only
git diff --check -> passed
```

## Browser / Runtime QA

- In-app Browser opened `http://127.0.0.1:8790/studio/`; title loaded, `canvas-root` was mounted, and console warn/error count was zero.
- `tools/studio_asset_context_browser_qa.py --allow-live-llm` passed with image/video/ASR gates closed in its isolated browser QA runtime. This rechecked named fixed-asset warning, one-click connect, carry confirmation, temporary unlock, and comparison flow.

## Live Provider Round

Provider calls were bounded:

- MiniMax image: two calls, `candidate_count=1`
- Kling I2V: one submit, `candidate_count=1`
- ASR and external download: no calls

Results:

- MiniMax T2I base image succeeded and produced one reusable image asset.
- The base image was promoted to a fixed visual asset.
- MiniMax reference-backed I2I succeeded with:
  - `reference_image_count=1`
  - `context_included_asset_count=1`
  - `provider_calls_started=true`
  - no raw provider response persisted
  - no media bytes returned by API
- Kling I2V succeeded from the edited image:
  - H.264, 1080x1920, 24fps, 5.04s
  - one safe Runtime preview
  - no provider URL persisted
- `video_revision` preflight/submit stayed blocked:
  - `block_id=experimental_video_revision_disabled`
  - `provider_calls_started=false`

## Localized Edit Finding

The full chain ran, but localized image quality did not pass the user goal in this live sample.

Observed image result:

- Preserved roughly: single subject, black short hair, beige trench coat, light turtleneck, gray background.
- Failed target edit: requested one subtle left-eyebrow scar; output instead introduced prominent forehead/brow wrinkles.
- Non-target drift: face shape and expression shifted enough that this should not be called accepted localized editing.

Root-cause hypothesis:

- The provider prompt for reference-backed localized edits put fixed-asset identity and locks before the requested delta.
- The fixed asset signature included "no scar in base asset", which competed with "add scar".
- The optimized prompt was long and diluted the edit target before provider truncation.

Fix applied:

- `provider_prompt_from_bundle` now detects reference-backed localized edit language and leads with:
  - requested change
  - preserve policy
  - explicit instruction that base descriptors are anchors, not undo instructions
- Ordinary fixed-asset generation keeps the previous identity-first ordering.
- This is a deterministic prompt-contract hardening, not proof that provider quality is fixed.

Required next validation:

- One authorized paid image retest after this fix, using the same base/reference and the scar/lighting edit target.
- Score both target-change success and non-target drift before calling image localized editing ready.
- Confirm whether the active image provider path exposes true masked/regional inpainting. If it remains full-frame I2I only, prompt ordering can reduce instruction conflict but cannot guarantee unrelated pixels stay stable.

## Video Localized Editing Boundary

Current video chain is Kling I2V smoke plus experimental revision contract only.

The architecture can now record:

- base video lineage
- editable targets
- locked aspects
- temporal scope
- preserve policy
- safe blocked manifest

It does not yet productize:

- accepted base video -> localized re-render
- frame/segment-level lighting edit
- motion-only change while preserving unrelated content
- V2V/masked/temporal provider submit

Conclusion: video partial adjustment remains a capability gap, not a passed MVP feature.

## Claude Checkpoints

Claude reviewed:

- gate and evidence boundary before live provider calls
- image/video localized-edit claim boundaries after live evidence
- deterministic prompt-contract fix direction

Claude recommendation accepted:

- Record flow as complete.
- Record localized image quality as not yet verified after the fix.
- Record video localized editing as experimental/not productized.
- Do not make more provider calls without user approval.

## Current Status

Recommendation: `needs_followup_quality_retest`.

The technical full chain is running end to end. The architecture has the prompt/context/asset hooks needed to attempt localized image edits, but the tested path is still full-frame reference-backed I2I and this run found a quality failure. The deterministic prompt ordering contract was fixed, but masked/regional editing support and one paid quality retest remain open before localized image editing can be called ready. Video localized editing is still a product gap behind an experimental blocked contract.

Non-claims:

- not human acceptance
- not business validation
- not durable memory
- not proof that image localized quality is fixed
- not proof that video localized editing is productized
