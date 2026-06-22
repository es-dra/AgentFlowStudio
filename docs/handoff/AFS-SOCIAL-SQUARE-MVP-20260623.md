# AFS 社交广场 MVP 交接 - 2026-06-23

## 范围

本分支完成社交广场第一版低冲突切片：

- 新增公开同源需求列表：`/community/requests`。
- 新增登录后发布需求、承接需求、提交成果、确认完成、关闭需求和举报事件。
- 社交广场数据写入 Runtime root 下的 `community/social_square/`。
- 首页新增“社交广场”模块，包含安全列表渲染和需求发布表单。

## 边界

- 未打开 provider gate。
- 未进行 provider 调用。
- 未写入生成媒体字节、signed URL、secret、本地私有路径、用户密码或 provider 原始响应。
- 公开响应不返回内部 `user_id`、邮箱或 session 信息。
- 本次证据是本地结构验证、Runtime 验证和浏览器烟测，不是 human acceptance，也不是 business validation。

## 变更文件

- `apps/api/runtime_social_square.py`
- `apps/api/runtime_auth_routes.py`
- `apps/api/runtime_service.py`
- `apps/site/index.html`
- `apps/site/social-square.js`
- `apps/site/styles/social-square.css`
- `tests/test_api_runtime_social_square.py`
- `tests/test_site_social_square_static.py`
- `tests/test_site_homepage_static.py`

## 验证

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_social_square.py tests\test_site_social_square_static.py tests\test_site_homepage_static.py -q
=> 9 passed, 1 existing Starlette/httpx warning

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_auth.py tests\test_api_runtime_service.py tests\test_api_runtime_social_square.py tests\test_site_homepage_static.py tests\test_site_social_square_static.py -q
=> 26 passed, 1 existing Starlette/httpx warning

npm run check:studio-js
=> JS syntax check passed: 111 files

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest -q
=> 605 passed, 520 deselected, 2 existing warnings

git diff --check
=> passed
```

浏览器烟测使用本地 Runtime `127.0.0.1:8891` 和临时 runtime root：

```text
/site/ => 200
/site/social-square.js => 200
/site/styles/social-square.css => 200
/community/requests => 200
DOM: #social-square present
DOM: form fields title, need_type, body, deliverable_hint present
Console warning/error count: 0
```

## 合并注意

- 主 checkout 当前仍有另一个线程占用 storyboard、context、asset-keyframe 相关文件。
- 本分支刻意不触碰这些文件。
- 后续合并时需要刷新 `origin/master`，再重跑 auth、site、Runtime 聚焦测试。
