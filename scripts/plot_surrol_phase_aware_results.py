from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


FAILURES = ["action_noise", "action_dropout", "execution_slip"]
CONTROLLERS = ["perturbed", "monitor_corrected"]
COLORS = {
    "clean": "#4B5563",
    "perturbed": "#D55E00",
    "monitor_corrected": "#0072B2",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode-csv", type=Path, required=True)
    parser.add_argument("--step-csv", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def mean(values: list[float]) -> float:
    return float(np.mean(values)) if values else float("nan")


def group_episode(rows: list[dict[str, str]]) -> dict[tuple[str, str], list[dict[str, str]]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row["failure"], row["controller"])].append(row)
    return grouped


def plot_success_bars(rows: list[dict[str, str]], out_dir: Path) -> None:
    grouped = group_episode(rows)
    x = np.arange(len(FAILURES))
    width = 0.34

    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    for offset, controller in [(-width / 2, "perturbed"), (width / 2, "monitor_corrected")]:
        vals = [
            mean([float(row["success"]) for row in grouped.get((failure, controller), [])])
            for failure in FAILURES
        ]
        bars = ax.bar(
            x + offset,
            vals,
            width,
            label="Perturbed" if controller == "perturbed" else "Phase-aware recovery",
            color=COLORS[controller],
        )
        for bar, value in zip(bars, vals):
            y = value + 0.025 if value > 0 else 0.025
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                y,
                f"{value:.1f}",
                ha="center",
                va="bottom",
                fontsize=9,
                color="#111827",
            )

    ax.set_title("SurRoL NeedlePick: Phase-Aware Recovery Restores Corrupted Rollouts")
    ax.set_ylabel("Success rate")
    ax.set_ylim(0, 1.08)
    ax.set_xticks(x)
    ax.set_xticklabels(["Action noise", "Action dropout", "Execution slip"])
    ax.legend(frameon=False, loc="upper left")
    ax.grid(axis="y", color="#E5E7EB", linewidth=0.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_dir / "success_rate_by_failure.png", dpi=180)
    plt.close(fig)


def step_groups(rows: list[dict[str, str]]) -> dict[tuple[str, str, int], list[dict[str, str]]]:
    grouped: dict[tuple[str, str, int], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row["failure"], row["controller"], int(row["seed"]))].append(row)
    for seq in grouped.values():
        seq.sort(key=lambda row: int(row["step"]))
    return grouped


def plot_representative_distances(rows: list[dict[str, str]], out_dir: Path) -> None:
    grouped = step_groups(rows)
    seeds = {
        "action_noise": 43000,
        "action_dropout": 43001,
        "execution_slip": 43001,
    }
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.2), sharey=True)
    for ax, failure in zip(axes, FAILURES):
        seed = seeds[failure]
        for controller in CONTROLLERS:
            seq = grouped.get((failure, controller, seed), [])
            if not seq:
                continue
            steps = [int(row["step"]) for row in seq]
            distance = [float(row["distance"]) for row in seq]
            label = "Perturbed" if controller == "perturbed" else "Phase-aware recovery"
            ax.plot(steps, distance, label=label, color=COLORS[controller], linewidth=2)
        ax.axhline(0.025, color="#6B7280", linestyle="--", linewidth=1, label="Success threshold")
        ax.set_title(failure.replace("_", " ").title())
        ax.set_xlabel("Step")
        ax.grid(color="#E5E7EB", linewidth=0.8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    axes[0].set_ylabel("Goal distance")
    axes[0].legend(frameon=False, loc="upper right")
    fig.suptitle("Representative Distance Trajectories")
    fig.tight_layout()
    fig.savefig(out_dir / "representative_distance_curves.png", dpi=180)
    plt.close(fig)


def plot_phase_replan_timeline(rows: list[dict[str, str]], out_dir: Path) -> None:
    grouped = step_groups(rows)
    targets = [("action_dropout", 43001), ("execution_slip", 43001)]
    fig, axes = plt.subplots(2, 1, figsize=(9.5, 5.8), sharex=True)
    for ax, (failure, seed) in zip(axes, targets):
        seq = grouped.get((failure, "monitor_corrected", seed), [])
        steps = [int(row["step"]) for row in seq]
        distance = [float(row["distance"]) for row in seq]
        triggers = [int(row["step"]) for row in seq if float(row["monitor_trigger"]) > 0]
        replan_steps = []
        previous_count = 0.0
        for row in seq:
            count = float(row.get("recovery_replan", 0.0) or 0.0)
            if count > previous_count:
                replan_steps.append(int(row["step"]))
            previous_count = count

        ax.plot(steps, distance, color=COLORS["monitor_corrected"], linewidth=2, label="Distance")
        for step in triggers:
            ax.axvline(step, color="#F59E0B", alpha=0.35, linewidth=1)
        for step in sorted(set(replan_steps)):
            ax.axvline(step, color="#7C3AED", alpha=0.9, linewidth=1.6, linestyle="--")
        ax.axhline(0.025, color="#6B7280", linestyle="--", linewidth=1)
        ax.set_title(f"{failure.replace('_', ' ').title()} seed {seed}")
        ax.set_ylabel("Goal distance")
        ax.grid(color="#E5E7EB", linewidth=0.8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    axes[-1].set_xlabel("Step")
    fig.suptitle("Phase-Aware Recovery Timeline: Trigger vs Grasp Retry")
    fig.text(0.62, 0.94, "orange: trigger, purple dashed: grasp retry", fontsize=9, color="#374151")
    fig.tight_layout()
    fig.savefig(out_dir / "phase_replan_timeline.png", dpi=180)
    plt.close(fig)


def write_figure_index(out_dir: Path) -> None:
    lines = [
        "# SurRoL Phase-Aware Recovery Figures",
        "",
        "- `success_rate_by_failure.png`: success-rate comparison for perturbed vs phase-aware recovery.",
        "- `representative_distance_curves.png`: representative distance trajectories for each failure type.",
        "- `phase_replan_timeline.png`: trigger and grasp-retry timing for dropout/slip examples.",
        "",
    ]
    (out_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    episode_rows = read_csv(args.episode_csv)
    step_rows = read_csv(args.step_csv)

    plot_success_bars(episode_rows, args.out_dir)
    plot_representative_distances(step_rows, args.out_dir)
    plot_phase_replan_timeline(step_rows, args.out_dir)
    write_figure_index(args.out_dir)
    print(f"figures={args.out_dir}")


if __name__ == "__main__":
    main()
