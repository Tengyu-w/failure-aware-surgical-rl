from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path

import numpy as np


FAILURE_MODES = ("none", "state_target_bias", "state_dropout", "execution_slip")
CONTROLLERS = ("policy_only", "monitor_recovery")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", default="nav_multiseed_failure")
    parser.add_argument("--runs-dir", type=Path, default=Path("runs"))
    parser.add_argument("--out", type=Path, default=Path("reports") / "navigation_multiseed_failure_report.md")
    return parser.parse_args()


def read_rows(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def mean(rows: list[dict], key: str) -> float:
    values = np.array([float(row.get(key, 0.0) or 0.0) for row in rows], dtype=np.float64)
    if np.isnan(values).all():
        return 0.0
    return float(np.nanmean(values))


def summarize_csv(path: Path) -> dict:
    rows = read_rows(path)
    return {
        "episodes": len(rows),
        "success": mean(rows, "success"),
        "budget_exhausted": mean(rows, "budget_exhausted"),
        "cost": mean(rows, "cumulative_cost"),
        "final_distance": mean(rows, "final_distance"),
        "detected": mean(rows, "failure_detected") if "failure_detected" in rows[0] else mean(rows, "drift_detected"),
        "recovery_triggered": mean(rows, "recovery_triggered"),
        "false_intervention": mean(rows, "false_intervention"),
        "class_correct": mean(rows, "failure_class_correct"),
        "detection_delay": mean(rows, "detection_delay"),
    }


def parse_file(path: Path, prefix: str) -> tuple[int, str, str] | None:
    match = re.fullmatch(
        rf"{re.escape(prefix)}_modelseed(?P<seed>\d+)_(?P<failure>.+)_(?P<controller>policy_only|monitor_recovery)\.csv",
        path.name,
    )
    if not match:
        return None
    return int(match.group("seed")), match.group("failure"), match.group("controller")


def fmt(value: float) -> str:
    return f"{value:.3f}"


def aggregate(values: list[float]) -> tuple[float, float]:
    arr = np.array(values, dtype=np.float64)
    return float(np.mean(arr)), float(np.std(arr, ddof=0))


def main() -> None:
    args = parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)

    seed_rows: dict[tuple[int, str, str], dict] = {}
    for path in args.runs_dir.glob(f"{args.prefix}_modelseed*.csv"):
        parsed = parse_file(path, args.prefix)
        if parsed is None:
            continue
        seed, failure, controller = parsed
        seed_rows[(seed, failure, controller)] = summarize_csv(path)

    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for (_seed, failure, controller), row in seed_rows.items():
        grouped[(failure, controller)].append(row)

    lines = [
        "# Navigation Multi-Seed Failure-Recovery Report",
        "",
        "## Takeaway",
        "",
        (
            "This report evaluates the navigation failure-recovery suite across multiple trained PPO seeds, "
            "rather than relying on a single policy checkpoint. It strengthens the evidence for the runtime "
            "monitor/recovery layer while still remaining an abstract proxy experiment."
        ),
        "",
        "## Aggregate Across Model Seeds",
        "",
        "| Failure Mode | Controller | Model Seeds | Episodes/Seed | Success Mean | Success Std | Recovery Trigger | False Trigger | Class Correct | Detection Delay |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for failure in FAILURE_MODES:
        for controller in CONTROLLERS:
            rows = grouped.get((failure, controller), [])
            if not rows:
                continue
            success_mean, success_std = aggregate([row["success"] for row in rows])
            recovery_mean, _ = aggregate([row["recovery_triggered"] for row in rows])
            false_mean, _ = aggregate([row["false_intervention"] for row in rows])
            class_mean, _ = aggregate([row["class_correct"] for row in rows])
            delay_mean, _ = aggregate([row["detection_delay"] for row in rows])
            episodes = int(rows[0]["episodes"])
            lines.append(
                f"| {failure} | {controller} | {len(rows)} | {episodes} | {fmt(success_mean)} | {fmt(success_std)} | "
                f"{fmt(recovery_mean)} | {fmt(false_mean)} | {fmt(class_mean)} | {fmt(delay_mean)} |"
            )

    lines.extend(
        [
            "",
            "## Reading Notes",
            "",
            "- Model seeds refer to independently trained navigation PPO checkpoints.",
            "- Episodes/Seed is intentionally modest for a fast multi-seed reliability pass.",
            "- Manipulation PPO multi-seed training is not included here yet; current manipulation failure results are controller/proxy evaluations.",
            "",
            "## Next Breadth Step",
            "",
            "After this multi-seed navigation pass, the next useful breadth expansion is to add more surgical proxy task families, then rerun the same failure taxonomy and risk reports over those presets.",
            "",
        ]
    )
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"report={args.out}")


if __name__ == "__main__":
    main()
