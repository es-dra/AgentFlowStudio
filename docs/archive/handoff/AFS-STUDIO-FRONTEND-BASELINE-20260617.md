# AFS Studio 前端基线修复记录 - 2026-06-17

## 范围

本轮只处理 `/studio/` 前端卫生基线，不进入下一轮界面重构。

- 修复浏览器默认 `favicon.ico` 404 风险。
- 锁定 Studio HTML 的 UTF-8、中文标题、`zh-CN` 和 favicon 元数据。
- 增加常见乱码字符哨兵测试，防止中文用户文案回退成 mojibake。
- 做本地 Runtime-hosted `/studio/` 桌面端浏览器 smoke。

## 改动

- `apps/studio/index.html` 增加 SVG favicon 声明。
- `apps/studio/favicon.svg` 新增仓库内轻量图标。
- `apps/api/runtime_studio_static.py` 将根 `/favicon.ico` 重定向到 `/studio/favicon.svg`。
- `tests/test_web_studio_static.py` 增加 HTML 元数据和乱码哨兵测试。
- `tests/test_api_runtime_service.py` 增加 favicon 静态服务回归断言。

## 验证

- `pytest tests\test_web_studio_static.py tests\test_api_runtime_service.py -q`
  - 36 passed, 1 warning。
- `node --check apps/studio/src/main.js`
  - passed。
- `node --check apps/studio/src/runtime-client.js`
  - passed。
- `node --check apps/studio/src/panels/add-node-menu.js`
  - passed。
- `python tools\maintenance_audit.py`
  - failed=0，仍有既有 warning。
- `git diff --check`
  - exit 0，提示 `apps/studio/index.html` 后续会按 Git 行尾策略转 LF。
- 本地浏览器打开 `http://127.0.0.1:8790/studio/`
  - title 为 `AFS Studio 创作图谱`。
  - charset 为 `UTF-8`。
  - html lang 为 `zh-CN`。
  - console warning/error 为 0。
  - 添加节点菜单可打开。
  - `/favicon.ico` 返回 307 到 `/studio/favicon.svg`，目标返回 200。

浏览器截图证据保存在仓库外：

```text
C:\Users\chenzy\.codex\backups\AgentFlowStudio\frontend-baseline-20260617\local-studio-add-node-menu.png
```

## 边界

- 未调用 provider。
- 未修改线上服务器。
- 未做移动端适配。
- 未声明 human acceptance、business validation 或 durable memory promotion。

## 下一轮建议

下一轮可以进入 Studio Home / Project Hub 和空画布 workflow starter，但应作为独立前端功能波次处理，避免和本轮基线修复混在一起。
