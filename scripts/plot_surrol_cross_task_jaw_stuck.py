import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode-csv", action="append", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--title", default="Cross-Task Phase-Aware Recovery Under Silent Jaw-Stuck Fault")
    return parser.parse_args()


def main():
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.concat([pd.read_csv(path) for path in args.episode_csv], ignore_index=True)
    df = df[df["failure"] == "jaw_stuck_open"]
    summary = (
        df.groupby(["task", "controller"], as_index=False)
        .agg(
            success=("success", "mean"),
            triggers=("monitor_triggers", "mean"),
            phase_replans=("recovery_phase_replans", "mean"),
            steps=("steps", "mean"),
            final_distance=("final_distance", "mean"),
        )
    )
    summary.to_csv(out_dir / "cross_task_jaw_stuck_summary.csv", index=False)

    tasks = sorted(summary["task"].unique())
    x = range(len(tasks))
    width = 0.34
    perturbed = []
    recovered = []
    triggers = []
    replans = []
    for task in tasks:
        perturbed.append(float(summary[(summary.task == task) & (summary.controller == "perturbed")]["success"].iloc[0]))
        rec = summary[(summary.task == task) & (summary.controller == "monitor_corrected")]
        recovered.append(float(rec["success"].iloc[0]))
        triggers.append(float(rec["triggers"].iloc[0]))
        replans.append(float(rec["phase_replans"].iloc[0]))

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.7))
    axes[0].bar([i - width / 2 for i in x], perturbed, width, label="Perturbed", color="#d95f02")
    axes[0].bar([i + width / 2 for i in x], recovered, width, label="Recovered", color="#1b9e77")
    for i, value in enumerate(perturbed):
        axes[0].text(i - width / 2, value + 0.03, f"{value:.1f}", ha="center")
    for i, value in enumerate(recovered):
        axes[0].text(i + width / 2, value + 0.03, f"{value:.1f}", ha="center")
    axes[0].set_xticks(list(x))
    axes[0].set_xticklabels(tasks)
    axes[0].set_ylim(0, 1.15)
    axes[0].set_ylabel("Success rate")
    axes[0].set_title("Silent Jaw-Stuck Failure")
    axes[0].legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.02), ncol=2)
    axes[0].grid(axis="y", alpha=0.35)

    axes[1].bar([i - width / 2 for i in x], triggers, width, label="Triggers", color="#f59e0b")
    axes[1].bar([i + width / 2 for i in x], replans, width, label="Grasp retries", color="#7c3aed")
    for i, value in enumerate(triggers):
        axes[1].text(i - width / 2, value + 0.12, f"{value:.1f}", ha="center")
    for i, value in enumerate(replans):
        axes[1].text(i + width / 2, value + 0.12, f"{value:.1f}", ha="center")
    axes[1].set_xticks(list(x))
    axes[1].set_xticklabels(tasks)
    axes[1].set_ylim(0, max(6, max(triggers) + 0.8))
    axes[1].set_ylabel("Mean count per recovered episode")
    axes[1].set_title("Recovery Mechanism")
    axes[1].legend(frameon=False, loc="upper right")
    axes[1].grid(axis="y", alpha=0.35)

    fig.suptitle(args.title, fontsize=15)
    fig.tight_layout()
    fig.savefig(out_dir / "cross_task_jaw_stuck_recovery.png", dpi=200)
    plt.close(fig)

    (out_dir / "README.md").write_text(
        "# Cross-Task Jaw-Stuck Figures\n\n"
        "- `cross_task_jaw_stuck_recovery.png`: jaw-stuck success recovery and recovery mechanism counts across tasks.\n",
        encoding="utf-8",
    )
    print(f"figures={out_dir}")


if __name__ == "__main__":
    main()
