import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode-csv", required=True)
    parser.add_argument("--out-dir", required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(args.episode_csv)
    df = df[df["failure"] == "jaw_stuck_open"]

    summary = (
        df.groupby("controller", as_index=False)
        .agg(
            success=("success", "mean"),
            phase_replans=("recovery_phase_replans", "mean"),
            triggers=("monitor_triggers", "mean"),
            steps=("steps", "mean"),
        )
    )
    summary.to_csv(out_dir / "jaw_stuck_summary.csv", index=False)

    labels = ["Perturbed", "Recovered"]
    success_values = [
        float(summary.loc[summary.controller == "perturbed", "success"].iloc[0]),
        float(summary.loc[summary.controller == "monitor_corrected", "success"].iloc[0]),
    ]
    replan_value = float(summary.loc[summary.controller == "monitor_corrected", "phase_replans"].iloc[0])
    trigger_value = float(summary.loc[summary.controller == "monitor_corrected", "triggers"].iloc[0])

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.4))
    colors = ["#d95f02", "#1b9e77"]
    bars = axes[0].bar(labels, success_values, color=colors, width=0.55)
    for bar, value in zip(bars, success_values):
        axes[0].text(bar.get_x() + bar.get_width() / 2, value + 0.03, f"{value:.1f}", ha="center")
    axes[0].set_ylim(0, 1.15)
    axes[0].set_ylabel("Success rate")
    axes[0].set_title("Jaw-Stuck Failure Recovery")
    axes[0].grid(axis="y", alpha=0.35)

    axes[1].bar(["Triggers", "Grasp retries"], [trigger_value, replan_value], color=["#f59e0b", "#7c3aed"], width=0.55)
    axes[1].text(0, trigger_value + 0.15, f"{trigger_value:.1f}", ha="center")
    axes[1].text(1, replan_value + 0.15, f"{replan_value:.1f}", ha="center")
    axes[1].set_ylim(0, max(6, trigger_value + 1))
    axes[1].set_ylabel("Mean count per episode")
    axes[1].set_title("Recovery Mechanism")
    axes[1].grid(axis="y", alpha=0.35)

    fig.suptitle("GauzeRetrieve: Silent Jaw-Stuck Fault Requires Grasp Retry", fontsize=15)
    fig.tight_layout()
    fig.savefig(out_dir / "gauzeretrieve_jaw_stuck_recovery.png", dpi=200)
    plt.close(fig)

    (out_dir / "README.md").write_text(
        "# GauzeRetrieve Jaw-Stuck Figures\n\n"
        "- `gauzeretrieve_jaw_stuck_recovery.png`: success recovery and mean recovery mechanism counts.\n",
        encoding="utf-8",
    )
    print(f"figures={out_dir}")


if __name__ == "__main__":
    main()
