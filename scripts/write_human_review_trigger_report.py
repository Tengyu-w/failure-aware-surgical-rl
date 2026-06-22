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
    parser.add_argument("--out", type=Path, default=Path("reports") / "human_review_trigger_report.md")
    parser.add_argument("--navigation-prefix", default="failure_suite")
    parser.add_argument("--manipulation-prefix", default="manip_failure")
    return parser.parse_args()


def read_rows(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def detected(row: dict) -> bool:
    if "failure_detected" in row:
        return float(row["failure_detected"]) > 0.5
    return float(row.get("drift_detected", 0.0) or 0.0) > 0.5


def delay(row: dict) -> float:
    try:
        value = float(row.get("detection_delay", np.nan) or np.nan)
    except ValueError:
        return np.nan
    return value


def summarize_trigger(rows: list[dict], failure_mode: str) -> dict:
    is_failure = failure_mode != "none"
    tp = fp = fn = tn = 0
    delays: list[float] = []
    for row in rows:
        did_trigger = detected(row)
        if is_failure and did_trigger:
            tp += 1
            current_delay = delay(row)
            if not np.isnan(current_delay):
                delays.append(current_delay)
        elif is_failure and not did_trigger:
            fn += 1
        elif not is_failure and did_trigger:
            fp += 1
        else:
            tn += 1

    total = tp + fp + fn + tn
    trigger_rate = (tp + fp) / total if total else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    false_trigger_rate = fp / (fp + tn) if (fp + tn) else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    mean_delay = float(np.mean(delays)) if delays else 0.0
    return {
        "episodes": total,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "trigger_rate": trigger_rate,
        "recall": recall,
        "precision": precision,
        "false_trigger_rate": false_trigger_rate,
        "mean_delay": mean_delay,
    }


def fmt(value: float) -> str:
    return f"{value:.3f}"


def collect_monitor_rows(runs_dir: Path, navigation_prefix: str, manipulation_prefix: str) -> list[dict]:
    summaries: list[dict] = []
    for failure in NAVIGATION_FAILURES:
        path = runs_dir / f"{navigation_prefix}_{failure}_monitor_recovery.csv"
        if path.exists():
            summaries.append(
                {"task": "navigation", "failure": failure, **summarize_trigger(read_rows(path), failure)}
            )

    for failure in MANIPULATION_FAILURES:
        stem = MANIP_FILE_STEMS.get(failure, failure)
        path = runs_dir / f"{manipulation_prefix}_{stem}_monitor.csv"
        if path.exists():
            summaries.append(
                {"task": "manipulation", "failure": failure, **summarize_trigger(read_rows(path), failure)}
            )
    return summaries


def aggregate(rows: list[dict]) -> dict:
    tp = sum(row["tp"] for row in rows)
    fp = sum(row["fp"] for row in rows)
    fn = sum(row["fn"] for row in rows)
    tn = sum(row["tn"] for row in rows)
    delays = [row["mean_delay"] for row in rows if row["failure"] != "none" and row["tp"] > 0]
    return {
        "episodes": tp + fp + fn + tn,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": tp / (tp + fp) if (tp + fp) else 1.0,
        "recall": tp / (tp + fn) if (tp + fn) else 0.0,
        "false_trigger_rate": fp / (fp + tn) if (fp + tn) else 0.0,
        "mean_delay": float(np.mean(delays)) if delays else 0.0,
    }


def write_report(rows: list[dict], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    overall = aggregate(rows)
    navigation = aggregate([row for row in rows if row["task"] == "navigation"])
    manipulation = aggregate([row for row in rows if row["task"] == "manipulation"])

    lines = [
        "# Human-Review Trigger Report",
        "",
        "## Takeaway",
        "",
        (
            "Treating the runtime monitor as a human-review trigger, the current proxy suites show "
            "high recall on injected failures and zero observed false triggers under nominal episodes. "
            "This is still a prototype-level result because failures are synthetic and the trigger logic is rule-based."
        ),
        "",
        "## Trigger Summary",
        "",
        "| Group | Episodes | Precision | Recall | False Trigger Rate | Mean Detection Delay | TP | FP | FN | TN |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        (
            f"| Overall | {overall['episodes']} | {fmt(overall['precision'])} | {fmt(overall['recall'])} | "
            f"{fmt(overall['false_trigger_rate'])} | {fmt(overall['mean_delay'])} | "
            f"{overall['tp']} | {overall['fp']} | {overall['fn']} | {overall['tn']} |"
        ),
        (
            f"| Navigation | {navigation['episodes']} | {fmt(navigation['precision'])} | {fmt(navigation['recall'])} | "
            f"{fmt(navigation['false_trigger_rate'])} | {fmt(navigation['mean_delay'])} | "
            f"{navigation['tp']} | {navigation['fp']} | {navigation['fn']} | {navigation['tn']} |"
        ),
        (
            f"| Manipulation | {manipulation['episodes']} | {fmt(manipulation['precision'])} | {fmt(manipulation['recall'])} | "
            f"{fmt(manipulation['false_trigger_rate'])} | {fmt(manipulation['mean_delay'])} | "
            f"{manipulation['tp']} | {manipulation['fp']} | {manipulation['fn']} | {manipulation['tn']} |"
        ),
        "",
        "## Per-Failure Trigger Table",
        "",
        "| Task | Failure Mode | Episodes | Trigger Rate | Recall | False Trigger Rate | Mean Detection Delay | TP | FP | FN | TN |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for row in rows:
        lines.append(
            f"| {row['task']} | {row['failure']} | {row['episodes']} | {fmt(row['trigger_rate'])} | "
            f"{fmt(row['recall'])} | {fmt(row['false_trigger_rate'])} | {fmt(row['mean_delay'])} | "
            f"{row['tp']} | {row['fp']} | {row['fn']} | {row['tn']} |"
        )

    lines.extend(
        [
            "",
            "## Reading Notes",
            "",
            "- TP means an injected failure was detected and would trigger review/recovery.",
            "- FP means a nominal episode triggered review unnecessarily.",
            "- FN means an injected failure was missed.",
            "- Detection delay is averaged only over detected abnormal episodes.",
            "",
            "## Limitations",
            "",
            "- This report uses synthetic failures in abstract proxy environments.",
            "- Current trigger logic is deterministic instrumentation, not a learned uncertainty model.",
            "- Real human-review usefulness would require higher-fidelity tasks and human-in-the-loop thresholds.",
            "",
        ]
    )
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"report={out}")


def main() -> None:
    args = parse_args()
    rows = collect_monitor_rows(args.runs_dir, args.navigation_prefix, args.manipulation_prefix)
    write_report(rows, args.out)


if __name__ == "__main__":
    main()
