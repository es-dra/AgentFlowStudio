from __future__ import annotations

import struct
from typing import Any


def image_dimensions(image_bytes: bytes) -> dict[str, Any]:
    size = _png_dimensions(image_bytes) or _jpeg_dimensions(image_bytes)
    if size is None:
        return {}
    width, height = size
    if width <= 0 or height <= 0:
        return {}
    return {
        "width": width,
        "height": height,
        "aspect_ratio": f"{width}:{height}",
    }


def image_extension(image_bytes: bytes) -> str:
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if image_bytes.startswith(b"\xff\xd8"):
        return ".jpg"
    return ""


def image_mime_type_from_bytes(image_bytes: bytes) -> str:
    suffix = image_extension(image_bytes)
    if suffix == ".png":
        return "image/png"
    if suffix == ".jpg":
        return "image/jpeg"
    return ""


def _png_dimensions(image_bytes: bytes) -> tuple[int, int] | None:
    if not image_bytes.startswith(b"\x89PNG\r\n\x1a\n") or len(image_bytes) < 24:
        return None
    return struct.unpack(">II", image_bytes[16:24])


def _jpeg_dimensions(image_bytes: bytes) -> tuple[int, int] | None:
    if not image_bytes.startswith(b"\xff\xd8"):
        return None
    index = 2
    length = len(image_bytes)
    while index + 9 < length:
        while index < length and image_bytes[index] == 0xFF:
            index += 1
        if index >= length:
            return None
        marker = image_bytes[index]
        index += 1
        if marker in {0xD8, 0xD9}:
            continue
        if index + 2 > length:
            return None
        segment_length = int.from_bytes(image_bytes[index : index + 2], "big")
        if segment_length < 2 or index + segment_length > length:
            return None
        if marker in {
            0xC0,
            0xC1,
            0xC2,
            0xC3,
            0xC5,
            0xC6,
            0xC7,
            0xC9,
            0xCA,
            0xCB,
            0xCD,
            0xCE,
            0xCF,
        }:
            if segment_length < 7:
                return None
            height = int.from_bytes(image_bytes[index + 3 : index + 5], "big")
            width = int.from_bytes(image_bytes[index + 5 : index + 7], "big")
            return width, height
        index += segment_length
    return None


__all__ = ("image_dimensions", "image_extension", "image_mime_type_from_bytes")
