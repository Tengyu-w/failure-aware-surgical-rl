from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np


FAILURE_MODES = ("none", "state_target_bias", "state_dropout", "execution_slip")
CONTROLLERS = ("policy_only", "monitor_recovery", "heuristic_only")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", default="failure_suite")
    parser.add_argument("--runs-dir", type=Path, default=Path("runs"))
    parser.add_argument("--out", type=Path, default=Path("runs") / "failure_suite_report.md")
    return parser.parse_args()


def read_rows(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def mean(rows: list[dict], key: str) -> float:
    values = np.array([float(row.get(key, 0.0) or 0.0) for row in rows], dtype=np.float64)
    if np.isnan(values).all():
        return 0.0
    return float(np.nanmean(values))


def optional_mean(rows: list[dict], key: str) -> float | None:
    if key not in rows[0]:
        return None
    values = np.array([float(row.get(key, np.nan) or np.nan) for row in rows], dtype=np.float64)
    if np.isnan(values).all():
        return None
    return float(np.nanmean(values))


def fmt(value: float) -> str:
    return f"{value:.3f}"


def fmt_optional(value: float | None) -> str:
    if value is None:
        return "N/A"
    return fmt(value)


def summarize(path: Path, failure_mode: str) -> dict:
    rows = read_rows(path)
    if "failure_class_correct" in rows[0]:
        class_correct = optional_mean(rows, "failure_class_correct")
    elif failure_mode == "none":
        class_correct = 1.0 - mean(rows, "drift_detected")
    else:
        class_correct = mean(rows, "drift_detected")

    if "false_intervention" in rows[0]:
        false_intervention = optional_mean(rows, "false_intervention")
    else:
        false_intervention = mean(rows, "drift_detected") if failure_mode == "none" else 0.0

    return {
        "success": mean(rows, "success"),
        "budget_exhausted": mean(rows, "budget_exhausted"),
        "cost": mean(rows, "cumulative_cost"),
        "final_distance": mean(rows, "final_distance"),
        "detected": mean(rows, "drift_detected"),
        "recovery_triggered": mean(rows, "recovery_triggered"),
        "detection_delay": mean(rows, "detection_delay"),
        "recovery_steps": mean(rows, "recovery_steps_used"),
        "false_intervention": false_intervention,
        "class_correct": class_correct,
    }


def main() -> None:
    args = parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)

    summaries: dict[tuple[str, str], dict] = {}
    for failure_mode in FAILURE_MODES:
        for controller in CONTROLLERS:
            path = args.runs_dir / f"{args.prefix}_{failure_mode}_{controller}.csv"
            if path.exists():
                summaries[(failure_mode, controller)] = summarize(path, failure_mode)

    lines = [
        "# Failure-Recovery Suite Report",
        "",
        "## Aggregate Table",
        "",
        "| Failure Mode | Controller | Success | Budget Exhausted | Cost | Final Distance | Detected | Recovery Triggered | Detection Delay | False Trigger | Class Correct |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for failure_mode in FAILURE_MODES:
        for controller in CONTROLLERS:
            row = summaries.get((failure_mode, controller))
            if row is None:
                continue
            lines.append(
                f"| {failure_mode} | {controller} | {fmt(row['success'])} | {fmt(row['budget_exhausted'])} | "
                f"{fmt(row['cost'])} | {fmt(row['final_distance'])} | {fmt(row['detected'])} | "
                f"{fmt(row['recovery_triggered'])} | {fmt(row['detection_delay'])} | "
                f"{fmt_optional(row['false_intervention'])} | {fmt_optional(row['class_correct'])} |"
            )

    lines.extend(
        [
            "",
            "## Key Readings",
            "",
            "- `none` estimates unnecessary intervention behavior under nominal execution.",
            "- `state_target_bias` and `state_dropout` probe state-estimation reliability.",
            "- `execution_slip` probes action-outcome reliability at the execution layer.",
            "- `Class Correct` reports whether the runtime diagnosis matches the injected failure type.",
            "- `False Trigger` reports unnecessary intervention under nominal execution.",
            "- `monitor_recovery` is a lightweight runtime layer, not a replacement for the learned policy.",
            "",
        ]
    )
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"report={args.out}")


if __name__ == "__main__":
    main()
