from __future__ import annotations

from agentflow_studio.schemas import Transcript
from agentflow_studio.subtitle_sop.timeline import build_clip_timeline_subtitle_export


def test_clip_timeline_subtitles_map_source_transcript_to_final_video_timeline() -> None:
    transcript = Transcript.model_validate(_transcript())
    real_slice_manifest = {
        "status": "succeeded",
        "source_video": "data/raw/demo.mp4",
        "clip_count": 2,
        "clips": [
            {"clip_id": "clip_001", "start_sec": 6.0, "end_sec": 10.0, "duration_sec": 4.0, "status": "succeeded"},
            {"clip_id": "clip_002", "start_sec": 20.0, "end_sec": 24.0, "duration_sec": 4.0, "status": "succeeded"},
        ],
    }
    final_video_manifest = {"status": "succeeded", "final_video": "final_video.mp4", "duration_sec": 8.0}

    export = build_clip_timeline_subtitle_export(
        transcript,
        real_slice_manifest,
        final_video_manifest=final_video_manifest,
        subtitle_path="subtitles.srt",
    )

    assert export.manifest.status == "succeeded"
    assert export.manifest.source_video == "data/raw/demo.mp4"
    assert export.manifest.timeline == "final_video"
    assert export.manifest.duration_sec == 8.0
    assert [cue.segment_id for cue in export.manifest.cues] == ["seg_002", "seg_004"]
    assert export.manifest.cues[0].start_time == 0.0
    assert export.manifest.cues[0].end_time == 4.0
    assert export.manifest.cues[1].start_time == 4.0
    assert export.manifest.cues[1].end_time == 8.0
    assert "00:00:04,000 --> 00:00:08,000" in export.srt_text


def test_clip_timeline_subtitles_clip_cues_to_final_video_duration() -> None:
    transcript = Transcript.model_validate(_transcript())
    real_slice_manifest = {
        "status": "succeeded",
        "source_video": "data/raw/demo.mp4",
        "clip_count": 1,
        "clips": [
            {"clip_id": "clip_001", "start_sec": 20.0, "end_sec": 26.0, "duration_sec": 6.0, "status": "succeeded"},
        ],
    }
    final_video_manifest = {"status": "succeeded", "final_video": "final_video.mp4", "duration_sec": 4.0}

    export = build_clip_timeline_subtitle_export(
        transcript,
        real_slice_manifest,
        final_video_manifest=final_video_manifest,
    )

    assert export.manifest.duration_sec == 4.0
    assert export.manifest.cues[-1].end_time == 4.0
    assert all(cue.end_time <= 4.0 for cue in export.manifest.cues)
    assert "clipped_to_final_duration" in export.manifest.warnings


def _transcript() -> dict[str, object]:
    return {
        "transcript_id": "asr_transcript",
        "source_video": "data/raw/demo.mp4",
        "language": "en",
        "duration": 30.0,
        "segments": [
            {"segment_id": "seg_001", "start_time": 0.0, "end_time": 5.0, "text": "Opening context that is not selected."},
            {"segment_id": "seg_002", "start_time": 6.0, "end_time": 10.0, "text": "The real bottleneck is choosing what to cut."},
            {"segment_id": "seg_003", "start_time": 14.0, "end_time": 18.0, "text": "Middle context that should not appear."},
            {"segment_id": "seg_004", "start_time": 20.0, "end_time": 24.0, "text": "Validate the story before final assembly."},
            {"segment_id": "seg_005", "start_time": 24.0, "end_time": 26.0, "text": "This tail should be clipped when final duration is short."},
        ],
        "metadata": {},
    }
