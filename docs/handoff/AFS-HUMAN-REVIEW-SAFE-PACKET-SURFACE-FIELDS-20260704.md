# AFS Human Review Safe Packet Surface Fields - 2026-07-04

TD:
`TD-AFS-V02-IMP-P1-REL1B-HUMAN-REVIEW-SAFE-PACKET-SURFACE-FIELDS-20260704-001`

BU:
`BU-AFS-V02-IMP-P1-REL1B-HUMAN-REVIEW-SAFE-PACKET-SURFACE-FIELDS-20260704-001`

Lane: `IMP-P1-REL1B-HUMAN-REVIEW-SAFE-PACKET-SURFACE-FIELDS`

Branch:
`codex/imp-p1-rel1b-human-review-safe-packet-surface-fields-20260704`

## Scope

Implemented a bounded Runtime source/contract slice for future redacted human
review packet assembly. This does not create a human acceptance flow and does
not claim packet readiness.

Changed surfaces:

- Keyframe safe manifest and candidate summary now persist `review_preview_refs`
  containing safe preview route metadata only: `job_id`, `candidate_id`,
  `safe_preview_ref`, `byte_count`, `sha256`, `width`, `height`, and
  `aspect_ratio`.
- Prompt optimization now writes
  `prompt_optimization_review_summary.json` and registers it as
  `prompt_optimization_review_summary`. The summary persists
  `optimized_prompt_char_count`, sanitized bounded `optimized_prompt_text`,
  truncation state, and `source_artifact_id` for the creative brief.
- `apps/api/runtime_human_review_safe_packet.py` provides a fail-closed
  selector/builder that reads only persisted safe preview refs and prompt
  summary fields.

## Fail-Closed Contract

The safe packet builder raises `ValueError` when:

- `review_preview_refs` is missing or empty.
- a preview ref lacks `job_id`, `candidate_id`, `safe_preview_ref`,
  `byte_count`, `sha256`, `width`, or `height`.
- prompt summary lacks `optimized_prompt_char_count`, `optimized_prompt_text`,
  or `source_artifact_id`.
- artifact project scope does not match the requested project.
- selected packet output contains private path, expiring URL, credential,
  provider-response, or binary-payload markers.

## Validation

Passed:

```text
python3 -m py_compile apps/api/runtime_keyframe_payloads.py apps/api/runtime_keyframes.py apps/api/runtime_keyframe_async.py apps/api/runtime_prompt_memory.py apps/api/runtime_prompt_review_summary.py apps/api/runtime_artifacts.py apps/api/runtime_human_review_safe_packet.py tests/test_api_runtime_human_review_safe_packet.py
git diff --check
```

Focused pytest was attempted but blocked in this checkout:

```text
/usr/bin/python3: No module named pytest
```

Environment notes:

- No `.venv/bin/python` was present.
- No `python` command was present.
- `/usr/bin/python3` is Python 3.12.3.
- `fastapi` and `pydantic` are missing from system Python, so Runtime route
  execution could not be validated here.

Pending before integration:

- Run `tests/test_api_runtime_human_review_safe_packet.py` in a repo environment
  with pytest/FastAPI/Pydantic installed.
- Run adjacent Runtime prompt/keyframe suites if this branch proceeds to
  integration review.

## Non-Claims

No provider gate was opened. No remote provider, deploy, restart, source sync,
fetch, pull, push, generated-media QA, human creative acceptance, product
readiness, business/legal/public readiness, CompanyOS/COS update, or durable
memory promotion occurred.

Archive policy:
`agent_created_archive_when_useless`,
`owner_manual_archive_excluded=no`,
`archive_after_ack_delivery_confirmed=true`.

Post-closeout next action: CEO ACK/register/route to CTO/CPO/PM/COO; evaluator
required before integration or packet-readiness claim.
