# Provider Adapter v0.1 Contract

AFS keeps provider access behind local adapters. The adapter layer is a thin
runtime boundary, not an external gateway.

## Descriptor

Each `services.*` entry in provider config must include `descriptor`:

```json
{
  "schema_version": "provider_descriptor.v0.1",
  "modality": "image",
  "execution_mode": "sync",
  "reference_image_slots": 1,
  "supported_aspect_ratios": ["1:1", "4:3", "3:4", "16:9", "9:16"],
  "prompt_char_limit": 1500,
  "seed_supported": true,
  "cost_hint": "Live image generation cost depends on provider account configuration.",
  "required_gate": "AFS_ALLOW_REMOTE_IMAGE"
}
```

Runtime consumes two descriptor fields directly:

- `prompt_char_limit`: controls context budget and final provider prompt trimming.
- `reference_image_slots`: controls how many resolver reference images may reach
  the adapter.

MiniMax image is configured with one reference image slot. This is a service
capability, not a resolver architecture assumption.

## Lifecycle

All adapters implement:

```text
validate -> translate -> submit -> poll -> normalize
```

Sync providers return an already-complete task from `submit`, so `poll` is still
present but immediate. Async providers can use the same interface for submit/poll
separation.

`safe_error(error)` must redact or generalize provider config and credential
details before any error reaches Runtime artifacts.

## Runtime Dispatch

Runtime code must call:

```python
registry.dispatch(capability, service_id, request)
```

`apps/api/runtime_keyframes.py` must not import MiniMax smoke functions directly.
The old CLI command names may remain, but should call through the adapter/registry
when they become Runtime-facing.

## Gates

Descriptor `required_gate` is the capability gate for that service. Gate-open
checks are per capability. `AFS_ALLOW_REMOTE_IMAGE=true` never authorizes LLM,
ASR, video, downloads, or other network operations.

Gate-closed Runtime paths should not require local provider config and must not
start network calls.
