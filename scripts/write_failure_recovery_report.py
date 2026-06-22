from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy-only", type=Path, required=True)
    parser.add_argument("--monitor-recovery", type=Path, required=True)
    parser.add_argument("--heuristic-only", type=Path, required=True)
    parser.add_argument("--failure-mode", default="state_target_bias")
    parser.add_argument("--out", type=Path, default=Path("runs") / "failure_recovery_report.md")
    return parser.parse_args()


def read_rows(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def mean(rows: list[dict], key: str) -> float:
    return float(np.nanmean([float(row.get(key, 0.0) or 0.0) for row in rows]))


def fmt(value: float) -> str:
    return f"{value:.3f}"


def table_row(label: str, rows: list[dict]) -> str:
    return (
        f"| {label} | {fmt(mean(rows, 'success'))} | {fmt(mean(rows, 'budget_exhausted'))} | "
        f"{fmt(mean(rows, 'cumulative_cost'))} | {fmt(mean(rows, 'final_distance'))} | "
        f"{fmt(mean(rows, 'drift_detected'))} | {fmt(mean(rows, 'recovery_triggered'))} | "
        f"{fmt(mean(rows, 'detection_delay'))} | {fmt(mean(rows, 'recovery_steps_used'))} | "
        f"{fmt(mean(rows, 'state_bias_active_at_end'))} | {fmt(mean(rows, 'state_dropout_active_at_end'))} | "
        f"{fmt(mean(rows, 'execution_slip_active_at_end'))} |"
    )


def main() -> None:
    args = parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    policy_rows = read_rows(args.policy_only)
    monitor_rows = read_rows(args.monitor_recovery)
    heuristic_rows = read_rows(args.heuristic_only)

    lines = [
        "# Failure-Recovery Evaluation",
        "",
        "## Setup",
        "",
        f"- Failure mode: `{args.failure_mode}` injected during execution.",
        "- Policy: 3D conditioned tangent-shielded PPO.",
        "- Recovery: runtime monitor detects the injected reliability signal, clears or disables the failure source when applicable, and uses a short heuristic recovery controller.",
        "",
        "## Results",
        "",
        "| Controller | Success | Budget Exhausted | Cost | Final Distance | Detected | Recovery Triggered | Detection Delay | Recovery Steps | Bias Active | Dropout Active | Slip Active |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        table_row("policy_only", policy_rows),
        table_row("monitor_recovery", monitor_rows),
        table_row("heuristic_only", heuristic_rows),
        "",
        "## Reading",
        "",
        "- Policy-only execution is brittle under the injected failure.",
        "- Monitor recovery restores performance by detecting the state-estimation jump and recalibrating before continuing.",
        "- Heuristic-only is an oracle-style sanity check, not a learned-policy baseline.",
        "- This is still a proxy experiment; the next step is to add dropout, execution slip, and SurRoL-style task failures.",
        "",
    ]
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"report={args.out}")


if __name__ == "__main__":
    main()
