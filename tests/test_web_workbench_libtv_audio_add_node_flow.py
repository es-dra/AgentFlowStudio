from __future__ import annotations

from pathlib import Path


WORKBENCH_ROOT = Path("apps/workbench")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_audio_add_node_flow_matches_libtv_audio_controls_without_uploading() -> None:
    flow = _read(WORKBENCH_ROOT / "src" / "render-studio-add-node-flow.js")
    audio_flow = _read(WORKBENCH_ROOT / "src" / "render-studio-audio-node-flow.js")
    index = _read(WORKBENCH_ROOT / "index.html")

    assert 'import { renderAudioNodeFlow } from "./render-studio-audio-node-flow.js";' in flow
    assert 'if (kind === "audio") return renderAudioNodeFlow(attrs);' in flow

    for marker in [
        "renderAudioNodeFlow",
        "libtv-audio-node-flow",
        "libtv-audio-node-card",
        "libtv-audio-node-waveform",
        "libtv-audio-node-control",
        "libtv-audio-mode-tabs",
        "libtv-audio-tool-row",
        "libtv-audio-param-grid",
        "音频节点",
        "00:00 / 00:03",
        "图片",
        "视频",
        "文生视频",
        "全能参考",
        "图生视频",
        "首尾帧",
        "图片参考",
        "标记",
        "运镜",
        "角色库",
        "根据上传的音频生成对应场景画面，镜头语言、节奏、音乐匹配情绪变化，电影级质感。",
        "Seedance 2.0 VIP",
        "16:9 · 720P · 5s",
        "1个",
        "135",
        "联网搜索",
        "自动校验素材",
        "点击按钮，可替换上传你的音频文件",
        "音频节点只登记音频摘要，不读取本地文件字节、不启动生成。",
        "音频生成未启动",
    ]:
        assert marker in audio_flow

    css = _read(WORKBENCH_ROOT / "styles-studio-audio-node-flow.css")
    for marker in [
        ".libtv-audio-node-flow",
        ".libtv-audio-node-card",
        ".libtv-audio-node-waveform",
        ".libtv-audio-node-control",
        ".libtv-audio-param-grid",
    ]:
        assert marker in css

    assert '<link rel="stylesheet" href="./styles-studio-audio-node-flow.css" />' in index

    for forbidden in ["input type=\"file\"", "showOpenFilePicker", "FileReader", "readAsArrayBuffer", "AFS_ALLOW_REMOTE_AUDIO"]:
        assert forbidden not in audio_flow
