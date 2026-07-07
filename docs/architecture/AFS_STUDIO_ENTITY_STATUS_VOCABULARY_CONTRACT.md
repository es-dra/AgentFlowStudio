# AFS Studio Entity/Status Vocabulary Contract

Status: current contract.
Scope: Studio entity, state, and action labels used by the Web canvas.
Version: `p0-20260704`.

This contract preserves the canonical IDs that Studio code and static tests use.
It is structure verification only. It does not prove Runtime readiness,
provider smoke, generated-media QA, human acceptance, business validation, or
CompanyOS/COS promotion.

## Entities

| ID | Canonical label | Chinese label |
|---|---|---|
| `project_asset` | Project Asset | 项目素材 |
| `reference_input` | Reference Input | 参考输入 |
| `generation_candidate` | Generation Candidate | 生成候选 |
| `keyframe_version` | Keyframe Version | 关键帧版本 |
| `video_revision` | Video Revision | 视频修订 |
| `binding` | Binding | 绑定 |
| `lineage` | Lineage | 来源链路 |

## Statuses

| ID | Chinese label |
|---|---|
| `draft` | 草稿 |
| `queued` | 排队中 |
| `submitted` | 已提交 |
| `running` | 生成中 |
| `succeeded` | 已完成 |
| `partial` | 部分完成 |
| `failed` | 失败 |
| `retryable` | 可重试 |
| `retrying` | 重试中 |
| `cancelled` | 已停止刷新 |
| `blocked` | 已阻断 |
| `needs_attention` | 需要检查 |
| `accepted` | 已采纳 |
| `rejected` | 已拒绝 |
| `fixed` | 已固定 |
| `retired` | 已停用 |
| `bound` | 已绑定 |
| `unbound` | 未绑定 |
| `replaced` | 已替换 |
| `available` | 可查看 |

Every `allowedStates` value in `STUDIO_ENTITY_VOCABULARY` must have a matching
entry in `STUDIO_STATUS_VOCABULARY`. UI aliases such as `complete`, `error`,
`partially_complete`, `cancelled_local_only`, `generating`, and `pending` must
resolve through `canonicalStudioStatusId()` before display.

## Actions

| ID | Chinese label | Applies to |
|---|---|---|
| `bind` | 绑定 | Project Asset, Reference Input, Generation Candidate, Keyframe Version, Video Revision |
| `unbind` | 取消绑定 | Binding |
| `replace` | 替换 | Project Asset, Reference Input, Keyframe Version, Video Revision, Binding, Lineage |
| `reference` | 用作参考 | Project Asset, Reference Input, Generation Candidate, Keyframe Version |
| `retry` | 重试 | Generation Candidate, Keyframe Version, Video Revision |
| `accept` | 采纳 | Generation Candidate, Keyframe Version, Video Revision |
| `reject` | 拒绝 | Generation Candidate, Keyframe Version, Video Revision |
| `view_lineage` | 查看来源链路 | Project Asset, Reference Input, Generation Candidate, Keyframe Version, Video Revision, Binding, Lineage |
| `view_evidence` | 查看证据 | Project Asset, Reference Input, Generation Candidate, Keyframe Version, Video Revision, Binding, Lineage |
| `continue_to_video` | 继续生成视频 | Keyframe Version |
| `edit_keyframe` | 编辑关键帧 | Keyframe Version |

## Non-Claims

The vocabulary and UI labels do not expose or prove provider raw response,
signed URLs, provider-side cancellation, generated-media QA, human acceptance,
business validation, durable memory, or CompanyOS/COS promotion.

`cancelled` means the local UI/runtime record stopped refreshing or was marked
cancelled locally. It does not prove provider-side cancellation.

`retry` means retry failed items only unless a task explicitly authorizes a
broader retry surface.
