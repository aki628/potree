#!/usr/bin/env python3
"""Backfill classification values in a LAS file using Z-based bins.

Default bins:
  [0.0, 0.2) -> 2
  [0.2, 0.4) -> 3
  [0.4, 0.6) -> 4
  [0.6, 0.8) -> 5
  [0.8, 1.0] -> 6
"""

from __future__ import annotations

import argparse
import os
import struct
import time
from typing import Dict, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--path",
        default="data/sample.las",
        help="Target LAS path (default: data/sample.las)",
    )
    parser.add_argument(
        "--chunk-points",
        type=int,
        default=500_000,
        help="Points per chunk while scanning/writing (default: 500000)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only analyze and print target histogram without writing.",
    )
    return parser.parse_args()


def parse_header(path: str) -> Dict[str, int]:
    with open(path, "rb") as f:
        base = f.read(375)

    if len(base) < 375:
        raise RuntimeError("LAS header too short (<375 bytes)")
    if base[:4] != b"LASF":
        raise RuntimeError("Invalid LAS signature (expected LASF)")

    version_major = base[24]
    version_minor = base[25]
    point_format = base[104] & 0x3F
    record_length = struct.unpack_from("<H", base, 105)[0]
    offset_to_point_data = struct.unpack_from("<I", base, 96)[0]
    legacy_point_count = struct.unpack_from("<I", base, 107)[0]

    point_count = legacy_point_count
    if (version_major, version_minor) >= (1, 4):
        with open(path, "rb") as f:
            f.seek(247)
            count64 = struct.unpack("<Q", f.read(8))[0]
        if count64 > 0:
            point_count = count64

    if point_format <= 5:
        classification_offset = 15
    elif point_format <= 10:
        classification_offset = 16
    else:
        raise RuntimeError(f"Unsupported point format for classification: {point_format}")

    return {
        "version_major": version_major,
        "version_minor": version_minor,
        "point_format": point_format,
        "record_length": record_length,
        "offset_to_point_data": offset_to_point_data,
        "point_count": point_count,
        "classification_offset": classification_offset,
    }


def class_from_norm(z_norm: float) -> int:
    if z_norm < 0.2:
        return 2
    if z_norm < 0.4:
        return 3
    if z_norm < 0.6:
        return 4
    if z_norm < 0.8:
        return 5
    return 6


def pass_find_z_range(path: str, offset: int, rec_len: int, chunk_points: int) -> Tuple[int, int]:
    chunk_bytes = chunk_points * rec_len
    z_min = 2**31 - 1
    z_max = -(2**31)
    unpack_i32 = struct.Struct("<i").unpack_from

    with open(path, "rb") as f:
        f.seek(offset)
        while True:
            block = f.read(chunk_bytes)
            if not block:
                break

            points = len(block) // rec_len
            if points == 0:
                break

            for i in range(points):
                base = i * rec_len
                z_raw = unpack_i32(block, base + 8)[0]
                if z_raw < z_min:
                    z_min = z_raw
                if z_raw > z_max:
                    z_max = z_raw

    if z_min > z_max:
        raise RuntimeError("No points found while scanning Z range")

    return z_min, z_max


def pass_apply_classification(
    path: str,
    offset: int,
    rec_len: int,
    cls_off: int,
    chunk_points: int,
    z_min: int,
    z_max: int,
    dry_run: bool,
) -> Dict[int, int]:
    chunk_bytes = chunk_points * rec_len
    unpack_i32 = struct.Struct("<i").unpack_from
    counts = {2: 0, 3: 0, 4: 0, 5: 0, 6: 0}

    span = z_max - z_min
    if span <= 0:
        span = 1

    mode = "rb" if dry_run else "r+b"

    with open(path, mode) as f:
        f.seek(offset)
        cursor = offset

        while True:
            block = f.read(chunk_bytes)
            if not block:
                break

            points = len(block) // rec_len
            if points == 0:
                break

            mutable = None
            if not dry_run:
                mutable = bytearray(block)

            for i in range(points):
                base = i * rec_len
                z_raw = unpack_i32(block, base + 8)[0]
                z_norm = (z_raw - z_min) / span
                cls = class_from_norm(z_norm)
                counts[cls] += 1

                if mutable is not None:
                    mutable[base + cls_off] = cls

            if mutable is not None:
                f.seek(cursor)
                f.write(mutable)
                f.flush()

            cursor += points * rec_len
            f.seek(cursor)

    return counts


def main() -> None:
    args = parse_args()
    target = args.path
    if not os.path.exists(target):
        raise SystemExit(f"File not found: {target}")

    info = parse_header(target)

    print("LAS info")
    print(
        f"  version={info['version_major']}.{info['version_minor']} "
        f"fmt={info['point_format']} rec_len={info['record_length']} "
        f"points={info['point_count']}"
    )
    print(f"  classification_offset={info['classification_offset']}")

    t0 = time.time()
    z_min, z_max = pass_find_z_range(
        target,
        info["offset_to_point_data"],
        info["record_length"],
        args.chunk_points,
    )
    t1 = time.time()
    print(f"Z range: min={z_min} max={z_max} (scan {t1 - t0:.2f}s)")

    counts = pass_apply_classification(
        target,
        info["offset_to_point_data"],
        info["record_length"],
        info["classification_offset"],
        args.chunk_points,
        z_min,
        z_max,
        args.dry_run,
    )
    t2 = time.time()

    mode = "dry-run" if args.dry_run else "write"
    print(f"Classification {mode} pass: {t2 - t1:.2f}s")
    print("Histogram")
    total = 0
    for cls in sorted(counts):
        c = counts[cls]
        total += c
        print(f"  class {cls}: {c}")
    print(f"  total: {total}")


if __name__ == "__main__":
    main()
