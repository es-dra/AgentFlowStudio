# AFS Landing Prep: Content Memory Web Workbench 001

Date: 2026-06-09

Owner roles:

- AI-Native Operating Architect
- Product / Engineering Orchestrator
- Runtime/API Integrator
- Frontend Contract Steward
- Evidence Reviewer

Status: planning and runtime evidence handoff. No UI implementation in this slice.

## Scope

This slice prepares the next AFS landing step:

```text
Runtime Service / Project Manifest
  -> deterministic content-production memory loop
  -> safe artifacts / trace / feedback
  -> context projection / two-round validation
  -> Web workbench plan
```

Pure slicing is intentionally out of scope for this step. It remains a fixed
supporting workflow and should not drive the next Web UI design.

## COS / Workflow Mapping

This task exercises the Harness-first Agentic Delivery System candidate rule.

ETCLOVG coverage:

| Layer | Current evidence |
|---|---|
| E - Execution | Runtime Service TestClient run under ignored `data/processed/runs/landing_prep_001_runtime_service_20260609`. |
| T - Tooling | Runtime Service endpoints and frontend request fixtures. |
| C - Context | Production Memory profile version, context projection, two-round runtime report. |
| L - Lifecycle | Project manifest status, job ids, Round 1 to Round 2 handoff. |
| O - Observability | `agentflow_run_trace` artifacts and job summaries. |
| V - Verification | Runtime/API focused tests passed: `8 passed, 1 warning`; CLI smoke, maintenance audit, and `git diff --check` passed. |
| G - Governance | Provider calls remain blocked by default; no durable memory or Company KB write. |

Agent output can become candidate feedback for COS, but it must not promote any
Company OS rule or durable memory without human review.

## External UI References

Reference links reviewed:

- LibTV: `https://libtv.gongke.net/`
- RHTV project surface: `https://rhtv.runninghub.cn/projects`
- RHTV deep dive: `https://ai-bot.cn/rhtv-deep-dive/`
- Mango Lingchuang: `https://aigc.mgtv.com/`
- Mango developer docs: `https://aigc.mgtv.com/develop/docs`

Mechanisms to borrow:

| Reference | Useful mechanism | AFS adaptation |
|---|---|---|
| LibTV | Infinite canvas and node workflow for script, storyboard, image, video, audio, and Agent Skill entry. | Use canvas nodes for AFS artifacts and actions, not raw local media paths. |
| RHTV | Agent lives inside the canvas, proposes a plan, waits for confirmation, then creates visible nodes. | Use an assistant/action rail that proposes backend actions, but every action maps to Runtime Service and explicit gate state. |
| RHTV | Transparent node tree reduces black-box generation and allows intervention at each step. | Show Run Trace, blockers, included refs, rejected refs, and non-claims per node. |
| Mango Lingchuang | Film-production project flow, AI canvas, controllable pose/camera/composition, API exposure. | Keep the product language production-grade: project, shot/content evidence, review, context reuse, provider gate, API contract. |

Mechanisms not to copy now:

- SaaS account system.
- Multi-user collaboration.
- Browser-side workflow execution.
- Direct provider execution from UI.
- Marketplace/model gallery as the main screen.
- Decorative showcase homepage before the operator workbench exists.

## AFS Differentiation

AFS should feel familiar to users of current AI canvas tools. The first-layer
experience should be a creator canvas, not an engineering observability screen.

User-facing differentiation:

- The user starts from familiar objects: project, source assets, script /
  storyboard, scene cards, generation actions, preview, feedback, and revision.
- The canvas should feel like a creative production space. It should not force
  users to learn `job_id`, `artifact_id`, promotion ledgers, Context Runtime, or
  memory terminology before they can operate it.
- AFS advantages appear as low-friction product affordances:
  - remembered project style and preferences;
  - fewer repeated setup prompts;
  - clear reusable project profile;
  - visible revision history;
  - safer provider preflight;
  - explainable “why this changed” when the user asks.

Internal differentiation:

- Behind each user-facing card, the backend still keeps verifiable evidence:
  `job_id`, `artifact_id`, blockers, trace, claim boundaries, context refs, and
  provider gate state.
- Feedback remains raw evidence until explicitly reviewed.
- Candidate memory, promotion decision, profile version, durable memory, human
  acceptance, and business validation stay separated in the data model.
- Context Runtime should be available through an advanced “why / evidence”
  drawer, not exposed as the default mental model.
- The Web surface stays low-maintenance by treating Runtime Service as the only
  backend contract.

## Industrial Frontend Product Architecture

AFS Web should be planned as a small but complete production frontend, not only
as a canvas page. The canvas is the primary creation surface, but the product
needs surrounding workspaces so a real user can start, manage, review, reuse,
and export work without falling back to file-system archaeology.

Recommended top-level surfaces:

| Surface | User-facing purpose | Backend contract |
|---|---|---|
| Project Hub | Create/open/import projects, see recent work and status. | `/projects`, project import/export, project summaries. |
| Project Setup | Collect goal, target platform, source assets, references, style direction, provider readiness. | Project manifest, source asset metadata, provider validation plan. |
| Asset Library | Manage reference images, character/style references, script/brief inputs, accepted results. | Safe artifact refs and source asset summaries; no private path exposure. |
| Creation Canvas | Familiar node/card canvas for script, storyboard, scene cards, generation results, variants, and revisions. | Workbench state adapter, jobs, safe artifact payloads. |
| Scene / Shot Inspector | Edit prompt, reference, style, generation settings, feedback, retry instruction for the selected card. | User-facing card model mapped to Runtime Service actions. |
| Review Room | Compare variants, mark keep/revise/reject, add comments, prepare next round. | `/feedback`, review artifacts, accepted/rejected status. |
| Project Memory / Style Profile | Show remembered style, character/profile rules, reusable preferences, and revision history in product language. | Profile version refs, context projection, promotion decision refs hidden behind friendly labels. |
| Generation Queue | Show running/blocked/succeeded jobs and provider preflight status. | Job progress, provider safe manifest, blocker model. |
| Export / Package | Prepare selected outputs and reports for downstream use. | Future export/package endpoints; not required for first Web slice. |
| Advanced Diagnostics | Optional drawer for trace, artifact ids, blocked refs, non-claims, and claim boundaries. | Run trace, artifact refs, quality reports, maintenance/evidence artifacts. |

Primary navigation should not expose internal architecture terms. Suggested
navigation labels:

```text
Projects
Create
Assets
Review
Style Memory
Jobs
Settings
```

Advanced/internal labels such as `Context Runtime`, `Promotion Decision`,
`Artifact Ledger`, and `Run Trace` should only appear in detail views,
developer mode, or evidence export.

## User Mental Model

The user should feel this flow:

```text
Open project
  -> add script / brief / references
  -> organize scenes on canvas
  -> generate or inspect candidates
  -> compare variants
  -> keep / revise / reject
  -> next round remembers the useful parts
```

The backend still runs the AFS chain:

```text
Project Manifest
  -> Runtime Service job
  -> safe artifact
  -> raw feedback
  -> candidate/profile update
  -> context projection
  -> next-round validation
```

But the primary UI should translate that chain into creation language:

| Internal object | User-facing label |
|---|---|
| Project Manifest | Project |
| Asset profile seed | Style / character reference |
| Asset test run | First generation check |
| Feedback event | Review note |
| Candidate update | Suggested style update |
| Promotion decision | Apply to project style |
| Profile version | Project style memory |
| Context projection | Used in next round |
| Run trace | Technical details |
| Blocked refs | Needs attention |

## Information Architecture

Default desktop layout:

```text
Global app shell
  left nav: Projects / Create / Assets / Review / Style Memory / Jobs / Settings

Project workspace
  top bar: project, target platform, provider readiness, primary action
  left rail: assets, references, script, scene list, project style
  center: creation canvas
  right panel: selected card inspector
  bottom strip: variants, accepted items, rejected items, comments
  optional drawer: evidence and diagnostics
```

Responsive priorities:

- Desktop: canvas, inspector, and filmstrip visible together.
- Tablet: canvas plus collapsible inspector.
- Mobile: project list, scene cards, review actions, and status; full canvas can
  be reduced or postponed.

## Feature Modules

First implementation should keep modules small and explicit:

| Module | Responsibility |
|---|---|
| `runtime-client` | Typed calls to Runtime Service. |
| `workbench-state` | Converts API payloads into user-facing project/canvas state. |
| `project-hub` | Project list, create/import/export shell. |
| `asset-library` | Safe asset/ref cards and artifact summaries. |
| `creation-canvas` | Scene/card canvas, connections, layout, selection. |
| `scene-inspector` | Prompt/reference/style/retry controls for selected card. |
| `review-room` | Keep/revise/reject/comment flow. |
| `style-memory` | Friendly view over profile versions and context reuse. |
| `job-center` | Job progress, provider preflight, blockers. |
| `evidence-drawer` | Advanced trace/artifact/non-claim inspection. |

The first Web slice should not create a large monolithic `App.tsx` equivalent.
Canvas render, API adapter, artifact renderers, status mapping, and forms should
stay separate from the beginning.

## Runtime Chain Evidence

The current deterministic chain was run through the Runtime Service app with
the frontend request fixtures.

Runtime root:

```text
data/processed/runs/landing_prep_001_runtime_service_20260609
```

Generated runtime artifacts are ignored and must not be committed.

Observed result:

| Step | Result |
|---|---|
| `/health` | `ready`, service version `0.2.0`, provider calls blocked by default. |
| `/capabilities` | 11 actions exposed. |
| `/projects` | Project manifest created and later reached `ready_for_next_round`. |
| `/runs/asset-test` | Job status `blocked`; report status `completed_with_blocks`. This is expected because real project materials were not supplied. |
| Round 1 blocker | `project_materials_missing`. |
| Round 1 artifacts | test package, feedback event, profile version, context projection, consistency review, real asset test report, review-screen selected files, run trace. |
| `/feedback` | Raw runtime feedback recorded; `feedback_is_memory=false`; no long-term memory write. |
| `/runs/two-round-validate` | Job status `succeeded`; `runtime_verification_status=verified`; `improvement_assessment=no_clear_improvement`. |
| Round 2 context | 1 included profile v2 ref; 1 blocked superseded profile v1 ref. |
| `/provider/validation-plan` | Job status `blocked`; no provider calls started. |
| Provider blockers | `image_gate_unset`, `video_gate_unset`, `provider_config_missing`, `character_reference_image_missing`. |

Claim boundaries:

- This is runtime verification, not human acceptance.
- This is not business validation.
- This is not durable memory.
- This does not write Company KB.
- This does not prove provider success.

## Backend Cooperation Needed

The existing backend is sufficient for planning and deterministic proof, but a
usable industrial frontend needs a small backend adapter layer before large UI
work starts.

Backend deliverables for the next slice:

1. `GET /projects/{project_id}/workbench-state`
   - Returns one UI-oriented state object for the current project.
   - Includes project summary, source asset cards, scene/content cards, job
     summaries, provider readiness, current blockers, next suggested actions,
     and advanced evidence refs.

2. Normalized canvas card model

```json
{
  "card_id": "scene-001",
  "kind": "scene",
  "title": "Opening scene",
  "status": "needs_review",
  "summary": "Lead character enters the archive room.",
  "thumbnail_artifact_id": null,
  "primary_artifact_id": "...",
  "actions": ["generate", "revise", "mark_keep"],
  "evidence": {
    "job_id": "...",
    "artifact_ids": ["..."],
    "has_advanced_details": true
  }
}
```

3. Normalized blocker model

```json
{
  "blocker_id": "project_materials_missing",
  "severity": "blocked",
  "message": "Add project materials before provider validation.",
  "user_action": "add_project_materials",
  "source": "provider_preflight"
}
```

4. Stable action vocabulary

```text
create_project
import_project
add_reference
start_first_generation_check
record_review_note
apply_to_project_style
start_next_round
run_provider_preflight
open_advanced_details
```

5. Job progress and event history
   - The frontend should not poll many unrelated artifacts to understand what
     happened.
   - A project event list should expose user-facing history:
     generated, reviewed, style updated, next round prepared, provider blocked.

6. Safe preview policy
   - First slice can render JSON/text summaries and placeholder thumbnails.
   - Real media previews require explicit safe artifact preview endpoints later.
   - Browser must not read raw local media paths.

7. Frontend adapter package
   - OpenAPI is available now.
   - A typed client or adapter should wrap API calls into UI domain objects:
     `WorkbenchProject`, `CanvasCard`, `AssetCard`, `ReviewItem`,
     `StyleMemoryItem`, `JobEvent`, and `ProviderGateState`.

Not needed before first Web slice:

- Live provider execution endpoint.
- Database persistence.
- Account system.
- Cloud sync.
- Durable Memory / COS promotion endpoint.

## Web UI Development Plan

The first screen must be the actual creator workbench. It should match the
mental model of existing canvas tools while keeping AFS evidence controls behind
the surface.

Recommended default layout:

```text
Top command bar
  project switcher / main generate action / provider readiness / export

Left creation rail
  project assets / references / script or brief / style profile / history

Center canvas
  source assets -> script / storyboard -> scene cards -> generation results
  -> selected revision -> next scene / next round

Right inspector
  selected card controls / prompt / reference / style / feedback / retry

Bottom filmstrip
  generated variants / accepted shots / rejected shots / comments

Advanced evidence drawer
  hidden by default; shows job id / artifact id / trace / included refs /
  blocked refs / non-claims only when debugging or reviewing
```

Core interaction:

1. Open or create a project.
2. Add source assets, references, script, or brief.
3. Let the system create canvas cards for scenes / shots / content units.
4. Generate or inspect a first round.
5. Mark outputs as keep, revise, reject, or use as reference.
6. The backend records raw feedback and prepares profile/context reuse.
7. Start the next round from the visible project state, not from a technical
   two-round-validation concept.
8. Provider validation remains a visible preflight state, not a hidden remote
   call.

Visual direction:

- Creative production canvas with professional control depth.
- Low learning cost for users of LibTV / RHTV / Mango-style tools.
- Canvas first, inspector second, evidence drawer optional.
- Clear status color semantics:
  - succeeded: stable green
  - blocked: amber
  - failed: red
  - needs review: blue
  - not started: neutral
- Avoid one-note dark blue/purple AI dashboards.
- Use visual scene cards, asset thumbnails, prompt chips, and compact action
  buttons.
- Do not put internal architecture terms on primary cards unless the user opens
  advanced details.

## Implementation Milestones

### M0 - Flow Run Ready

Status: current slice evidence exists.

Deliverables:

- Runtime chain smoke result.
- Backend/UI gap list.
- Web workbench plan.

### M1 - Backend Workbench State Adapter

Deliverables:

- `GET /projects/{project_id}/workbench-state`.
- Normalized user-facing canvas state plus advanced evidence refs.
- Normalized blocker and node status model.
- Normalized project event/history model.
- Safe preview policy placeholder.
- Tests for safe refs and non-claims.

### M2 - Frontend Foundation

Deliverables:

- New lightweight Web application surface.
- Runtime client and state adapter.
- App shell with top navigation, project hub, and project workspace layout.
- Empty/loading/error/blocked states.
- No provider execution and no browser-side workflow execution.

### M3 - Project Hub and Setup

Deliverables:

- Project list, create, import, export shell.
- Project goal, target platform, reference/style setup.
- Asset/reference entry using safe summaries only.
- Provider readiness shown as preflight state.

### M4 - Creation Workspace

Deliverables:

- Creation rail, canvas, scene/content cards, inspector, and filmstrip.
- First generation check action mapped to Runtime Service.
- Visual status states: needs assets, ready, generating, needs review, blocked.
- Internal `job_id` and `artifact_id` stay behind advanced details.

### M5 - Review and Style Memory UX

Deliverables:

- Keep/revise/reject/comment review flow.
- Raw feedback submission through `/feedback`.
- Friendly Project Style Memory view over profile/context artifacts.
- Next-round action from visible project state.

### M6 - Advanced Evidence and Diagnostics

Deliverables:

- Artifact-specific panels for real asset test report, context projection,
  two-round report, runtime feedback, provider safe manifest, and run trace.
- Explicit claim-boundary labels.
- Run trace and blocker drilldown.
- These panels are advanced/detail views, not the default primary experience.

### M7 - Provider-Gated Real Model Smoke

Deliverables:

- Only after deterministic Web flow is stable.
- Explicit capability gate for image/video/LLM as needed.
- Safe preview/metadata handling.
- Quality report separates provider smoke from human acceptance and business
  validation.

### M8 - Browser QA and Release Gate

Deliverables:

- Runtime Service smoke.
- Browser screenshot checks for desktop and mobile widths.
- Focused frontend tests.
- Runtime/API focused pytest.
- `maintenance_audit`.
- `git diff --check`.

## Acceptance Criteria Before UI Implementation Starts

- The deterministic content-production memory chain can be run from Runtime
  Service without provider calls.
- The Web team has a single graph/state contract to consume.
- Blocked states are first-class and do not look like crashes.
- The primary UI has no extra learning cost compared with current canvas tools.
- AFS-specific evidence and memory advantages appear through smoother reuse,
  safer runs, and optional explainability, not through default technical
  terminology.
- Pure slicing is not pulled into the next development slice.

## Verification Run

Executed after this handoff was written:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_service.py -q
.\.venv\Scripts\python.exe -m apps.cli.main --help
.\.venv\Scripts\python.exe -m apps.cli.main version
.\.venv\Scripts\python.exe tools\maintenance_audit.py
git diff --check
```

Results:

- Runtime/API focused tests: `8 passed, 1 warning`.
- CLI version: `0.1.0`.
- Maintenance audit: `failed=0`, `passed=6`, `warning=0`.
- `git diff --check`: passed; PowerShell reported line-ending conversion
  warnings for modified Markdown files only.
