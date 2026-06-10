from __future__ import annotations

from pathlib import Path


WORKBENCH_ROOT = Path("apps/workbench")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_director_add_node_flow_replicates_libtv_workspace_controls() -> None:
    flow = _read(WORKBENCH_ROOT / "src" / "render-studio-add-node-flow.js")
    css = _read(WORKBENCH_ROOT / "styles-studio-director-merge-flow.css")

    for marker in [
        "renderDirectorFlow",
        "libtv-director-flow",
        "libtv-director-canvas",
        "libtv-director-toolbar",
        "libtv-director-object-list",
        "libtv-director-camera-panel",
        "3D导演台",
        "导演视角",
        "机位视角",
        "场景",
        "搜索场景对象",
        "机位1",
        "角色A",
        "重置视角",
        "摄像机",
        "属性",
        "摄像机截图",
        "FOV 50°",
        "位置 X Y Z",
        "注视目标",
        "手动坐标",
        "视野角度 (FOV)",
        "控制镜头视野范围。数值越小，画面越近、越聚焦；数值越大，画面越广、能看到更多环境。",
        "移动 (V)",
        "添加角色",
        "全景图",
        "添加机位",
        "选择画幅比例",
        "截图",
        "AI 识图导入",
        "全屏",
        "导演台未启动",
    ]:
        assert marker in flow

    for marker in [
        ".libtv-director-flow",
        ".libtv-director-canvas",
        ".libtv-director-stage",
        ".libtv-director-grid",
        ".libtv-director-toolbar",
        ".libtv-director-object-list",
        ".libtv-director-camera-panel",
        ".libtv-director-action-row",
    ]:
        assert marker in css


def test_video_merge_add_node_flow_exposes_safe_timeline_controls() -> None:
    flow = _read(WORKBENCH_ROOT / "src" / "render-studio-add-node-flow.js")
    css = _read(WORKBENCH_ROOT / "styles-studio-director-merge-flow.css")

    for marker in [
        "renderVideoMergeFlow",
        "libtv-video-merge-flow",
        "libtv-video-merge-preview",
        "libtv-video-merge-timeline",
        "libtv-video-merge-control",
        "多个视频片段合为一个",
        "片段 01",
        "片段 02",
        "片段 03",
        "片段排序",
        "转场",
        "节奏",
        "统一画幅",
        "生成历史素材仅以安全引用进入时间线。",
        "视频合成未启动",
    ]:
        assert marker in flow

    for marker in [
        ".libtv-video-merge-flow",
        ".libtv-video-merge-preview",
        ".libtv-video-merge-timeline",
        ".libtv-video-merge-clip",
        ".libtv-video-merge-control",
    ]:
        assert marker in css


def test_image_add_node_flow_matches_libtv_image_controls_without_uploading() -> None:
    flow = _read(WORKBENCH_ROOT / "src" / "render-studio-add-node-flow.js")
    css = _read(WORKBENCH_ROOT / "styles-studio-add-node-flow.css")

    for marker in [
        "renderImageNodeFlow",
        "libtv-image-node-flow",
        "libtv-image-node-card",
        "libtv-image-upload-pill",
        "libtv-image-node-preview",
        "libtv-image-control-card",
        "libtv-image-tool-row",
        "libtv-image-param-grid",
        "图片节点",
        "上传",
        "尝试：",
        "图生图",
        "图片高清",
        "风格",
        "标记",
        "可直接文字生图，或上传图片输入文字指令对图片进行编辑，如：将背景改为雪夜",
        "Lib Image",
        "自适应 · 标准画质 · 2K",
        "摄像机",
        "全景",
        "1张",
        "18",
        "图片生成未启动",
        "上传入口只登记安全摘要，不读取本地文件字节。",
    ]:
        assert marker in flow

    for marker in [
        ".libtv-image-node-flow",
        ".libtv-image-node-card",
        ".libtv-image-upload-pill",
        ".libtv-image-node-preview",
        ".libtv-image-control-card",
        ".libtv-image-tool-row",
        ".libtv-image-param-grid",
    ]:
        assert marker in css

    for forbidden in ["input type=\"file\"", "showOpenFilePicker", "FileReader", "readAsDataURL"]:
        assert forbidden not in flow


def test_script_add_node_flow_matches_libtv_script_generator_controls() -> None:
    flow = _read(WORKBENCH_ROOT / "src" / "render-studio-add-node-flow.js")
    css = _read(WORKBENCH_ROOT / "styles-studio-script-generator-flow.css")
    index = _read(WORKBENCH_ROOT / "index.html")

    for marker in [
        "renderScriptGeneratorFlow",
        "libtv-script-generator-flow",
        "libtv-script-generator-card",
        "libtv-script-reference-node",
        "libtv-script-generator-control",
        "libtv-script-attempts",
        "脚本生成器",
        "尝试：",
        "剧本生成分镜脚本",
        "视频参考生成分镜脚本",
        "角色生成分镜脚本",
        "描述剧情或添加角色参考、视频参考等，为你生成分镜脚本",
        "GVLM 3.1",
        "文本节点 2",
        "自己编写内容",
        "文生视频",
        "图片反推提示词",
        "文字生音乐",
        "脚本生成未启动",
        "参考文本只登记安全摘要，不上传素材、不启动生成。",
    ]:
        assert marker in flow

    for marker in [
        ".libtv-script-generator-flow",
        ".libtv-script-generator-card",
        ".libtv-script-reference-node",
        ".libtv-script-generator-control",
        ".libtv-script-attempts",
    ]:
        assert marker in css

    assert '<link rel="stylesheet" href="./styles-studio-script-generator-flow.css" />' in index

    for forbidden in ["showOpenFilePicker", "FileReader", "fetch(\"/provider", "AFS_ALLOW_REMOTE_LLM"]:
        assert forbidden not in flow


def test_text_add_node_flow_matches_libtv_text_node_controls() -> None:
    flow = _read(WORKBENCH_ROOT / "src" / "render-studio-add-node-flow.js")
    index = _read(WORKBENCH_ROOT / "index.html")

    for marker in [
        "renderTextNodeFlow",
        "libtv-text-node-flow",
        "libtv-text-node-card",
        "libtv-text-node-placeholder",
        "libtv-text-generator-control",
        "libtv-text-attempts",
        "文本节点 2",
        "尝试：",
        "自己编写内容",
        "文生视频",
        "图片反推提示词",
        "文字生音乐",
        "写下你想讲的故事、场景或角色设定。例如：一个来自未来的机器人，在城市屋顶看星星。",
        "GVLM 3.1",
        "文本只登记安全摘要，不上传素材、不启动生成。",
        "文本生成未启动",
    ]:
        assert marker in flow

    css = _read(WORKBENCH_ROOT / "styles-studio-text-node-flow.css")
    for marker in [
        ".libtv-text-node-flow",
        ".libtv-text-node-card",
        ".libtv-text-node-placeholder",
        ".libtv-text-generator-control",
        ".libtv-text-attempts",
    ]:
        assert marker in css

    assert '<link rel="stylesheet" href="./styles-studio-text-node-flow.css" />' in index

    for forbidden in ["showOpenFilePicker", "FileReader", "fetch(\"/provider", "AFS_ALLOW_REMOTE_LLM"]:
        assert forbidden not in flow


def test_video_add_node_flow_matches_libtv_video_controls_without_provider() -> None:
    flow = _read(WORKBENCH_ROOT / "src" / "render-studio-add-node-flow.js")
    video_flow = _read(WORKBENCH_ROOT / "src" / "render-studio-video-node-flow.js")
    index = _read(WORKBENCH_ROOT / "index.html")

    assert 'import { renderVideoNodeFlow } from "./render-studio-video-node-flow.js";' in flow
    assert 'if (kind === "video") return renderVideoNodeFlow(attrs);' in flow

    for marker in [
        "renderVideoNodeFlow",
        "libtv-video-node-flow",
        "libtv-video-node-card",
        "libtv-video-node-screen",
        "libtv-video-node-control",
        "libtv-video-mode-tabs",
        "libtv-video-tool-row",
        "libtv-video-param-grid",
        "视频节点",
        "文生视频",
        "全能参考",
        "图生视频",
        "首尾帧",
        "图片参考",
        "标记",
        "运镜",
        "角色库",
        "描述你想要生成的画面内容，@引用素材",
        "Seedance 2.0 VIP",
        "16:9 · 720P · 5s",
        "1个",
        "135",
        "联网搜索",
        "自动校验素材",
        "视频节点只登记画面摘要，不上传素材、不启动生成。",
        "视频生成未启动",
    ]:
        assert marker in video_flow

    css = _read(WORKBENCH_ROOT / "styles-studio-video-node-flow.css")
    for marker in [
        ".libtv-video-node-flow",
        ".libtv-video-node-card",
        ".libtv-video-node-screen",
        ".libtv-video-node-control",
        ".libtv-video-param-grid",
    ]:
        assert marker in css

    assert '<link rel="stylesheet" href="./styles-studio-video-node-flow.css" />' in index

    for forbidden in ["showOpenFilePicker", "FileReader", "fetch(\"/provider", "AFS_ALLOW_REMOTE_VIDEO"]:
        assert forbidden not in video_flow
