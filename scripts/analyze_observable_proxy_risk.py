from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUTS = [
    ("NeedlePick", ROOT / "runs" / "surrol_needlepick_observable_phase_jaw_stuck_w32_10seed_steps.csv"),
    ("GauzeRetrieve", ROOT / "runs" / "surrol_gauzeretrieve_observable_phase_jaw_stuck_w32_10seed_steps.csv"),
]
THRESHOLDS = [1.5, 2.0, 2.5, 3.0, 3.5]


def add_scores(seq: pd.DataFrame) -> pd.DataFrame:
    seq = seq.sort_values("step").copy()
    initial_distance = float(seq["distance"].iloc[0])
    seq["min_distance_so_far"] = seq["distance"].cummin()
    seq["close_score"] = (seq["close_command_count"] >= 4).astype(float)
    seq["stall_score"] = np.clip(seq["stalled_count"] / 8.0, 0.0, 1.0)
    seq["far_score"] = (
        (seq["distance"] > 0.08) | (seq["distance"] > initial_distance * 0.55)
    ).astype(float)
    seq["no_improve_score"] = ((initial_distance - seq["min_distance_so_far"]) < 0.035).astype(float)
    seq["observable_risk_score"] = (
        seq["close_score"] + seq["stall_score"] + seq["far_score"] + seq["no_improve_score"]
    )
    return seq


def load_scored_steps() -> pd.DataFrame:
    frames = []
    for task, path in INPUTS:
        df = pd.read_csv(path)
        df["task"] = task
        groups = []
        for _, seq in df.groupby(["task", "failure", "controller", "seed", "episode"], dropna=False):
            groups.append(add_scores(seq))
        frames.append(pd.concat(groups, ignore_index=True))
    return pd.concat(frames, ignore_index=True)


def first_alarm(seq: pd.DataFrame, threshold: float) -> float:
    candidates = seq[
        (seq["step"] >= 30)
        & (seq["close_command_count"] >= 4)
        & (seq["observable_risk_score"] >= threshold)
    ]
    if candidates.empty:
        return np.nan
    return float(candidates["step"].iloc[0])


def sweep_thresholds(scored: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for threshold in THRESHOLDS:
        for (task, failure, controller), group in scored.groupby(["task", "failure", "controller"], dropna=False):
            alarms = []
            episodes = 0
            for _, seq in group.groupby(["seed", "episode"], dropna=False):
                episodes += 1
                alarms.append(first_alarm(seq, threshold))
            alarms_arr = np.asarray(alarms, dtype=float)
            valid = ~np.isnan(alarms_arr)
            rows.append(
                {
                    "threshold": threshold,
                    "task": task,
                    "failure": failure,
                    "controller": controller,
                    "episodes": episodes,
                    "alarm_rate": float(valid.mean()) if episodes else np.nan,
                    "mean_alarm_step": float(np.nanmean(alarms_arr)) if valid.any() else np.nan,
                    "median_alarm_step": float(np.nanmedian(alarms_arr)) if valid.any() else np.nan,
                }
            )
    return pd.DataFrame(rows)


def plot_sweep(sweep: pd.DataFrame, out_dir: Path) -> None:
    fault = sweep[(sweep["failure"] == "jaw_stuck_open") & (sweep["controller"] == "perturbed")]
    nominal = sweep[(sweep["failure"] == "none") & (sweep["controller"] == "monitor_corrected")]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    for task, group in fault.groupby("task"):
        axes[0].plot(group["threshold"], group["alarm_rate"], marker="o", label=task)
        axes[1].plot(group["threshold"], group["mean_alarm_step"], marker="o", label=f"{task} fault")
    for task, group in nominal.groupby("task"):
        axes[0].plot(group["threshold"], group["alarm_rate"], marker="x", linestyle="--", label=f"{task} nominal")

    axes[0].set_title("Alarm Rate")
    axes[0].set_xlabel("Risk threshold")
    axes[0].set_ylabel("Episode alarm rate")
    axes[0].set_ylim(-0.05, 1.05)
    axes[0].grid(alpha=0.35)
    axes[0].legend(frameon=False, fontsize=9)

    axes[1].set_title("Fault Alarm Step")
    axes[1].set_xlabel("Risk threshold")
    axes[1].set_ylabel("Mean first alarm step")
    axes[1].grid(alpha=0.35)
    axes[1].legend(frameon=False, fontsize=9)

    fig.suptitle("Observable Proxy Risk Threshold Sweep (10 seeds)", fontsize=15)
    fig.tight_layout()
    fig.savefig(out_dir / "observable_proxy_threshold_sweep.png", dpi=200)
    plt.close(fig)


def write_report(sweep: pd.DataFrame, scored: pd.DataFrame, out_path: Path) -> None:
    selected = sweep[
        (sweep["threshold"] == 3.0)
        & (sweep["failure"].isin(["jaw_stuck_open", "none"]))
        & (sweep["controller"].isin(["perturbed", "monitor_corrected"]))
    ].copy()

    lines = [
        "# Observable Proxy Risk Sweep",
        "",
        "## Takeaway",
        "",
        (
            "Using the existing 10-seed step logs, an offline observable risk score detects silent jaw-stuck "
            "faults in both NeedlePick and GauzeRetrieve. At threshold 3.0, fault alarm rate is 10/10 for both "
            "tasks, while nominal monitor-corrected runs also alarm late because the current proxy treats normal "
            "pre-grasp stalls as risk. This means the proxy is useful but not yet well calibrated."
        ),
        "",
        "## Risk Score",
        "",
        "```text",
        "risk_score = close_score + stall_score + far_score + no_improve_score",
        "```",
        "",
        "- `close_score`: close command count >= 4.",
        "- `stall_score`: stalled_count / 8, clipped to [0, 1].",
        "- `far_score`: current distance is still high relative to the initial distance.",
        "- `no_improve_score`: cumulative best distance has barely improved.",
        "",
        "## Threshold 3.0 Summary",
        "",
        "| Task | Failure | Controller | Alarm Rate | Mean Alarm Step |",
        "|---|---|---|---:|---:|",
    ]
    for _, row in selected.sort_values(["task", "failure", "controller"]).iterrows():
        mean_step = "" if pd.isna(row["mean_alarm_step"]) else f"{row['mean_alarm_step']:.1f}"
        lines.append(
            f"| {row['task']} | {row['failure']} | {row['controller']} | "
            f"{row['alarm_rate']:.3f} | {mean_step} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Fault sensitivity is strong: jaw-stuck perturbed episodes are detected for both tasks.",
            "- Specificity is still weak: nominal episodes can trigger late alarms because normal approach/grasp phases contain stalls.",
            "- The next improvement should add phase gating or a learned calibration layer so normal pre-grasp pauses are not treated the same as failed grasps.",
            "",
            "## Outputs",
            "",
            "- `reports/tables/observable_proxy_scored_steps_10seed.csv`",
            "- `reports/tables/observable_proxy_threshold_sweep_10seed.csv`",
            "- `reports/figures/observable_proxy_risk/observable_proxy_threshold_sweep.png`",
        ]
    )
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    table_dir = ROOT / "reports" / "tables"
    figure_dir = ROOT / "reports" / "figures" / "observable_proxy_risk"
    table_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    scored = load_scored_steps()
    sweep = sweep_thresholds(scored)
    scored.to_csv(table_dir / "observable_proxy_scored_steps_10seed.csv", index=False)
    sweep.to_csv(table_dir / "observable_proxy_threshold_sweep_10seed.csv", index=False)
    plot_sweep(sweep, figure_dir)
    write_report(sweep, scored, ROOT / "reports" / "observable_proxy_risk_sweep.md")

    print(f"scored={table_dir / 'observable_proxy_scored_steps_10seed.csv'}")
    print(f"sweep={table_dir / 'observable_proxy_threshold_sweep_10seed.csv'}")
    print(f"figures={figure_dir}")


if __name__ == "__main__":
    main()
