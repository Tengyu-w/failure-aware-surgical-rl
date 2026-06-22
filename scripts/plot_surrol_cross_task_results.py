import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


FAILURE_LABELS = {
    "action_noise": "Action noise",
    "action_dropout": "Action dropout",
    "execution_slip": "Execution slip",
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode-csv", action="append", required=True)
    parser.add_argument("--out-dir", required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for csv_path in args.episode_csv:
        rows.append(pd.read_csv(csv_path))
    df = pd.concat(rows, ignore_index=True)
    df = df[df["failure"].isin(FAILURE_LABELS)]
    df = df[df["controller"].isin(["perturbed", "monitor_corrected"])]

    summary = (
        df.groupby(["task", "failure", "controller"], as_index=False)
        .agg(success=("success", "mean"), phase_replans=("recovery_phase_replans", "mean"))
    )

    tasks = list(summary["task"].drop_duplicates())
    failures = list(FAILURE_LABELS)
    x_labels = [f"{task}\n{FAILURE_LABELS[failure]}" for task in tasks for failure in failures]
    x = range(len(x_labels))
    width = 0.38

    fig, ax = plt.subplots(figsize=(14, 6))
    perturbed = []
    recovered = []
    replans = []
    for task in tasks:
        for failure in failures:
            p = summary[
                (summary["task"] == task)
                & (summary["failure"] == failure)
                & (summary["controller"] == "perturbed")
            ]["success"]
            r = summary[
                (summary["task"] == task)
                & (summary["failure"] == failure)
                & (summary["controller"] == "monitor_corrected")
            ]["success"]
            rp = summary[
                (summary["task"] == task)
                & (summary["failure"] == failure)
                & (summary["controller"] == "monitor_corrected")
            ]["phase_replans"]
            perturbed.append(float(p.iloc[0]) if not p.empty else 0.0)
            recovered.append(float(r.iloc[0]) if not r.empty else 0.0)
            replans.append(float(rp.iloc[0]) if not rp.empty else 0.0)

    ax.bar([i - width / 2 for i in x], perturbed, width, label="Perturbed", color="#d95f02")
    ax.bar([i + width / 2 for i in x], recovered, width, label="Recovered", color="#1b9e77")
    for i, (p, r, rp) in enumerate(zip(perturbed, recovered, replans)):
        ax.text(i - width / 2, p + 0.025, f"{p:.1f}", ha="center", va="bottom", fontsize=10)
        ax.text(i + width / 2, r + 0.025, f"{r:.1f}", ha="center", va="bottom", fontsize=10)
        if rp > 0:
            ax.text(i + width / 2, 0.50, f"phase\n{rp:.1f}", ha="center", va="center", fontsize=9, color="white")

    ax.set_title("Cross-Task Runtime Recovery in SurRoL", fontsize=18)
    ax.set_ylabel("Success rate")
    ax.set_ylim(0, 1.15)
    ax.set_xticks(list(x))
    ax.set_xticklabels(x_labels, fontsize=10)
    ax.grid(axis="y", alpha=0.35)
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(out_dir / "cross_task_success_rate.png", dpi=200)
    plt.close(fig)

    readme = out_dir / "README.md"
    readme.write_text(
        "# SurRoL Cross-Task Figures\n\n"
        "- `cross_task_success_rate.png`: perturbed vs recovered success rates for NeedlePick and GauzeRetrieve.\n",
        encoding="utf-8",
    )

    summary.to_csv(out_dir / "cross_task_summary.csv", index=False)
    print(f"figures={out_dir}")


if __name__ == "__main__":
    main()
