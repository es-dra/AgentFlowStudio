# Loulan API Workbench Contract

`agentflow_loulan_api_workbench_plan` is the dry-run bridge between a Loulan
memory package and a future image provider adapter.

Required boundaries:

- input is an explicit `agentflow_loulan_memory_package`;
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
