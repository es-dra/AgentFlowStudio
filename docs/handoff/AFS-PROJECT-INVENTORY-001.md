# AFS-PROJECT-INVENTORY-001

分支：`codex/afs-project-inventory-001`

日期：2026-06-12

## 摘要

本切片完成第一阶段项目全量盘点与低风险删减。新增可复跑工具：

```powershell
.\.venv\Scripts\python.exe tools\project_inventory.py --root . --output-dir data\reports\project_inventory\<run-id> --report-doc docs\maintenance\AFS-PROJECT-INVENTORY-20260612.md --execute-cleanup
```

工具区分 tracked 产品代码、ignored 本地产物、未忽略 untracked 文件，并将本地配置、模型权重、原始素材和媒体证据列为 report-only。

## 结果

- Tracked baseline：774 文件，86,068 行。
- Ignored baseline：约 3.43GB，主要为 `data/`、`.venv/`、历史媒体证据和本地模型。
- 低风险清理：累计删除 14,452 个缓存目标，约 30.24MB。
- 直接删减：删除 `agentflow_studio/asset_manager/__init__.py` tracked 空壳；删除 6 份旧 `AFS-PRODUCTION-MEMORY-ASSET-*` handoff；production-memory CLI 短别名不再进入默认 help，只保留 hidden compatibility 长命令。
- 本地深度核对：12,791 个本地文件、约 3.46GB；755 个项目文本文件、86,993 行做过逐行级统计；发现 80 组 exact duplicate，本地重复媒体证据理论可回收约 827MB，但需先定 canonical evidence retention。
- Protected confirmed：`configs/providers.local.json`、`configs/models.yaml`、`data/models/faster-whisper`、`data/raw/demo_zombie/input.mp4` 仍存在。
- 剩余阻塞：`data/processed/pytest-basetemp` 有历史目录拒绝当前用户 ACL / 删除，需拥有者或管理员权限清理。

## 产物

- 人读报告：`docs/maintenance/AFS-PROJECT-INVENTORY-20260612.md`
- 深度本地核对：`docs/maintenance/AFS-DEEP-LOCAL-REVIEW-20260612.md`
- 机器报告：`data/reports/project_inventory/20260612-cleanup-final/`
- 工具：`tools/project_inventory.py`、`tools/project_inventory_core.py`
- 测试：`tests/test_project_inventory_cleanup.py`

## 验证

- `tests/test_project_inventory_cleanup.py`: 3 passed
- `tests/test_cli_command_registry_boundaries.py`: pending after visible production-memory CLI removal

后续仍需跑完整维护验证：

```powershell
.\.venv\Scripts\python.exe tools\maintenance_audit.py
.\.venv\Scripts\python.exe -m pytest tests/test_project_inventory_cleanup.py tests/test_provider_adapter_registry.py tests/test_api_runtime_context_resolver.py -q
git diff --check
```

## 边界

- 未打开任何 provider gate。
- 未删除本地 provider config、模型权重、原始素材或唯一媒体证据。
- 本报告不是 human acceptance、business validation 或 durable-memory promotion。
