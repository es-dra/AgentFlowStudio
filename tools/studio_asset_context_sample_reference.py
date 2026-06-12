from __future__ import annotations

import argparse
import struct
import zlib
from pathlib import Path


WIDTH = 512
HEIGHT = 768


def write_sample_reference(path: str | Path) -> Path:
    output = Path(path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    pixels = _portrait_pixels(WIDTH, HEIGHT)
    output.write_bytes(_png_bytes(WIDTH, HEIGHT, pixels))
    return output


def write_sample_scene_reference(path: str | Path) -> Path:
    output = Path(path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    pixels = _observatory_pixels(WIDTH, HEIGHT)
    output.write_bytes(_png_bytes(WIDTH, HEIGHT, pixels))
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Write a deterministic S1 character reference PNG.")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    path = write_sample_reference(args.output)
    print(str(path))
    return 0


def _portrait_pixels(width: int, height: int) -> bytes:
    rows: list[bytes] = []
    for y in range(height):
        row = bytearray()
        for x in range(width):
            row.extend(_pixel(x, y, width, height))
        rows.append(bytes(row))
    return b"".join(rows)


def _observatory_pixels(width: int, height: int) -> bytes:
    rows: list[bytes] = []
    for y in range(height):
        row = bytearray()
        for x in range(width):
            nx = (x - width / 2) / (width / 2)
            ny = (y - height / 2) / (height / 2)
            row.extend(_observatory_pixel(nx, ny))
        rows.append(bytes(row))
    return b"".join(rows)


def _pixel(x: int, y: int, width: int, height: int) -> tuple[int, int, int]:
    nx = (x - width / 2) / (width / 2)
    ny = (y - height / 2) / (height / 2)
    background = _background(nx, ny)
    if _coat(nx, ny):
        return (148, 24, 35)
    if _neck(nx, ny):
        return (198, 142, 112)
    if _face(nx, ny):
        if _brow_scar(nx, ny):
            return (82, 52, 45)
        if _eye(nx, ny):
            return (28, 24, 24)
        if _mouth(nx, ny):
            return (120, 48, 54)
        return (210, 158, 128)
    if _hair(nx, ny):
        return (18, 18, 20)
    return background


def _observatory_pixel(nx: float, ny: float) -> tuple[int, int, int]:
    dome = nx * nx + (ny + 0.32) * (ny + 0.32) < 0.82
    telescope_base = abs(nx) < 0.14 and -0.06 < ny < 0.28
    telescope_tube = -0.2 < nx < 0.45 and -0.2 < ny + nx * 0.28 < -0.13
    floor = ny > 0.32
    cracked_window = abs(nx + 0.5) < 0.08 and -0.18 < ny < 0.16
    star_chart = 0.36 < nx < 0.68 and -0.02 < ny < 0.22
    if telescope_tube:
        return (88, 96, 98)
    if telescope_base:
        return (111, 74, 47)
    if cracked_window:
        return (115, 178, 205)
    if star_chart:
        return (44, 65, 78)
    if floor:
        shade = int(42 + 25 * (1 - abs(nx)))
        return (shade, shade + 15, shade + 24)
    if dome:
        shade = int(34 + 40 * (1 - abs(nx)) + 20 * (1 - abs(ny + 0.3)))
        return (max(20, shade - 5), max(42, shade + 16), max(58, shade + 36))
    return (14, 25, 34)


def _background(nx: float, ny: float) -> tuple[int, int, int]:
    shade = int(42 + 32 * (1 - abs(nx)) + 22 * (1 - abs(ny)))
    return (max(24, shade - 8), max(31, shade), max(42, shade + 14))


def _coat(nx: float, ny: float) -> bool:
    return ny > 0.28 and abs(nx) < 0.58 + (ny - 0.28) * 0.35


def _neck(nx: float, ny: float) -> bool:
    return abs(nx) < 0.16 and 0.16 < ny < 0.38


def _face(nx: float, ny: float) -> bool:
    return (nx / 0.34) ** 2 + ((ny + 0.22) / 0.42) ** 2 < 1


def _hair(nx: float, ny: float) -> bool:
    cap = (nx / 0.42) ** 2 + ((ny + 0.43) / 0.33) ** 2 < 1
    side = abs(nx) > 0.26 and abs(nx) < 0.43 and -0.48 < ny < 0.12
    fringe = -0.58 < ny < -0.32 and -0.22 < nx < 0.32
    return cap or side or fringe


def _eye(nx: float, ny: float) -> bool:
    left = ((nx + 0.13) / 0.055) ** 2 + ((ny + 0.24) / 0.018) ** 2 < 1
    right = ((nx - 0.13) / 0.055) ** 2 + ((ny + 0.24) / 0.018) ** 2 < 1
    return left or right


def _brow_scar(nx: float, ny: float) -> bool:
    return -0.28 < nx < -0.16 and -0.31 < ny < -0.27 and (nx + 0.28) * 0.35 < (ny + 0.31)


def _mouth(nx: float, ny: float) -> bool:
    return abs(nx) < 0.11 and 0.0 < ny < 0.025


def _png_bytes(width: int, height: int, rgb: bytes) -> bytes:
    raw_rows = []
    stride = width * 3
    for offset in range(0, len(rgb), stride):
        raw_rows.append(b"\x00" + rgb[offset : offset + stride])
    raw = b"".join(raw_rows)
    return b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)),
            _chunk(b"IDAT", zlib.compress(raw, level=9)),
            _chunk(b"IEND", b""),
        ]
    )


def _chunk(kind: bytes, payload: bytes) -> bytes:
    crc = zlib.crc32(kind + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", crc)


if __name__ == "__main__":
    raise SystemExit(main())
