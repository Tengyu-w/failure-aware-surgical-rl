from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("aggregates", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, default=Path("runs") / "combined_aggregate_summary.csv")
    parser.add_argument("--report", type=Path, default=Path("runs") / "combined_report.md")
    return parser.parse_args()


def read_rows(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def fmt(row: dict, metric: str) -> str:
    return f"{float(row[f'{metric}_mean_over_seeds']):.3f}"


def write_csv(rows: list[dict], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_report(rows: list[dict], out: Path) -> None:
    lines = [
        "# Combined Prototype Results",
        "",
        "| Variant | Success | Budget Exhausted | Cost | Final Distance | Shield Interventions |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        interventions = row.get("shield_interventions_mean_mean_over_seeds", "")
        interventions_text = "" if interventions == "" else f"{float(interventions):.3f}"
        lines.append(
            "| {variant} | {success} | {budget} | {cost} | {distance} | {interventions} |".format(
                variant=row["variant"],
                success=fmt(row, "success_mean"),
                budget=fmt(row, "budget_exhausted_mean"),
                cost=fmt(row, "cumulative_cost_mean"),
                distance=fmt(row, "final_distance_mean"),
                interventions=interventions_text,
            )
        )

    best_success = max(rows, key=lambda row: float(row["success_mean_mean_over_seeds"]))
    safest = min(rows, key=lambda row: float(row["budget_exhausted_mean_mean_over_seeds"]))
    lowest_cost = min(rows, key=lambda row: float(row["cumulative_cost_mean_mean_over_seeds"]))
    lines.extend(
        [
            "",
            "## Current Reading",
            "",
            f"- Best success rate: `{best_success['variant']}`.",
            f"- Lowest budget exhaustion: `{safest['variant']}`.",
            f"- Lowest cumulative cost: `{lowest_cost['variant']}`.",
            "- These are prototype results from three seeds, so they should be treated as early evidence rather than final claims.",
            "",
        ]
    )
    out.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    rows = []
    for path in args.aggregates:
        rows.extend(read_rows(path))
    rows.sort(key=lambda row: row["variant"])
    write_csv(rows, args.out)
    write_report(rows, args.report)
    print(f"combined_csv={args.out}")
    print(f"combined_report={args.report}")


if __name__ == "__main__":
    main()
