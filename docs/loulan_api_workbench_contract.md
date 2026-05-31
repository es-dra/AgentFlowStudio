# Loulan API Workbench Contract

`agentflow_loulan_api_workbench_plan` is the dry-run bridge between a Loulan
memory package, an optional explicit context bundle projection, and a future
image provider adapter.

Required boundaries:

- input is an explicit `agentflow_loulan_memory_package`;
- optional `--context-projection` input must be an
  `agentflow_loulan_context_bundle_projection`;
- if a context projection is provided, reference packs use only its ready or
  partial-ready human-approved `context_bundle.memory_refs`;
- if a context projection is blocked, request preview remains blocked and the
  workbench must not fall back to package-level eligible refs;
- output is request preview only and must keep `dry_run_only: true`;
- no provider call, download, generated media write, or Company memory write is
  performed;
- reference packs use approved memory refs and sha256 values, not absolute local
  paths;
- request manifests contain runtime placeholders, not credentials, bearer
  headers, signed URLs, or provider response URLs;
- response ledgers start as `not_submitted`;
- QA and promotion gates stay blocked until provider response, human review, and
  explicit promotion decision evidence exist.

Committed example:

```text
examples/agentflow/loulan_api_workbench_plan.example.json
```
