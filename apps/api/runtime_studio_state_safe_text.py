from __future__ import annotations

import re


MEDIA_FILENAME_FRAGMENT_RE = re.compile(r"\.(?:mp4|mov)\b", re.IGNORECASE)


def strip_media_filename_fragment(value: str) -> str:
    return MEDIA_FILENAME_FRAGMENT_RE.sub("", value).strip()


def has_media_filename_fragment(value: str) -> bool:
    return bool(MEDIA_FILENAME_FRAGMENT_RE.search(value))


__all__ = ("has_media_filename_fragment", "strip_media_filename_fragment")
