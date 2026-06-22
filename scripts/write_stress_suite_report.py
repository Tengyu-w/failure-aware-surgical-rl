from __future__ import annotations

import argparse
import csv
from pathlib import Path


METRICS = [
    "success_mean",
    "budget_exhausted_mean",
    "cumulative_cost_mean",
    "final_distance_mean",
    "shield_interventions_mean",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-dir", type=Path, default=Path("runs"))
    parser.add_argument("--out", type=Path, default=Path("reports") / "stress_transfer_suite_report.md")
    return parser.parse_args()


def read_rows(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def metric(row: dict, name: str) -> float:
    return float(row[f"{name}_mean_over_seeds"])


def fmt(value: float) -> str:
    return f"{value:.3f}"


def preset_name(path: Path) -> str:
    name = path.name
    return name.removeprefix("stress_").removesuffix("_aggregate_summary.csv")


def main() -> None:
    args = parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    aggregate_files = sorted(args.runs_dir.glob("stress_*_aggregate_summary.csv"))

    lines = [
        "# Expanded Stress Transfer Suite",
        "",
        "This report evaluates trained prototype policies across additional surgical-proxy and stress presets.",
        "",
        "## Preset-Level Tables",
        "",
    ]

    all_rows: list[tuple[str, dict]] = []
    for path in aggregate_files:
        preset = preset_name(path)
        rows = read_rows(path)
        all_rows.extend((preset, row) for row in rows)
        lines.extend(
            [
                f"### {preset}",
                "",
                "| Variant | Success | Budget Exhausted | Cost | Final Distance | Shield Interventions |",
                "|---|---:|---:|---:|---:|---:|",
            ]
        )
        for row in sorted(rows, key=lambda item: item["variant"]):
            lines.append(
                "| {variant} | {success} | {budget} | {cost} | {distance} | {interventions} |".format(
                    variant=row["variant"],
                    success=fmt(metric(row, "success_mean")),
                    budget=fmt(metric(row, "budget_exhausted_mean")),
                    cost=fmt(metric(row, "cumulative_cost_mean")),
                    distance=fmt(metric(row, "final_distance_mean")),
                    interventions=fmt(metric(row, "shield_interventions_mean")),
                )
            )
        lines.append("")

    if all_rows:
        by_variant: dict[str, list[tuple[str, dict]]] = {}
        for preset, row in all_rows:
            by_variant.setdefault(row["variant"], []).append((preset, row))

        lines.extend(["## Cross-Preset Averages", "", "| Variant | Mean Success | Mean Budget Exhausted | Mean Cost | Mean Final Distance |", "|---|---:|---:|---:|---:|"])
        for variant, entries in sorted(by_variant.items()):
            lines.append(
                "| {variant} | {success} | {budget} | {cost} | {distance} |".format(
                    variant=variant,
                    success=fmt(sum(metric(row, "success_mean") for _, row in entries) / len(entries)),
                    budget=fmt(sum(metric(row, "budget_exhausted_mean") for _, row in entries) / len(entries)),
                    cost=fmt(sum(metric(row, "cumulative_cost_mean") for _, row in entries) / len(entries)),
                    distance=fmt(sum(metric(row, "final_distance_mean") for _, row in entries) / len(entries)),
                )
            )

        lines.extend(
            [
                "",
                "## Reading",
                "",
                "- This stress suite is a transfer-style evaluation: models are trained on prototype-style settings, then evaluated on additional presets.",
                "- Surgical-proxy presets increase document and experiment volume, but they should be described as abstract proxies until implemented in SurRoL/MuJoCo.",
                "- The main question is whether tangent backup control remains robust when target precision, action scale, budget, and forbidden radius change.",
                "",
            ]
        )

    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"stress_report={args.out}")


if __name__ == "__main__":
    main()
