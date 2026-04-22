#!/usr/bin/env python3
"""Generate X-axis interval label-index JSON from a LAS file.

Output shape:
{
  "metadata": {...},
  "intervals": [
    {
      "index": 0,
      "xMin": ...,
      "xMax": ...,
      "labelIndexes": {
        "Ground": [12, 18, ...]
      }
    }
  ]
}
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--path",
        default="data/sample.las",
        help="Target LAS path (default: data/sample.las)",
    )
    parser.add_argument(
        "--label-map",
        default="data/sample_labels.xml",
        help="Label XML path (default: data/sample_labels.xml)",
    )
    parser.add_argument(
        "--out",
        default="data/sample_label_indexes_by_x.json",
        help="Output JSON path (default: data/sample_label_indexes_by_x.json)",
    )
    parser.add_argument(
        "--intervals",
        type=int,
        default=8,
        help="Number of X-axis intervals (default: 8)",
    )
    parser.add_argument(
        "--chunk-points",
        type=int,
        default=500_000,
        help="Points per chunk while scanning (default: 500000)",
    )
    parser.add_argument(
        "--max-points",
        type=int,
        default=500_000,
        help="Limit scanned points (0 means all points, default: 500000)",
    )
    return parser.parse_args()


def parse_las_header(path: str) -> Dict[str, float]:
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
        raise RuntimeError(f"Unsupported point format: {point_format}")

    x_scale = struct.unpack_from("<d", base, 131)[0]
    x_offset = struct.unpack_from("<d", base, 155)[0]

    return {
        "version_major": version_major,
        "version_minor": version_minor,
        "point_format": point_format,
        "record_length": record_length,
        "offset_to_point_data": offset_to_point_data,
        "point_count": point_count,
        "classification_offset": classification_offset,
        "x_scale": x_scale,
        "x_offset": x_offset,
    }


def parse_label_map(path: str) -> Dict[int, str]:
    if not os.path.exists(path):
        raise RuntimeError(f"Label map not found: {path}")

    tree = ET.parse(path)
    root = tree.getroot()
    result: Dict[int, str] = {}

    for node in root.iter():
        if node.tag.lower() != "label":
            continue
        label_id_text = node.get("id")
        if label_id_text is None:
            continue
        try:
            label_id = int(label_id_text)
        except ValueError:
            continue

        name = (
            node.get("name")
            or node.get("label")
            or node.text
            or f"Class {label_id}"
        )
        result[label_id] = str(name).strip() or f"Class {label_id}"

    return result


def find_x_raw_range(
    path: str,
    offset: int,
    rec_len: int,
    chunk_points: int,
    scan_limit: int,
) -> Tuple[int, int, int]:
    unpack_i32 = struct.Struct("<i").unpack_from
    x_min = 2**31 - 1
    x_max = -(2**31)
    scanned = 0

    with open(path, "rb") as f:
        f.seek(offset)
        while scanned < scan_limit:
            remaining = scan_limit - scanned
            read_points = min(chunk_points, remaining)
            block = f.read(read_points * rec_len)
            if not block:
                break

            points = len(block) // rec_len
            if points <= 0:
                break

            for i in range(points):
                x_raw = unpack_i32(block, i * rec_len)[0]
                if x_raw < x_min:
                    x_min = x_raw
                if x_raw > x_max:
                    x_max = x_raw

            scanned += points

    if scanned == 0:
        raise RuntimeError("No points scanned while finding X range")

    return x_min, x_max, scanned


def point_interval_index(x_raw: int, x_min: int, x_max: int, interval_count: int) -> int:
    if interval_count <= 1 or x_min == x_max:
        return 0
    ratio = (x_raw - x_min) / (x_max - x_min)
    idx = int(ratio * interval_count)
    if idx >= interval_count:
        idx = interval_count - 1
    if idx < 0:
        idx = 0
    return idx


def build_intervals(
    interval_count: int,
    x_raw_min: int,
    x_raw_max: int,
    x_scale: float,
    x_offset: float,
) -> List[Dict[str, object]]:
    intervals: List[Dict[str, object]] = []

    if interval_count <= 0:
        raise RuntimeError("intervals must be >= 1")

    if interval_count == 1 or x_raw_min == x_raw_max:
        intervals.append(
            {
                "index": 0,
                "xMin": x_raw_min * x_scale + x_offset,
                "xMax": x_raw_max * x_scale + x_offset,
                "labelIndexes": {},
            }
        )
        return intervals

    raw_span = x_raw_max - x_raw_min
    for idx in range(interval_count):
        left_ratio = idx / interval_count
        right_ratio = (idx + 1) / interval_count
        left_raw = x_raw_min + int(raw_span * left_ratio)
        right_raw = x_raw_min + int(raw_span * right_ratio)
        if idx == interval_count - 1:
            right_raw = x_raw_max

        intervals.append(
            {
                "index": idx,
                "xMin": left_raw * x_scale + x_offset,
                "xMax": right_raw * x_scale + x_offset,
                "labelIndexes": {},
            }
        )

    return intervals


def collect_label_indexes(
    path: str,
    offset: int,
    rec_len: int,
    cls_off: int,
    chunk_points: int,
    scan_limit: int,
    x_min: int,
    x_max: int,
    interval_count: int,
    label_map: Dict[int, str],
    intervals: List[Dict[str, object]],
) -> int:
    unpack_i32 = struct.Struct("<i").unpack_from
    unpack_u8 = struct.Struct("<B").unpack_from
    scanned = 0
    global_index = 0

    with open(path, "rb") as f:
        f.seek(offset)
        while scanned < scan_limit:
            remaining = scan_limit - scanned
            read_points = min(chunk_points, remaining)
            block = f.read(read_points * rec_len)
            if not block:
                break

            points = len(block) // rec_len
            if points <= 0:
                break

            for i in range(points):
                base = i * rec_len
                x_raw = unpack_i32(block, base)[0]
                cls_value = unpack_u8(block, base + cls_off)[0]
                label_name = label_map.get(cls_value, f"Class {cls_value}")
                interval_idx = point_interval_index(x_raw, x_min, x_max, interval_count)

                target = intervals[interval_idx]["labelIndexes"]  # type: ignore[index]
                if label_name not in target:
                    target[label_name] = []
                target[label_name].append(global_index)

                global_index += 1

            scanned += points

    return scanned


def main() -> None:
    args = parse_args()
    if not os.path.exists(args.path):
        raise SystemExit(f"LAS file not found: {args.path}")
    if args.intervals < 1:
        raise SystemExit("--intervals must be >= 1")

    header = parse_las_header(args.path)
    label_map = parse_label_map(args.label_map)
    total_points = int(header["point_count"])

    scan_limit = total_points
    if args.max_points > 0:
        scan_limit = min(scan_limit, args.max_points)

    x_min_raw, x_max_raw, scanned_range = find_x_raw_range(
        args.path,
        int(header["offset_to_point_data"]),
        int(header["record_length"]),
        args.chunk_points,
        scan_limit,
    )
    if scanned_range != scan_limit:
        scan_limit = scanned_range

    intervals = build_intervals(
        args.intervals,
        x_min_raw,
        x_max_raw,
        float(header["x_scale"]),
        float(header["x_offset"]),
    )

    scanned_collect = collect_label_indexes(
        args.path,
        int(header["offset_to_point_data"]),
        int(header["record_length"]),
        int(header["classification_offset"]),
        args.chunk_points,
        scan_limit,
        x_min_raw,
        x_max_raw,
        args.intervals,
        label_map,
        intervals,
    )

    payload = {
        "metadata": {
            "sourceLas": args.path,
            "labelMap": args.label_map,
            "axis": "x",
            "intervalCount": args.intervals,
            "pointCountTotal": total_points,
            "pointCountScanned": scanned_collect,
            "xMin": x_min_raw * float(header["x_scale"]) + float(header["x_offset"]),
            "xMax": x_max_raw * float(header["x_scale"]) + float(header["x_offset"]),
        },
        "intervals": intervals,
    }

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)

    print(f"Wrote: {args.out}")
    print(
        "Scanned points: "
        f"{payload['metadata']['pointCountScanned']} / {payload['metadata']['pointCountTotal']}"
    )


if __name__ == "__main__":
    main()
