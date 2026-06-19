from __future__ import annotations

import re


REMOTE_VIDEO_ENV = "AFS_ALLOW_REMOTE_VIDEO"
REMOTE_TRUE_VALUES = {"1", "true", "yes", "on"}
SAFE_CANDIDATE_ID = re.compile(r"^candidate_\d{3}$")
VIDEO_SUFFIX_TYPES = {
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
}
DAILY_VIDEO_SUBMIT_LIMIT = 3
VIDEO_NON_CLAIMS = [
    "runtime verification only",
    "not human acceptance",
    "not business validation",
    "not durable memory",
]
