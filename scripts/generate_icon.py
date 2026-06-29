#!/usr/bin/env python3
"""Generate ORION icon (orion.ico) with gold/blue/black branding.

The icon is a stylized 'O' letter on a dark background,
using the ORION brand colors.

Usage:
    python scripts/generate_icon.py
    python scripts/generate_icon.py --size 256 --output installer/icons/orion.ico
"""

from __future__ import annotations

import argparse
import struct
import zlib
from pathlib import Path


def _create_png(size: int, bg_color: tuple[int, ...], fg_color: tuple[int, ...], accent_color: tuple[int, ...]) -> bytes:
    """Create a minimalist 'O' icon as PNG bytes."""
    import struct

    def write_chunk(chunk_type: bytes, data: bytes) -> bytes:
        chunk = chunk_type + data
        return struct.pack(">I", len(data)) + chunk + struct.pack(">I", zlib.crc32(chunk) & 0xFFFFFFFF)

    # RGBA pixel data
    raw_data = bytearray()
    for y in range(size):
        raw_data.append(0)  # filter byte
        for x in range(size):
            cx, cy = size // 2, size // 2
            radius = size * 0.38
            ring_inner = size * 0.18

            dx, dy = x - cx, y - cy
            dist = (dx * dx + dy * dy) ** 0.5

            if dist < ring_inner:
                # Inner circle → background color
                raw_data.extend(bg_color)
            elif dist < radius:
                # Ring → gradient from gold to blue
                t = (dist - ring_inner) / (radius - ring_inner)
                r = int(fg_color[0] * (1 - t) + accent_color[0] * t)
                g = int(fg_color[1] * (1 - t) + accent_color[1] * t)
                b = int(fg_color[2] * (1 - t) + accent_color[2] * t)
                raw_data.extend((r, g, b, 255))
            else:
                # Outside → transparent
                raw_data.extend((0, 0, 0, 0))

    # Build PNG
    png = b"\x89PNG\r\n\x1a\n"
    png += write_chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
    png += write_chunk(b"IDAT", zlib.compress(bytes(raw_data)))
    png += write_chunk(b"IEND", b"")
    return png


def _create_ico(png_sizes: list[int]) -> bytes:
    """Combine multiple PNGs into a single ICO file."""
    png_data: list[bytes] = []
    for size in png_sizes:
        bg = (10, 11, 15, 255)       # #0a0b0f
        gold = (212, 175, 55, 255)    # #d4af37
        blue = (59, 130, 246, 255)    # #3b82f6
        png_data.append(_create_png(size, bg, gold, blue))

    # ICO header
    count = len(png_sizes)
    ico = struct.pack("<HHH", 0, 1, count)  # reserved, type=1 (icon), count

    offset = 6 + count * 16
    for i, (size, png) in enumerate(zip(png_sizes, png_data)):
        w = size if size < 256 else 0
        h = size if size < 256 else 0
        ico += struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(png), offset)
        offset += len(png)

    for png in png_data:
        ico += png

    return ico


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate ORION icon (.ico)")
    parser.add_argument("--output", default="installer/icons/orion.ico", help="Output path")
    parser.add_argument("--sizes", nargs="+", type=int, default=[16, 32, 48, 64, 128, 256],
                        help="Icon sizes to include")
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    ico_data = _create_ico(args.sizes)
    output.write_bytes(ico_data)
    print(f"  ORION icon generated: {output} ({len(ico_data)} bytes, {len(args.sizes)} sizes)")
    print(f"  Sizes: {', '.join(str(s) for s in args.sizes)}px")


if __name__ == "__main__":
    main()
