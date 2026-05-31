# AFS-LOULAN-WEB-DECISION-REVIEW-001

Status: Loulan decision review pack selected-file rendering implemented.

## Scope

The Web memory workbench now recognizes:

```text
agentflow_loulan_decision_review_pack
```

Selected-file projection adds:

- `workspace.loulanDecisionReviewPack`
- "Decision review pack" bundle card
- "decision review" protocol control
- next-pass status/action from `review_status`
- inspector facts for pending, ready, missing, provider, and acceptance flags
- "Decision Review" timeline node

## Boundary Evidence

- Rendering is read-only.
- The browser still requires explicit selected files.
- No directory scanning, browser persistence, workflow execution, artifact
  write, provider call, Company memory write, or approval inference was added.
- `blocked_pending_human_input` stays blocked and is not treated as human
  acceptance.

## Verification Snapshot

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_memory_loulan_decision_context_static.py -q
# 2 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_memory_static_structure.py tests\test_web_memory_canvas_static.py tests\test_web_memory_interaction_static.py tests\test_web_memory_sample_static.py tests\test_web_memory_feedback_static.py tests\test_web_memory_loulan_package_static.py tests\test_web_memory_loulan_human_review_static.py tests\test_web_memory_loulan_decision_context_static.py -q
# 21 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain -q
# 716 passed

.\.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
# passed

git diff --check
# passed; CRLF normalization warnings only
```

In-app Browser tooling was not exposed in this session, `agent-browser` was not
installed, and no local Chrome/Edge executable was found. Browser-level
verification is therefore deferred; static Node rendering tests covered the
selected-file Web projection.

## Next Work

- Add a copy-only decision worksheet/export if the operator needs a tighter
  manual-fill surface.
- After a human fills a decisions file, run `loulan-context-bundle` and load
  the ready projection into the workbench.
- Keep live provider calls blocked until an explicit capability gate and local
  provider config are authorized.
