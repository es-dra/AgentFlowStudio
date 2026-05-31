# AFS-LOULAN-WEB-CONTEXT-001 - Loulan Web Decision Context

## Task

Render Loulan decision templates and context bundle projections in the Memory
Workbench as read-only selected artifacts.

## Goal

The canvas workbench should show where the Loulan flow is blocked or partially
ready after review:

```text
review pack -> decision template -> context bundle projection -> next pass
```

## Non-goals

- Do not add browser persistence.
- Do not auto-scan local directories or follow refs.
- Do not create or edit human decisions in the browser.
- Do not call providers or write artifacts from the Web UI.

## Owner Role

Web UI Agent + Memory / Evidence Steward + QA Reviewer

## Acceptance Criteria

- [x] Workspace normalization recognizes
      `agentflow_loulan_promotion_decisions`.
- [x] Workspace normalization recognizes
      `agentflow_loulan_context_bundle_projection`.
- [x] Loulan bundle summary, protocol controls, next-pass status, inspector,
      and timeline display the selected artifacts.
- [x] Existing Loulan package/API/review static rendering still passes.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_memory_loulan_package_static.py tests\test_web_memory_loulan_human_review_static.py tests\test_web_memory_loulan_decision_context_static.py -q
```

## Remote Provider Policy

No remote provider is authorized in this task.
