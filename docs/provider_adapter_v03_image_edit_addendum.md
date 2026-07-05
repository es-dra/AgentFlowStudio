# Provider Adapter v0.3 Image Edit Addendum

This addendum extends `docs/provider_adapter_contract.md` for future image-edit
providers. It is descriptor metadata only. It does not add Runtime local-edit
routes, OpenAPI paths, Studio UI, provider config, provider calls, provider QA,
or readiness claims.

## Compatibility

Existing `provider_descriptor.v0.1` and `provider_descriptor.v0.2` descriptors
remain compatible. When `image_edit_capabilities` is absent, the registry must
default to blocked/no-support semantics:

- `supports_image_edit=false`
- `supports_true_local_edit=false`
- no supported local-edit scope kinds
- no fallback modes
- `local_edit_truth_label=blocked_no_supported_local_edit`

For v0.1 descriptors, `reference_image_slots`, `prompt_char_limit`,
`supported_aspect_ratios`, and `required_gate` remain active, but they do not
imply image-edit or true-local-edit capability.

Registry consumers can use `descriptor.image_edit_capabilities_present` to keep
the absent-field default separate from an explicit future descriptor.

## Field Shape

Future image descriptors may use:

```json
{
  "schema_version": "provider_descriptor.v0.3",
  "modality": "image",
  "capabilities": ["image"],
  "image_edit_capabilities": {
    "supports_image_edit": true,
    "supports_true_local_edit": false,
    "supports_mask_asset": true,
    "supports_bbox_region": false,
    "supports_polygon_region": false,
    "supports_semantic_region": true,
    "supports_preserve_locks": "prompt_only",
    "supports_negative_locks": "prompt_only",
    "fallback_modes": ["provider_full_frame_edit"],
    "max_mask_count": 1,
    "max_reference_images": 1,
    "input_fidelity_modes": ["low", "high"],
    "local_edit_truth_label": "provider_masked_edit"
  }
}
```

Supported scope kinds are derived from the explicit support flags:

```text
supports_mask_asset -> mask_asset
supports_bbox_region -> bbox
supports_polygon_region -> polygon
supports_semantic_region -> semantic_region
```

## Truth Labels

`supports_true_local_edit` is reserved for descriptors that explicitly support a
scoped edit operation. It requires at least one supported local-edit scope.

Allowed fallback labels are lower-truth vocabulary:

- `provider_full_frame_edit`
- `full_regeneration_fallback`
- `reference_image_to_image_fallback`

Those labels must not be reported as true local edit. `fallback_modes` cannot
contain `true_local_edit`.

`ProviderDispatchRequest.image_operation`, `edit_source_image_path`,
`edit_reference_image_paths`, and `image_input_fidelity` are adapter inputs.
They are insufficient by themselves to claim image-edit capability or local-edit
precision.

## Non-Claims

This addendum does not claim:

- any current provider supports true local edit;
- full-frame/reference/image-to-image fallback is true local edit;
- provider QA, generated-media QA, human acceptance, or business readiness;
- Runtime route/OpenAPI/UI support for local-edit submission.
