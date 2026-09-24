"""Offline-only replay of immutable IBM result files.

This module has no IBM Runtime import and cannot submit or retrieve a job.
"""

from __future__ import annotations

import csv
import json
from math import sqrt
from pathlib import Path

import pandas as pd


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_IBM_DATA_ROOT = PACKAGE_ROOT / "data/ibm_hardware_existing"


def wilson_interval(successes: int, shots: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if shots <= 0 or successes < 0 or successes > shots:
        raise ValueError("require 0 <= successes <= shots and shots > 0")
    p = successes / shots
    denominator = 1 + z * z / shots
    center = (p + z * z / (2 * shots)) / denominator
    half = z * sqrt(p * (1 - p) / shots + z * z / (4 * shots * shots)) / denominator
    return center - half, center + half


def analyze_existing_hardware(output_path: Path, input_root: Path = DEFAULT_IBM_DATA_ROOT) -> None:
    """Recompute direct and derived metrics without constructing an IBM service."""
    input_root = input_root.resolve()
    final = pd.read_csv(input_root / "composed_candidate_final.csv").iloc[0]
    raw_counts = json.loads(final["counts_json"])
    shots = int(sum(raw_counts.values()))
    expected = f"{int(final['expected']):03d}"
    success_count = int(raw_counts.get(expected, 0))
    low, high = wilson_interval(success_count, shots)
    rows = [
        {
            "record_type": "composed_candidate_final",
            "execution": final["execution"],
            "case": "composed_candidate_m1",
            "m": 1,
            "DIRECT_HARDWARE": "YES",
            "DERIVED_FROM_SINGLE_TEST": "NO",
            "backend": final["backend"],
            "job_id": final["job_id"],
            "shots": shots,
            "recomputed_accept_probability": success_count / shots,
            "recomputed_detection_probability": "",
            "recomputed_wilson_95_low": low,
            "recomputed_wilson_95_high": high,
            "stored_probability": float(final["success_probability"]),
            "absolute_difference": abs(success_count / shots - float(final["success_probability"])),
            "composition_assumption": "direct m=1 hardware counts",
        }
    ]

    swap = pd.read_csv(input_root / "swap_test_hardware.csv")
    for (execution, case), group in swap.groupby(["execution", "case"], sort=False):
        direct = group[group["lambda"] == 1].iloc[0]
        single_accept = float(direct["single_test_accept_probability"])
        single_detection = 1.0 - single_accept
        detection_count = int(round(single_detection * int(direct["shots"])))
        direct_low, direct_high = wilson_interval(detection_count, int(direct["shots"]))
        for m in (1, 2, 4, 8):
            old = group[group["lambda"] == m].iloc[0]
            accept = single_accept**m
            detection = 1.0 - accept
            interval_low = 1.0 - (1.0 - direct_low) ** m
            interval_high = 1.0 - (1.0 - direct_high) ** m
            rows.append(
                {
                    "record_type": "swap_test",
                    "execution": execution,
                    "case": case,
                    "m": m,
                    "DIRECT_HARDWARE": "YES" if m == 1 else "NO",
                    "DERIVED_FROM_SINGLE_TEST": "NO" if m == 1 else "YES",
                    "backend": direct["backend"],
                    "job_id": direct["job_id"],
                    "shots": int(direct["shots"]),
                    "recomputed_accept_probability": accept,
                    "recomputed_detection_probability": detection,
                    "recomputed_wilson_95_low": interval_low,
                    "recomputed_wilson_95_high": interval_high,
                    "stored_probability": float(old["composed_detection_probability"]),
                    "absolute_difference": abs(detection - float(old["composed_detection_probability"])),
                    "composition_assumption": "direct m=1 hardware estimate" if m == 1 else "analytical independent-identical composition from m=1 estimate",
                }
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
