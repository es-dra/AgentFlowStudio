# Creative Intent Control Agent — Working Mode Baseline

Date: 2026-07-29  
Branch: `codex/agent-working-mode-20260729`  
Scope: provider-free Runtime verification only.

## Baseline test result

Focused suite (worktree, gates closed by default):

```text
tests/test_api_runtime_creative_agent_keyframes.py
tests/test_api_runtime_prompt_memory_loop.py
tests/test_api_runtime_prompt_node_contract.py
tests/test_api_runtime_prompt_memory_candidates.py
tests/test_api_runtime_context_resolver.py
tests/test_model_call_context_contract.py
tests/test_creative_runtime_contract.py
```

Result: **104 passed**.

## Working mode as implemented

```text
node prompt
  -> slots + professional rules + background context
  -> hard / strong / soft constraints
  -> three candidates
  -> weighted primary-axis scores + generation_target bias
  -> hard-control vetoes
  -> selected canonical prompt + provider translation + safe trace
```

| Piece | Value |
|---|---|
| Agent | `creative_intent_control_agent_v1` |
| Mode | `layered_single_agent` |
| Candidates | `continuity_safe`, `expressive_cinematic`, `provider_safe_keyframe` |
| Score dims | 8 heuristic dimensions |
| Selection | weighted primary axes + target bias + hard-control veto |
| Default provider | closed (`provider_calls_started=false`) |

## Case matrix (verified)

1. `generation_target=script` prefers continuity-safe candidate under current scores.
2. `generation_target=keyframe` prefers provider-safe keyframe under current scores + image bias.
3. Node parameters land in hard constraints; user preference stays soft / lower precedence.
4. Keyframe route with `AFS_ALLOW_REMOTE_IMAGE` unset returns blocked safe manifest and starts no network call.
5. Trace includes constraint layers, candidates, scores, selected candidate, and provider translation.

## Guarantees

- Deterministic candidate set and safe trace for prompt optimization.
- Hard node parameters are recorded as hard constraints and injected into candidate prompts.
- Soft user preferences do not outrank hard/strong layers in the precedence list.
- Keyframe generation does not call providers when the image gate is closed.

## Non-claims

- Not provider smoke or generated-media QA.
- Not human creative acceptance or business validation.
- Not SaaS / public-edge readiness.
- Not Domain Crew multi-agent content generation.
- Not a claim that scores are learned model outputs; they remain deterministic heuristics.
