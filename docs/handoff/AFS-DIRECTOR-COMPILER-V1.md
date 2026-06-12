# AFS-DIRECTOR-COMPILER-V1 交接

分支：`codex/afs-director-compiler-v1`

## 范围

- 新增后端确定性 Director Compiler v1。
- 扩展 `DirectorSetup2D`：`activeCameraId`、`activeSubjectIds`、主体 `visual_asset_id`。
- 用户版提示词的导演台部分改为消费 compiler 输出。
- resolver 接入 compiler，生成伴随包的 scene/director 段会包含编译后的导演台语义。
- 更新 Studio 导演台面板：
  - 默认布置不再携带卧室道具/遮光旗模板；
  - 空列表保持空，不再回填默认对象；
  - 对象列表可添加缺失对象；
  - 生效机位/生效主体显式设置；
  - 主体可绑定 visual asset id；
  - “生成提示词片段”改为确认后追加，不覆盖原 prompt。

## 验证

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_web_studio_static.py tests/test_runtime_director_compiler.py tests/test_api_runtime_director_setup_prompt.py tests/test_api_runtime_context_resolver.py
node --check apps/studio/src/director-data.js
node --check apps/studio/src/panels/director-shell.js
node --check apps/studio/src/panels/director-fields.js
```

结果：

- Runtime/Web 聚焦集：24 passed。
- 变更过的导演台 JS 语法检查：passed。

## 边界

- 前端预览只是 UI 摘要，Runtime compiler 才是权威语义来源。
- 未打开真实 provider gate。
- 本切片做的是静态/Runtime 验证；后续仍建议补一次浏览器交互 QA。
