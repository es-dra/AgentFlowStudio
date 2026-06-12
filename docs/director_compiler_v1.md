# Director Compiler v1

Director Compiler v1 是 Studio 二维导演台的后端确定性编译器。前端只传结构化布置和资产 id；提示词语义在 Runtime 侧编译。

## 输入

`DirectorSetup2D` 支持：

- `activeCameraId`：本镜头真正生效的机位 id。
- `activeSubjectIds`：本镜头参与编译的主体 id 列表。
- `subjects[].visual_asset_id`：可选 fixed visual asset id。前端只能传 id，不能传 signature、feature_card、negative_locks。

如果没有 `activeCameraId`，compiler 默认取第一个机位并写 warning。如果 `activeSubjectIds` 为空，compiler 默认编译全部主体。

## 输出

`DirectorCompileResult v1` 包含：

- `sections[]`：中文摄影语言六段，覆盖主体调度、机位景别、光线、空间道具、运动连续、负面约束。
- `warnings[]`：确定性 warning，例如手选景别与几何/FOV 推断冲突。
- `active_camera_id`
- `active_subject_ids`
- `asset_refs_used[]`
- `trace_summary`

## 规则

- 相机和主体几何关系会被翻译成摄影语言，不能把坐标、FOV、色温数字原样念给模型。
- 相机距离和 FOV 会推断景别；与用户手选景别明显冲突时写 warning。
- 灯光位置、色温、柔硬、强度会被翻译成顺光/侧光/逆光、偏暖/偏冷、柔光/硬光等表达。
- 道具按主体相对方位描述为前景/背景/左右侧。
- 绑定资产时，signature 必须由后端按 visual asset id 从资产库读取；前端伪造的 signature 会被忽略。

## 前端边界

`directorPromptSummary` 只是 UI 摘要，可用于预览和面板标签，但不是权威提示词编译器。优化和生成请求的权威导演语义来自 Runtime Director Compiler。
