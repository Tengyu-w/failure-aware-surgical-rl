from __future__ import annotations

import argparse
import csv
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prototype", type=Path, required=True)
    parser.add_argument("--strict", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("runs") / "cross_preset_report.md")
    return parser.parse_args()


def read_rows(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def metric(row: dict, name: str) -> float:
    return float(row[f"{name}_mean_over_seeds"])


def table(title: str, rows: list[dict]) -> list[str]:
    lines = [
        f"## {title}",
        "",
        "| Variant | Success | Budget Exhausted | Cost | Final Distance |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in sorted(rows, key=lambda item: item["variant"]):
        lines.append(
            "| {variant} | {success:.3f} | {budget:.3f} | {cost:.3f} | {distance:.3f} |".format(
                variant=row["variant"],
                success=metric(row, "success_mean"),
                budget=metric(row, "budget_exhausted_mean"),
                cost=metric(row, "cumulative_cost_mean"),
                distance=metric(row, "final_distance_mean"),
            )
        )
    return lines


def best_by(rows: list[dict], metric_name: str, reverse: bool) -> str:
    row = sorted(rows, key=lambda item: metric(item, metric_name), reverse=reverse)[0]
    return row["variant"]


def main() -> None:
    args = parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    prototype_rows = read_rows(args.prototype)
    strict_rows = read_rows(args.strict)

    lines = [
        "# Cross-Preset Evaluation Report",
        "",
        "These results compare models trained on the prototype setting and evaluated on both prototype and strict presets.",
        "",
        *table("Prototype Evaluation", prototype_rows),
        "",
        *table("Strict Evaluation", strict_rows),
        "",
        "## Current Reading",
        "",
        f"- Prototype best success: `{best_by(prototype_rows, 'success_mean', True)}`.",
        f"- Prototype lowest budget exhaustion: `{best_by(prototype_rows, 'budget_exhausted_mean', False)}`.",
        f"- Strict best success: `{best_by(strict_rows, 'success_mean', True)}`.",
        f"- Strict lowest budget exhaustion: `{best_by(strict_rows, 'budget_exhausted_mean', False)}`.",
        "- The shielded variants consistently reduce budget exhaustion and cumulative cost.",
        "- Curriculum is promising on prototype success, but strict transfer still has high variance.",
        "",
    ]
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"cross_preset_report={args.out}")


if __name__ == "__main__":
    main()
