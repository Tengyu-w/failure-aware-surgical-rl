from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path

import numpy as np


METRICS = [
    "success_mean",
    "budget_exhausted_mean",
    "cumulative_cost_mean",
    "final_distance_mean",
    "final_force_proxy_mean",
    "shield_interventions_mean",
    "mean_action_deviation_mean",
    "cumulative_action_deviation_mean",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("runs") / "aggregate_summary.csv")
    return parser.parse_args()


def load_rows(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def normalized_variant(row: dict) -> str:
    name = Path(row["eval_csv"]).parent.name
    known_variants = (
        "conditioned_tangent_shielded",
        "no_phase_budget_tangent_shielded",
        "conditioned_shielded",
        "no_phase_budget_shielded",
        "no_phase_budget",
        "conditioned",
        "no_budget",
    )
    for variant in known_variants:
        if name.endswith(f"_{variant}") or re.search(rf"_{variant}_seed\d+$", name):
            return variant
    match = re.fullmatch(r"proto_3d_[^_]+_(?P<variant>.+)_seed\d+", name)
    if match:
        return match.group("variant")
    match = re.fullmatch(r"proto_[^_]+_(?P<variant>.+)_seed\d+", name)
    if match:
        return match.group("variant")
    match = re.fullmatch(r"cmp_(?P<variant>.+)_seed\d+", name)
    if match:
        return match.group("variant")
    match = re.fullmatch(r"smoke_(?P<variant>.+)", name)
    if match:
        return match.group("variant")
    if "_seed" in name:
        return name.split("_seed")[0]
    return row["variant"]


def aggregate(rows: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[normalized_variant(row)].append(row)

    out_rows = []
    for variant, variant_rows in sorted(grouped.items()):
        out_row = {"variant": variant, "seeds": len(variant_rows)}
        for metric in METRICS:
            values = [float(row[metric]) for row in variant_rows if row.get(metric, "") != ""]
            if values:
                out_row[f"{metric}_mean_over_seeds"] = float(np.mean(values))
                out_row[f"{metric}_std_over_seeds"] = float(np.std(values, ddof=0))
        out_rows.append(out_row)
    return out_rows


def main() -> None:
    args = parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    rows = aggregate(load_rows(args.summary))

    fieldnames = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)

    with args.out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"aggregate_csv={args.out}")
    for row in rows:
        print(
            " | ".join(
                [
                    f"variant={row['variant']}",
                    f"success={row['success_mean_mean_over_seeds']:.3f}",
                    f"budget_exhausted={row['budget_exhausted_mean_mean_over_seeds']:.3f}",
                    f"cost={row['cumulative_cost_mean_mean_over_seeds']:.3f}",
                    f"distance={row['final_distance_mean_mean_over_seeds']:.3f}",
                ]
            )
        )


if __name__ == "__main__":
    main()
