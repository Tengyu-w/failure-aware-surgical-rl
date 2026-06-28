from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

INPUTS = [
    {
        "task": "NeedlePick",
        "severity": "low",
        "perception_bias_scale": 0.25,
        "depth_scale_error": 0.03,
        "near_target_drift_scale": 0.50,
        "path": ROOT / "runs" / "surrol_needlepick_severity_low_w16_5seed.csv",
    },
    {
        "task": "NeedlePick",
        "severity": "medium",
        "perception_bias_scale": 1.00,
        "depth_scale_error": 0.12,
        "near_target_drift_scale": 1.00,
        "path": ROOT / "runs" / "surrol_needlepick_perception_drift_w16_5seed.csv",
    },
    {
        "task": "NeedlePick",
        "severity": "high",
        "perception_bias_scale": 1.50,
        "depth_scale_error": 0.18,
        "near_target_drift_scale": 1.50,
        "path": ROOT / "runs" / "surrol_needlepick_severity_high_w16_5seed.csv",
    },
    {
        "task": "GauzeRetrieve",
        "severity": "low",
        "perception_bias_scale": 0.25,
        "depth_scale_error": 0.03,
        "near_target_drift_scale": 0.50,
        "path": ROOT / "runs" / "surrol_gauzeretrieve_severity_low_w16_5seed.csv",
    },
    {
        "task": "GauzeRetrieve",
        "severity": "medium",
        "perception_bias_scale": 1.00,
        "depth_scale_error": 0.12,
        "near_target_drift_scale": 1.00,
        "path": ROOT / "runs" / "surrol_gauzeretrieve_perception_drift_w16_5seed.csv",
    },
    {
        "task": "GauzeRetrieve",
        "severity": "high",
        "perception_bias_scale": 1.50,
        "depth_scale_error": 0.18,
        "near_target_drift_scale": 1.50,
        "path": ROOT / "runs" / "surrol_gauzeretrieve_severity_high_w16_5seed.csv",
    },
]

SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2}
FAILURE_ORDER = ["perception_bias", "depth_scale_error", "near_target_drift"]


def fmt(value: float) -> str:
    return f"{float(value):.3f}"


def load() -> pd.DataFrame:
    frames = []
    for item in INPUTS:
        if not item["path"].exists():
            raise FileNotFoundError(item["path"])
        df = pd.read_csv(item["path"])
        df["task"] = item["task"]
        df["severity"] = item["severity"]
        df["severity_rank"] = SEVERITY_ORDER[item["severity"]]
        df["perception_bias_scale"] = item["perception_bias_scale"]
        df["depth_scale_error"] = item["depth_scale_error"]
        df["near_target_drift_scale"] = item["near_target_drift_scale"]
        df["source_csv"] = str(item["path"].relative_to(ROOT))
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        df.groupby(
            [
                "task",
                "severity",
                "severity_rank",
                "failure",
                "controller",
                "perception_bias_scale",
                "depth_scale_error",
                "near_target_drift_scale",
            ],
            as_index=False,
        )
        .agg(
            episodes=("success", "size"),
            seeds=("seed", "nunique"),
            success_mean=("success", "mean"),
            final_distance_mean=("final_distance", "mean"),
            triggers_mean=("monitor_triggers", "mean"),
            override_rate_mean=("recovery_override_rate", "mean"),
            steps_mean=("steps", "mean"),
        )
        .sort_values(["task", "failure", "severity_rank", "controller"])
    )
    return summary


def paired(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (task, severity, failure), group in summary.groupby(["task", "severity", "failure"], dropna=False):
        if failure == "none":
            continue
        by_controller = {row["controller"]: row for _, row in group.iterrows()}
        perturbed = by_controller.get("perturbed")
        monitor = by_controller.get("monitor_corrected")
        clean = by_controller.get("clean")
        if perturbed is None or monitor is None:
            continue
        rows.append(
            {
                "task": task,
                "severity": severity,
                "severity_rank": SEVERITY_ORDER[severity],
                "failure": failure,
                "seeds": int(monitor["seeds"]),
                "clean_success": clean["success_mean"] if clean is not None else pd.NA,
                "perturbed_success": perturbed["success_mean"],
                "monitor_success": monitor["success_mean"],
                "perturbed_final_distance": perturbed["final_distance_mean"],
                "monitor_final_distance": monitor["final_distance_mean"],
                "mean_triggers": monitor["triggers_mean"],
                "override_rate": monitor["override_rate_mean"],
            }
        )
    return pd.DataFrame(rows).sort_values(["failure", "task", "severity_rank"])


def suggested_route(row: pd.Series) -> str:
    failure = str(row["failure"])
    monitor_success = float(row["monitor_success"])
    triggers = float(row["mean_triggers"])
    if failure in {"perception_bias", "depth_scale_error"}:
        if monitor_success < 0.8:
            return "human_review / re-estimate state"
        return "auto_execute_or_review_by_threshold"
    if failure == "near_target_drift":
        if monitor_success >= 0.8 and triggers > 0:
            return "auto_recovery"
        if monitor_success >= 0.8:
            return "auto_execute"
        return "threshold_needs_calibration"
    return "case_by_case"


def plot(paired_df: pd.DataFrame, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for task, task_df in paired_df.groupby("task"):
        fig, axes = plt.subplots(1, 3, figsize=(12.8, 3.8), sharey=True)
        for ax, failure in zip(axes, FAILURE_ORDER):
            group = task_df[task_df["failure"] == failure].sort_values("severity_rank")
            ax.plot(group["severity"], group["perturbed_success"], marker="o", label="perturbed")
            ax.plot(group["severity"], group["monitor_success"], marker="o", label="monitor")
            ax.set_title(failure)
            ax.set_ylim(-0.05, 1.05)
            ax.set_xlabel("Severity")
            ax.grid(alpha=0.3)
        axes[0].set_ylabel("Success rate")
        axes[-1].legend(frameon=False, loc="lower right")
        fig.suptitle(f"{task}: Severity Sweep")
        fig.tight_layout()
        fig.savefig(out_dir / f"{task.lower()}_severity_sweep.png", dpi=200)
        plt.close(fig)


def write_report(paired_df: pd.DataFrame, out: Path) -> None:
    lines = [
        "# SurRoL Severity Sweep For Visual-State Error And Near-Target Drift",
        "",
        "## Takeaway",
        "",
        (
            "This sweep tests low, medium, and high severity levels for "
            "perception bias, depth-scale error, and near-target drift on "
            "NeedlePick and GauzeRetrieve. It supports a route boundary: "
            "visual/depth state errors that cause task failure should be routed "
            "to state re-estimation or review, while recoverable near-target "
            "drift can be handled by automatic monitor recovery. Low-severity "
            "NeedlePick drift still has missed triggers, indicating that the "
            "monitor threshold needs calibration."
        ),
        "",
        "## Paired Severity Results",
        "",
        "| Task | Failure | Severity | Seeds | Perturbed | Monitor | Triggers | Perturbed Dist | Monitor Dist | Suggested Route |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for _, row in paired_df.iterrows():
        lines.append(
            f"| {row['task']} | {row['failure']} | {row['severity']} | {int(row['seeds'])} | "
            f"{fmt(row['perturbed_success'])} | {fmt(row['monitor_success'])} | {fmt(row['mean_triggers'])} | "
            f"{fmt(row['perturbed_final_distance'])} | {fmt(row['monitor_final_distance'])} | {suggested_route(row)} |"
        )

    lines.extend(
        [
            "",
            "## Boundary Interpretation",
            "",
            "- `perception_bias`: GauzeRetrieve tolerates low severity but fails at medium/high severity; NeedlePick already shows failures at low severity and 0/5 success at medium/high severity.",
            "- `depth_scale_error`: both tasks are fragile even at low severity, suggesting that depth/3D-state error should be high-priority review evidence.",
            "- `near_target_drift`: medium/high drift can be recovered to 5/5 by the monitor; low drift succeeds naturally on GauzeRetrieve but has missed triggers on NeedlePick, so endpoint-error monitoring or threshold calibration is needed.",
            "",
            "## Relation To The Project",
            "",
            "This experiment does not replace the mainstream surgical robot workflow. It adds a reliability boundary at the handoff between visual-state estimation and final control: reversible drift can enter automatic recovery, while unreliable visual/depth state should enter review or re-estimation.",
            "",
            "## Limitations",
            "",
            "- Severity is a state-space proxy, not a real FastSAM/IGEV image error.",
            "- Each task/severity condition uses 5 seeds, so the result remains lightweight prototype evidence.",
            "- The monitor threshold is rule-based; missed-trigger cases should be used for calibration.",
            "",
            "## Outputs",
            "",
            "- `reports/tables/surrol_severity_sweep_summary.csv`",
            "- `reports/tables/surrol_severity_sweep_paired.csv`",
            "- `reports/figures/surrol_severity_sweep/needlepick_severity_sweep.png`",
            "- `reports/figures/surrol_severity_sweep/gauzeretrieve_severity_sweep.png`",
        ]
    )
    out.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    table_dir = ROOT / "reports" / "tables"
    figure_dir = ROOT / "reports" / "figures" / "surrol_severity_sweep"
    table_dir.mkdir(parents=True, exist_ok=True)
    df = load()
    summary = summarize(df)
    paired_df = paired(summary)
    summary.to_csv(table_dir / "surrol_severity_sweep_summary.csv", index=False)
    paired_df.to_csv(table_dir / "surrol_severity_sweep_paired.csv", index=False)
    plot(paired_df, figure_dir)
    report_path = ROOT / "reports" / "surrol_severity_sweep.md"
    write_report(paired_df, report_path)
    print(f"summary={table_dir / 'surrol_severity_sweep_summary.csv'}")
    print(f"paired={table_dir / 'surrol_severity_sweep_paired.csv'}")
    print(f"figures={figure_dir}")
    print(f"report={report_path}")


if __name__ == "__main__":
    main()
