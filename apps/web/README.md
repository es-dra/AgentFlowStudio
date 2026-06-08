# AFS 过渡 Web 工作台

`apps/web` 只保留本地 read-only / local-only artifact 查看能力。

它不是最终前端产品，也不负责后端执行。后续外部画布工作台应对接 Runtime
Service，而不是读取 CLI 内部实现或旧 Web bridge。

## 打开方式

直接打开：

```text
apps/web/index.html
```

当前 Web 工作台不需要本地 server，不启动 provider，不写文件，不持久化浏览器状态。

## 当前职责

- 读取用户显式选择的本地 artifact。
- 展示 Project Manifest、run package、asset review、context projection、consistency review 等安全摘要。
- 展示 local video preview，但只使用用户显式选择的本地媒体文件。
- 辅助人工复制 feedback event copy JSON 文本。
- 对未知 JSON 显示 `unknown_json`，对不支持文件显示 `unsupported_file`。
- 展示 `schema_version`、状态 `warning` 和边界提示。

## 非职责

机器关键词保留给静态测试和后续前端对接：

- no upload
- no backend execution
- no persistence
- no provider config
- no workflow execution
- does not scan directories
- terminal mojibake
- source files are utf-8
- default Chinese
- in-memory

人工边界：

- 不执行 workflow。
- 不启动 Runtime Service。
- 不调用 provider。
- 不扫描目录。
- 不读取 secret、signed URL、provider config 或私有素材字节。
- 不保存 durable memory。
- 不声明 human acceptance 或 business validation。

## 里程碑标签

以下标签仅作为历史兼容测试锚点，不代表恢复旧执行面：

- m1.2.1
- m1.3
- m1.5
- m2

## 后续方向

该目录是过渡工具。正式前端工作台由外部画布类应用接管后，本目录应继续瘦身或删除。
