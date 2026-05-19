# Platform Profile Contract

Platform profiles describe lightweight distribution preferences for a target
platform. They help agents choose candidate settings and package review
criteria without hard-coding platform assumptions into workflow nodes.

NarratoCut `v0.1.0` ships example profiles only. Product workflows do not yet
load these profiles automatically.

## Required Fields

- `schema_version`: contract version, currently `"0.1"`.
- `platform_id`: stable lowercase id.
- `display_name`: human-facing platform name.
- `aspect_ratio`: expected output ratio, for example `"9:16"`.
- `recommended_duration_sec`: `min`, `target`, and `max` duration values.
- `opening_style`: target hook timing and preferred content signals.
- `subtitle_density`: recommended subtitle style and line length.
- `packaging`: basic cover/BGM expectations.

## Examples

Committed examples:

- [`../configs/platform_profiles/douyin.yaml`](../configs/platform_profiles/douyin.yaml)
- [`../configs/platform_profiles/xiaohongshu.yaml`](../configs/platform_profiles/xiaohongshu.yaml)
- [`../configs/platform_profiles/youtube_shorts.yaml`](../configs/platform_profiles/youtube_shorts.yaml)

## Agent Notes

Use platform profiles as advisory defaults. Do not treat them as publishing
rules or compliance checks. If user preferences conflict with a profile, record
the override in `project_manifest.json` or future feedback events.
