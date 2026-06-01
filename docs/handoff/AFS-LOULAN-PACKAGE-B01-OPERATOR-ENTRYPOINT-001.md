# AFS-LOULAN-PACKAGE-B01-OPERATOR-ENTRYPOINT-001

Status: Loulan B01 operator entrypoint package intake implemented.

## Scope

`loulan-memory-package` now reads optional:

```text
manifests/b01_operator_entrypoint.json
```

and emits:

```text
feedback_loop_gates.b01_operator_entrypoint
```

The field is a sanitized no-call summary for the operator-facing B01 review
entrypoint. It is review evidence only and does not approve B01, apply
decisions, project context, or promote memory.

## Package Fields

| Field | Meaning |
|---|---|
| `status` | B01 operator entrypoint status |
| `decision_items` | B01 decision count |
| `pending_decisions` | decisions still requiring human input |
| `validation_status` | local B01 validation gate |
| `apply_status` | local B01 apply gate |
| `next_context_status` | next context bundle blocker |
| `operator_steps` | review sequence length |
| `blocked_until_count` | explicit blocker count |
| `recommendations` | AI recommendation rows |
| `pending_operator_decisions` | recommendations not yet accepted by a human |

## Web Surfaces

| Surface | Behavior |
|---|---|
| Bundle summary | shows `B01 operator entrypoint` with pending decision and operator-step counts |
| Protocol controls | shows the entrypoint blocked status and operator-step count |
| Inspector | shows `b01_operator_entrypoint: blocked_pending_human_review` |
| Timeline | shows `B01 Operator Entrypoint` with pending decision and operator-step counts |

## Boundaries

- No provider calls.
- No media generation or media copy.
- No decision apply.
- No context projection.
- No browser persistence or project-file writes.
- No human acceptance recorded.
- No durable Memory write.

## Verification Snapshot

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_memory_package.py tests\test_web_memory_loulan_package_static.py -q
# 5 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain -q
# 763 passed

.\.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
# passed

git diff --check
# passed; CRLF normalization warnings only
```

## Next Work

- Keep B01 blocked until the human operator fills the five B01 decisions.
- After a ready validation/apply dry run exists, regenerate the package and
  verify that only explicitly approved/promoted refs enter the next context.
