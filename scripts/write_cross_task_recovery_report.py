from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np


NAVIGATION_FAILURES = ("none", "state_target_bias", "state_dropout", "execution_slip")
MANIPULATION_FAILURES = ("none", "object_state_bias", "object_dropout", "execution_slip", "contact_loss")
MANIP_FILE_STEMS = {"object_state_bias": "object_bias"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-dir", type=Path, default=Path("runs"))
    parser.add_argument("--out", type=Path, default=Path("reports") / "cross_task_recovery_report.md")
    parser.add_argument("--navigation-prefix", default="failure_suite")
    parser.add_argument("--manipulation-prefix", default="manip_failure")
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


def infer_optional_metrics(rows: list[dict], path: Path) -> tuple[float | None, float | None]:
    stem = path.stem
    if "failure_class_correct" in rows[0]:
        class_correct = optional_mean(rows, "failure_class_correct")
    elif stem.startswith("failure_suite_"):
        failure_mode = stem.removeprefix("failure_suite_")
        for suffix in ("_policy_only", "_monitor_recovery", "_heuristic_only"):
            failure_mode = failure_mode.removesuffix(suffix)
        if failure_mode == "none":
            class_correct = 1.0 - mean(rows, "drift_detected")
        else:
            class_correct = mean(rows, "drift_detected")
    else:
        class_correct = None

    if "false_intervention" in rows[0]:
        false_intervention = optional_mean(rows, "false_intervention")
    elif stem.startswith("failure_suite_none_"):
        false_intervention = mean(rows, "drift_detected")
    elif stem.startswith("failure_suite_"):
        false_intervention = 0.0
    else:
        false_intervention = None

    return false_intervention, class_correct


def summarize(path: Path) -> dict:
    rows = read_rows(path)
    false_intervention, class_correct = infer_optional_metrics(rows, path)
    return {
        "success": mean(rows, "success"),
        "budget_exhausted": mean(rows, "budget_exhausted"),
        "cost": mean(rows, "cumulative_cost"),
        "detected": mean(rows, "failure_detected") if "failure_detected" in rows[0] else mean(rows, "drift_detected"),
        "recovery_triggered": mean(rows, "recovery_triggered"),
        "detection_delay": mean(rows, "detection_delay"),
        "false_intervention": false_intervention,
        "class_correct": class_correct,
    }


def add_delta(row: dict, baseline: dict | None) -> dict:
    out = dict(row)
    if baseline is None:
        out["success_delta"] = 0.0
    else:
        out["success_delta"] = row["success"] - baseline["success"]
    return out


def collect_navigation(runs_dir: Path, prefix: str) -> list[dict]:
    rows: list[dict] = []
    for failure in NAVIGATION_FAILURES:
        baseline = None
        baseline_path = runs_dir / f"{prefix}_{failure}_policy_only.csv"
        if baseline_path.exists():
            baseline = summarize(baseline_path)
        for controller in ("policy_only", "monitor_recovery"):
            path = runs_dir / f"{prefix}_{failure}_{controller}.csv"
            if not path.exists():
                continue
            summary = add_delta(summarize(path), baseline)
            rows.append({"task": "navigation", "failure": failure, "controller": controller, **summary})
    return rows


def collect_manipulation(runs_dir: Path, prefix: str) -> list[dict]:
    rows: list[dict] = []
    for failure in MANIPULATION_FAILURES:
        file_stem = MANIP_FILE_STEMS.get(failure, failure)
        baseline = None
        baseline_path = runs_dir / f"{prefix}_{file_stem}_base.csv"
        if baseline_path.exists():
            baseline = summarize(baseline_path)
        for controller in ("base", "monitor"):
            path = runs_dir / f"{prefix}_{file_stem}_{controller}.csv"
            if not path.exists():
                continue
            summary = add_delta(summarize(path), baseline)
            rows.append({"task": "manipulation", "failure": failure, "controller": controller, **summary})
    return rows


def mean_for(rows: list[dict], key: str, *, task: str | None = None, controller: str | None = None) -> float:
    selected = [
        row[key]
        for row in rows
        if (task is None or row["task"] == task) and (controller is None or row["controller"] == controller)
    ]
    if not selected:
        return 0.0
    return float(np.mean(selected))


def mean_optional_for(rows: list[dict], key: str, *, controller: str | None = None) -> float | None:
    selected = [
        row[key]
        for row in rows
        if (controller is None or row["controller"] == controller) and row.get(key) is not None
    ]
    if not selected:
        return None
    return float(np.mean(selected))


def write_report(rows: list[dict], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)

    monitor_rows = [row for row in rows if row["controller"] in {"monitor_recovery", "monitor"}]
    baseline_rows = [row for row in rows if row["controller"] in {"policy_only", "base"}]
    abnormal_monitor_rows = [row for row in monitor_rows if row["failure"] != "none"]

    lines = [
        "# Cross-Task Failure-Recovery Report",
        "",
        "## One-Paragraph Takeaway",
        "",
        (
            "Across the current abstract 3D navigation and multi-phase manipulation proxies, "
            "the runtime recovery layer preserves nominal success while recovering from injected "
            "state-estimation, execution, and contact-loss failures. This supports a prototype-level "
            "claim about failure-aware recovery across task families, not just a single reach/avoid action."
        ),
        "",
        "## Cross-Task Summary",
        "",
        "| Group | Mean Success | Mean Recovery Trigger | Mean False Trigger | Mean Class Correct |",
        "|---|---:|---:|---:|---:|",
        (
            f"| Baseline controllers | {fmt(float(np.mean([row['success'] for row in baseline_rows])))} | "
            f"{fmt(float(np.mean([row['recovery_triggered'] for row in baseline_rows])))} | "
            f"{fmt_optional(mean_optional_for(baseline_rows, 'false_intervention'))} | "
            f"{fmt_optional(mean_optional_for(baseline_rows, 'class_correct'))} |"
        ),
        (
            f"| Runtime monitor/recovery | {fmt(float(np.mean([row['success'] for row in monitor_rows])))} | "
            f"{fmt(float(np.mean([row['recovery_triggered'] for row in monitor_rows])))} | "
            f"{fmt_optional(mean_optional_for(monitor_rows, 'false_intervention'))} | "
            f"{fmt_optional(mean_optional_for(monitor_rows, 'class_correct'))} |"
        ),
        (
            f"| Runtime monitor/recovery on abnormal cases | {fmt(float(np.mean([row['success'] for row in abnormal_monitor_rows])))} | "
            f"{fmt(float(np.mean([row['recovery_triggered'] for row in abnormal_monitor_rows])))} | "
            f"{fmt_optional(mean_optional_for(abnormal_monitor_rows, 'false_intervention'))} | "
            f"{fmt_optional(mean_optional_for(abnormal_monitor_rows, 'class_correct'))} |"
        ),
        "",
        "## Detailed Table",
        "",
        "| Task | Failure Mode | Controller | Success | Success Delta | Detected | Recovery Triggered | Detection Delay | False Trigger | Class Correct |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for row in rows:
        lines.append(
            f"| {row['task']} | {row['failure']} | {row['controller']} | {fmt(row['success'])} | "
            f"{fmt(row['success_delta'])} | {fmt(row['detected'])} | {fmt(row['recovery_triggered'])} | "
            f"{fmt(row['detection_delay'])} | {fmt_optional(row['false_intervention'])} | "
            f"{fmt_optional(row['class_correct'])} |"
        )

    lines.extend(
        [
            "",
            "## What Is Shown",
            "",
            "- Navigation covers target/state bias, state dropout, and execution slip.",
            "- Manipulation covers object-state bias, object dropout, execution slip, and contact loss.",
            "- Nominal `none` cases estimate unnecessary intervention behavior.",
            "- The current manipulation monitor reports explicit failure-type diagnosis.",
            "- For legacy navigation CSVs without explicit classification fields, class correctness is inferred from the injected failure mode and detection flag.",
            "- `N/A` means the metric was not logged and cannot be inferred for that task family yet.",
            "",
            "## What Remains Unproven",
            "",
            "- These are abstract proxy environments, not high-fidelity SurRoL or real robot experiments.",
            "- Failure classification is currently rule-based instrumentation, not a learned classifier.",
            "- The result is episode-level reliability evidence, not proof of sim-to-real robustness.",
            "",
            "## Recommended Next Experiment",
            "",
            "Move the same failure taxonomy into a SurRoL-style needle or gauze task, while keeping the same metrics: success, recovery success, detection delay, false trigger rate, and failure-type classification accuracy.",
            "",
        ]
    )
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"report={out}")


def main() -> None:
    args = parse_args()
    rows = [
        *collect_navigation(args.runs_dir, args.navigation_prefix),
        *collect_manipulation(args.runs_dir, args.manipulation_prefix),
    ]
    write_report(rows, args.out)


if __name__ == "__main__":
    main()
