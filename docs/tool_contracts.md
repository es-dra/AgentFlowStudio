# 工具契约索引

本文件只保留工具契约入口，不再逐项复制工具条目。

当前单一事实来源：

```text
configs/tool_catalog.yaml
configs/tool_catalog/*.yaml
```

`configs/tool_catalog.yaml` 是索引文件，实际工具条目拆在
`configs/tool_catalog/` 分片中。代码通过
`agentflow_studio.workflow_engine.tool_catalog.load_tool_catalog_contract`
读取完整 catalog。

## 当前边界

- 这是静态工具契约，不是 runtime registry。
- 不新增 agent execution。
- 不自动打开 provider。
- 不保存 secret、signed URL、私有素材字节或生成媒体。
- 工具条目的输入、输出、失败模式、质量检查和权限约束以 YAML 为准。

## 验证

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_tool_catalog.py -q
```
