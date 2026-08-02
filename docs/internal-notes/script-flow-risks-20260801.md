# Script Flow Risk Analysis — 2026-08-01

Local working note based on the script flow trace in
`docs/internal-notes/script-flow-trace-20260801.md`.

Scope: Script Core Truth → M6 script-plan → Production Graph → Runtime Store →
Studio projections, plus Director Compiler as a generation side path.

---

## 1) Duplicate / overlapping implementations

| Overlap | Where | Why it matters |
|---|---|---|
| **Multiple “script” models** | `agentflow_studio/schemas/script.py` (`ShortVideoScript`) vs Script Core Truth revisions vs M6 `script_revision` inside film candidate vs canvas `script` nodes / `script_plan` | Same domain concept, different shapes; no single authority |
| **Two planning paths into “shots”** | M6 script-plan → film candidate → `ProductionGraphStore` vs `runtime_storyboard_breakdown.py` → `build_storyboard_production_graph` | Parallel production graphs / shot models |
| **Two Director compilers** | `runtime_director_compiler.py` (v1) + `runtime_director_compiler_v2.py` (blocking) | Overlapping prompt-section compilers |
| **Dual UI entry for script truth** | `product-shell.js`, `agent-chat-lifecycle.js`, `embedded-creative-actions.js` all call `createScriptRevision` + `applyScriptCoreTruthProjection` | Same flow reimplemented in multiple Studio surfaces |
| **M6 invents its own revision id** | Deterministic planner sets `revision_id = m6-script-{digest}` while also carrying `source_revision_id` from Script Truth | Two revision identities in one candidate |

---

## 2) Oversized modules that should be split

| Module | ~LOC | Suggested split |
|---|---:|---|
| `apps/studio/src/product-shell.js` | ~5963 | shell / script actions / m6 / workspace |
| `apps/studio/src/agent-chat-lifecycle.js` | ~2691 | chat vs command dispatch vs projections |
| `apps/api/runtime_embedded_creative_actions.py` | ~2020 | per-action services |
| `apps/api/runtime_m6_script_plan_asset_bible.py` | ~1336 | routes / deterministic planner / validators / candidate builders |
| `apps/api/runtime_script_core_truth.py` | ~1234 | routes / persistence / analysis / asset commands |
| `apps/api/runtime_film_production_graph.py` | ~837 | compile vs HTTP vs projections vs media receipts |
| `apps/studio/src/runtime-client.js` | ~1055 | already a fat API surface; group by domain |

`runtime_production_graph.py` (~375) is comparatively clean as a kernel.

---

## 3) Intermediate data lacking a formal schema

| Data | Status today |
|---|---|
| Script Truth **persisted state** (`revisions`, `assets`, audit) | Hand-built `dict`s + string `schema_version`; request bodies are Pydantic, stored records are not a shared domain model |
| Analysis **`beats: list[dict]`** | Explicitly untyped in `StructuredAnalysisCandidateRequest` |
| M6 / film **candidate** | Validated by custom `validate_m6_candidate`, not a shared Pydantic/JSON Schema package used everywhere |
| Film graph **events / node metadata** | Generic kernel records; domain meaning lives in ad-hoc metadata |
| `agentflow_script_plan` from `runtime_script_plan.py` | Loose dict with `schema_version: "0.1.0"`, not the Script Truth / M6 contracts |
| Legacy `ShortVideoScript` | Exists but is **not** the Runtime script-truth authority |
| Studio projections | JS shaping into canvas nodes; contract is implicit |

---

## 4) Implicit / weakly versioned state

| State | Issue |
|---|---|
| **Studio canvas state** (`studio_state.json`) vs **Script Truth** vs **Production Graph** | Three stores; canvas can drift unless projections are reapplied |
| **“Current revision”** | Selected in Script Truth, but Studio also caches `script_core_truth_projection` locally |
| **M6 preview runs** | Async/recoverable via client request id; confirmation depends on digest + graph version — easy to desync if UI lags |
| **Analysis state** | Derived fields like `analysis_state` / asset status on revision — not a first-class versioned event log consumers share |
| **Director setup on nodes** | Lives in Studio node params; not part of Script Truth or Production Graph authority |
| **Authority flag** | `production_graph_authoritative` computed from “graph has nodes”, not an explicit lifecycle state machine |
| **Dual revision ids in M6** | Source Script Truth revision vs planner-generated `m6-script-*` id |

---

## 5) Model / LLM calls hard to test without the live system

| Call path | Why it’s coupled |
|---|---|
| **`runtime_m6_server_codex_planner.py`** → `build_m6_server_codex_script_plan_asset_bible` | Real provider registry dispatch when server Codex / `AFS_ALLOW_REMOTE_LLM` path is enabled; expects `provider_calls_started is True` |
| M6 preview route choosing remote vs deterministic planner | Behavior depends on server env / gate, not pure function of request body |
| Downstream media (image/video) after graph | Gated providers; not part of script structural path but often confused with it |

### Independently testable today

- Deterministic `build_m6_script_plan_asset_bible`
- `validate_m6_candidate`
- `compile_film_candidate` + `ProductionGraphStore` with `tmp_path`
- Script Truth create/select/analysis with TestClient + temp runtime root
- Director `compile_director_setup` (pure deterministic)

### Not independently testable without fakes/mocks

- Server Codex structured plan dispatch
- Any path that requires live provider registry + real LLM process

---

## Highest-leverage cleanup order

1. Pick **one script authority**: Script Core Truth revision (+ digest)
2. Make M6 candidate **only reference** that revision — stop inventing a second revision id
3. One formal schema for **Script → Scene → Beat → Shot → AssetRequirement** shared by Truth / M6 / Graph
4. Split M6 + Script Truth modules along routes / planner / validate / persist
5. Keep Codex planner behind a **fakeable port** so tests never need the live LLM

---

## Non-claims

- Local structural analysis from the current worktree only.
- Not provider QA, human acceptance, SaaS readiness, or live `/opt` deploy verification.
- Module line counts are approximate snapshots from 2026-08-01.
