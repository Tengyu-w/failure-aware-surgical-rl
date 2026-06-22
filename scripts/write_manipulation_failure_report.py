from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np


FAILURE_MODES = ("none", "object_state_bias", "object_dropout", "execution_slip", "contact_loss")
CONTROLLERS = ("base", "monitor")
FILE_STEMS = {"object_state_bias": "object_bias"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", default="manip_failure")
    parser.add_argument("--runs-dir", type=Path, default=Path("runs"))
    parser.add_argument("--out", type=Path, default=Path("runs") / "manipulation_failure_report.md")
    return parser.parse_args()


def read_rows(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def mean(rows: list[dict], key: str) -> float:
    values = np.array([float(row.get(key, 0.0) or 0.0) for row in rows], dtype=np.float64)
    if np.isnan(values).all():
        return 0.0
    return float(np.nanmean(values))


def fmt(value: float) -> str:
    return f"{value:.3f}"


def summarize(path: Path) -> dict:
    rows = read_rows(path)
    return {
        "success": mean(rows, "success"),
        "object_delivered": mean(rows, "object_delivered"),
        "budget_exhausted": mean(rows, "budget_exhausted"),
        "cost": mean(rows, "cumulative_cost"),
        "final_distance": mean(rows, "final_distance"),
        "object_goal_distance": mean(rows, "object_goal_distance"),
        "detected": mean(rows, "failure_detected"),
        "recovery_triggered": mean(rows, "recovery_triggered"),
        "recovery_steps": mean(rows, "recovery_steps_used"),
        "false_intervention": mean(rows, "false_intervention"),
        "class_correct": mean(rows, "failure_class_correct"),
    }


def main() -> None:
    args = parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Manipulation Failure-Recovery Report",
        "",
        "## Aggregate Table",
        "",
        "| Failure Mode | Controller | Success | Object Delivered | Budget Exhausted | Cost | Final Distance | Object-Goal Distance | Detected | Recovery Triggered | False Trigger | Class Correct |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for failure_mode in FAILURE_MODES:
        for controller in CONTROLLERS:
            file_stem = FILE_STEMS.get(failure_mode, failure_mode)
            path = args.runs_dir / f"{args.prefix}_{file_stem}_{controller}.csv"
            if not path.exists():
                continue
            row = summarize(path)
            lines.append(
                f"| {failure_mode} | {controller} | {fmt(row['success'])} | {fmt(row['object_delivered'])} | "
                f"{fmt(row['budget_exhausted'])} | {fmt(row['cost'])} | {fmt(row['final_distance'])} | "
                f"{fmt(row['object_goal_distance'])} | {fmt(row['detected'])} | {fmt(row['recovery_triggered'])} | "
                f"{fmt(row['false_intervention'])} | {fmt(row['class_correct'])} |"
            )

    lines.extend(
        [
            "",
            "## Key Readings",
            "",
            "- The manipulation proxy extends the project beyond point reaching into object-state change.",
            "- `object_state_bias` and `object_dropout` probe object-state estimation failures.",
            "- `execution_slip` probes manipulation execution reliability after the object has been moved.",
            "- `contact_loss` probes the case where the tool moves but the object stops responding to push actions.",
            "- `Class Correct` reports whether the runtime diagnosis matches the injected failure type.",
            "- `False Trigger` reports unnecessary intervention under nominal execution.",
            "- The monitor should preserve nominal execution while recovering from injected manipulation failures.",
            "",
        ]
    )
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"report={args.out}")


if __name__ == "__main__":
    main()
