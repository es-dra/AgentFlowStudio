# Scene Name Normalization Confirmation

Scene name normalization has two separate states:

- `scene_name_normalization_proposals` are non-authoritative analysis candidates.
- `merge_scene_name` is the explicit human confirmation command that records a
  variant scene name on the canonical `main_scene` asset.

The proposal path never mutates authoritative scene assets, never collapses
duplicate `main_scene` asset IDs, and never writes Production Graph state. A
human must call:

```text
POST /projects/{project_id}/core-assets/commands/confirm
command_type: merge_scene_name
target_asset_id: <canonical main_scene asset id>
patch.variant_asset_id: <variant main_scene asset id>
expected_asset_version: <canonical asset version>
```

`patch.alias` or `patch.variant_scene_name` can be used when the operator has a
surface name but not a variant asset ID. When `patch.variant_asset_id` is used,
the Runtime Service verifies that both assets belong to the same project and
script revision, both are active, and the variant is a different `main_scene`.

Concurrency follows the existing core asset command pattern:

- `expected_asset_version` guards the canonical scene asset.
- `idempotency_key` replays the same confirmed command receipt.
- Reusing an idempotency key with a different command is rejected.

After confirmation, the canonical scene keeps its original `name` and receives
the variant surface name in `aliases`. The variant scene asset is not retired by
this command; retiring or resolving duplicate assets remains a separate
explicit operation.
